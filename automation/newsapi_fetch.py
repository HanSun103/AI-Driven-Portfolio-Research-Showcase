"""Fetch-only research collection. Never print provider bodies, keys or article data."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import gzip
import io
import json
import os
from pathlib import Path
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from cryptography.fernet import Fernet

REPO = "HanSun103/AI-Driven-Portfolio-Research-Showcase"
QUERY = "stock market OR equities OR earnings"
MAX_REQUESTS = 80  # Across rolling 24 hours, including manual retries.
MAX_BODY = 4_000_000
MAX_ARCHIVE_BYTES = 4_000_000
UTC = timezone.utc


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the provider credential to a redirect target.
        return None


def iso(value):
    return value.astimezone(UTC).isoformat()


def dt(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def cutoff(now):
    # Extra 15 minutes protects against clock skew and provider indexing delay.
    return (now - timedelta(hours=24, minutes=15)).replace(minute=0, second=0, microsecond=0)


def seal(value, key):
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    return Fernet(key).encrypt(gzip.compress(raw, mtime=0))


def unseal(value, key):
    packed = Fernet(key).decrypt(value)
    with gzip.GzipFile(fileobj=io.BytesIO(packed)) as stream:
        raw = stream.read(32_000_001)
    if len(raw) > 32_000_000:
        raise ValueError("archive_too_large")
    return json.loads(raw)


def gh_bytes(endpoint, paginate=False):
    args = ["gh", "api", endpoint]
    if paginate:
        args += ["--paginate", "--slurp"]
    result = subprocess.run(args, capture_output=True, check=False, timeout=90)
    if result.returncode:
        raise RuntimeError("github_request_failed")
    return result.stdout


def artifact_list():
    pages = json.loads(gh_bytes(f"repos/{REPO}/actions/artifacts?per_page=100", True))
    return [a for page in pages for a in page["artifacts"]]


def restore(key, artifacts, bootstrap):
    states = [a for a in artifacts if a["name"].startswith("newsapi-state-")]
    if not states:
        if bootstrap:
            return None
        raise RuntimeError("state_missing_manual_bootstrap_required")
    latest = max(states, key=lambda a: int(a["id"]))
    if latest["expired"]:
        raise RuntimeError("latest_state_expired")
    raw = gh_bytes(f"repos/{REPO}/actions/artifacts/{latest['id']}/zip")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        if len(members) != 1 or members[0].filename != "state.enc" or members[0].file_size > MAX_BODY:
            raise ValueError("invalid_state_artifact")
        state = unseal(archive.read(members[0]), key)
    if state.get("version") != 1 or state.get("query") != QUERY or state.get("repository") != REPO:
        raise ValueError("incompatible_state")
    return state


def prepare_state(state, now, run_id):
    end = cutoff(now)
    if state is None:
        state = dict(version=1, repository=REPO, query=QUERY, cursor=iso(end-timedelta(hours=48)),
                     pending=[], reservations=[], expired_windows=0)
    # Persisted quota reservations protect retries even if a worker dies mid-fetch.
    state["reservations"] = [r for r in state["reservations"] if dt(r["at"]) > now-timedelta(hours=24)]
    budget = max(0, MAX_REQUESTS-sum(r["count"] for r in state["reservations"]))
    # A workflow can run for 15 minutes. Reserve through its latest possible
    # request time, so rolling expiry never precedes the actual API calls.
    state["reservations"].append(dict(id=run_id, at=iso(now+timedelta(minutes=15)), count=budget))
    cursor = dt(state["cursor"])
    if cursor > end:
        raise ValueError("future_cursor")
    # Expired gaps are counted, never described as recovered.
    oldest = (now-timedelta(days=28)).replace(minute=0, second=0, microsecond=0)
    if cursor < oldest:
        state["expired_windows"] += int((oldest-cursor).total_seconds()//3600)
        cursor = oldest
    while cursor < end:
        state["pending"].append(dict(start=iso(cursor), end=iso(cursor+timedelta(hours=1)), attempts=0))
        cursor += timedelta(hours=1)
    retained = []
    for window in state["pending"]:
        if dt(window["start"]) < oldest:
            state["expired_windows"] += 1
        else:
            retained.append(window)
    state.update(pending=retained, cursor=iso(end), current_run=run_id, reserved=budget)
    return state


def fetch(window, api_key):
    params = dict(q=QUERY, language="en", pageSize=100, page=1, sortBy="publishedAt",
                  **{"from": iso(dt(window["start"])), "to": iso(dt(window["end"])-timedelta(seconds=1))})
    url = "https://newsapi.org/v2/everything?"+urllib.parse.urlencode(params)
    # API key is a header, never a URL parameter or command-line argument.
    request = urllib.request.Request(url, headers={"X-Api-Key": api_key, "User-Agent": "portfolio-research-fetch/1"})
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=25) as response:
            body = response.read(MAX_BODY+1)
        if len(body) > MAX_BODY:
            return {"status": "error", "code": "response_too_large"}
        result = json.loads(body)
        return result if isinstance(result, dict) else dict(status="error", code="invalid_response")
    except urllib.error.HTTPError as exc:
        try:
            data = json.loads(exc.read(16384))
            code = data.get("code")
        except Exception:
            code = None
        allowed = {"rateLimited", "apiKeyExhausted", "apiKeyInvalid", "apiKeyDisabled",
                   "parameterInvalid", "maximumResultsReached", "parameterMissing"}
        return dict(status="error", code=code if code in allowed else "http_error", http_status=exc.code)
    except Exception:
        return dict(status="error", code="network_or_parse_error")


def collect(state, now, api_key, key, request=fetch):
    # Current 24 hours of newly reachable news first; older recovery second.
    end = cutoff(now)
    eligible = [w for w in state["pending"] if w.get("attempts", 0) < 3 and
                (not w.get("last_attempt") or dt(w["last_attempt"]) <= now-timedelta(hours=6))]
    recent = sorted([w for w in eligible if dt(w["start"]) >= end-timedelta(hours=24)], key=lambda w:w["start"])
    older = sorted([w for w in eligible if dt(w["start"]) < end-timedelta(hours=24)], key=lambda w:w["start"])
    batch = dict(version=1, repository=REPO, run_id=state["current_run"], commit=os.getenv("GITHUB_SHA"),
                 query=QUERY, collection_started_at=iso(now), windows=[], expired_windows=state["expired_windows"])
    used = 0
    complete = set()
    for window in (recent+older)[:state["reserved"]]:
        used += 1
        window["attempts"] += 1
        window["last_attempt"] = iso(now)
        response = request(window, api_key)
        articles = response.get("articles")
        total = response.get("totalResults")
        valid = response.get("status") == "ok" and isinstance(articles, list) and isinstance(total, int) and total >= 0
        good = valid and total <= len(articles) and total <= 100
        if valid:
            for article in articles:
                try:
                    publication = dt(article["publishedAt"])
                    if not (dt(window["start"]) <= publication < dt(window["end"])) or not article.get("url"):
                        good = False
                except Exception:
                    good = False
            if len({a.get("url") for a in articles if isinstance(a, dict)}) < len(articles):
                good = False
        window["last_status"] = "complete" if good else "incomplete"
        batch["windows"].append(dict(start=window["start"], end=window["end"], fetched_at=iso(datetime.now(UTC)),
                                      status=window["last_status"], response=response))
        if good:
            complete.add(window["start"])
        # Bounded one-page windows; never evade paid-page restrictions or change query.
        if response.get("code") in {"rateLimited", "apiKeyExhausted", "apiKeyInvalid", "apiKeyDisabled"} or response.get("http_status") in {401,403,429}:
            break
        # Bound storage; keep the response that crossed the threshold, then stop fetching.
        if len(seal(batch, key)) >= MAX_ARCHIVE_BYTES or len(json.dumps(batch, ensure_ascii=False).encode()) >= 24_000_000:
            break
    state["pending"] = [w for w in state["pending"] if w["start"] not in complete]
    for reservation in state["reservations"]:
        if reservation["id"] == state["current_run"]:
            reservation["count"] = used
    batch.update(requests=used, outstanding_windows=len(state["pending"]),
                 coverage_status="complete_requested_windows" if not state["pending"] else "incomplete")
    return state,batch


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("stage", choices=["prepare","collect","status"])
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--out", default="private/run")
    args=parser.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    key=os.environ.get("NEWS_ARCHIVE_KEY", "").encode()
    Fernet(key)  # Fail closed before any external request when missing/invalid.
    if args.stage=="prepare":
        if not os.environ.get("NEWSAPI_KEY"):
            raise RuntimeError("newsapi_secret_missing")
        artifacts=artifact_list()
        retained=sum(a["size_in_bytes"] for a in artifacts if not a["expired"])
        if retained > 400_000_000:
            raise RuntimeError("artifact_storage_budget_requires_local_archival")
        state=restore(key,artifacts,args.bootstrap)
        now=datetime.now(UTC)
        state=prepare_state(state,now,os.environ["GITHUB_RUN_ID"]+"-"+os.environ["GITHUB_RUN_ATTEMPT"])
        (out/"reserved").mkdir(exist_ok=True)
        (out/"reserved/state.enc").write_bytes(seal(state,key))
    elif args.stage=="collect":
        state=unseal((out/"reserved/state.enc").read_bytes(),key)
        state,batch=collect(state,datetime.now(UTC),os.environ["NEWSAPI_KEY"],key)
        # Batch must be uploaded before the final state advances past completed windows.
        (out/"batch.enc").write_bytes(seal(batch,key))
        (out/"final").mkdir(exist_ok=True)
        (out/"final/state.enc").write_bytes(seal(state,key))
    else:
        state=unseal((out/"final/state.enc").read_bytes(),key)
        if state["pending"] or state["expired_windows"]:
            print("Collection archived; private coverage audit requires review.")
            return 2
        print("Requested windows archived. This does not certify all-source completeness.")
    return 0


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Never print raw exception messages: network/provider errors may include secrets.
        print("Collector blocked: "+type(exc).__name__+". Review configuration or encrypted audit.")
        raise SystemExit(1)
