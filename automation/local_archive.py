"""Windows-only key setup and local retrieval; no provider key or model processing."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import io
import json
import os
from pathlib import Path
import subprocess
import zipfile

from cryptography.fernet import Fernet
from newsapi_fetch import REPO, artifact_list, gh_bytes, unseal


def protect(data: bytes, decrypt=False) -> bytes:
    if os.name != "nt":
        raise RuntimeError("windows_dpapi_required")

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source, target = Blob(len(data), buffer), Blob()
    dll = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if decrypt:
        call = dll.CryptUnprotectData
        call.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    else:
        call = dll.CryptProtectData
        call.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    call.restype = wintypes.BOOL
    if not call(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise RuntimeError("dpapi_failed")
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel.LocalFree(target.pbData)


def key_setup(path):
    if path.exists():
        key = protect(path.read_bytes(), decrypt=True)
    else:
        # Refuse to replace a remotely configured key with a new random key.
        result = subprocess.run(["gh", "secret", "list", "--repo", REPO, "--json", "name"],
                                capture_output=True, timeout=60)
        if result.returncode:
            raise RuntimeError("secret_metadata_unavailable")
        if any(x["name"] == "NEWS_ARCHIVE_KEY" for x in json.loads(result.stdout)):
            raise RuntimeError("existing_remote_key_requires_original_local_backup")
        key = Fernet.generate_key()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(protect(key))
    Fernet(key)
    result = subprocess.run(["gh", "secret", "set", "NEWS_ARCHIVE_KEY", "--repo", REPO],
                            input=key, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError("archive_secret_upload_failed_local_backup_retained")
    print("Archive secret configured; local DPAPI recovery file retained. No key displayed.")


def read_batch(raw, key):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if len(entries) != 1 or entries[0].filename != "batch.enc" or entries[0].file_size > 16_000_000:
            raise ValueError("invalid_batch_artifact")
        ciphertext = archive.read(entries[0])
    batch = unseal(ciphertext, key)
    if batch.get("repository") != REPO or batch.get("version") != 1:
        raise ValueError("incompatible_batch")
    return ciphertext, batch


def download(path, out):
    key = protect(path.read_bytes(), decrypt=True)
    out.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    expired = 0
    for artifact in sorted(artifact_list(), key=lambda a: int(a["id"])):
        if not artifact["name"].startswith("newsapi-batch-"):
            continue
        target = out / str(int(artifact["id"]))
        if (target / "receipt.json").exists():
            continue
        if artifact["expired"]:
            expired += 1
            continue
        raw = gh_bytes(f"repos/{REPO}/actions/artifacts/{artifact['id']}/zip")
        ciphertext, batch = read_batch(raw, key)
        target.mkdir(exist_ok=True)
        (target / "batch.enc").write_bytes(ciphertext)
        (target / "batch.json").write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
        receipt = dict(artifact_id=artifact["id"], name=artifact["name"], created_at=artifact["created_at"],
                       run_id=batch["run_id"], requests=batch["requests"],
                       outstanding_windows=batch["outstanding_windows"], coverage_status=batch["coverage_status"])
        # Receipt is last: an interrupted download remains retryable.
        (target / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        downloaded += 1
    print(json.dumps(dict(downloaded_batches=downloaded, expired_unavailable_batches=expired)))
    return 2 if expired else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["setup-key", "download"])
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("private/downloaded"))
    args = parser.parse_args()
    if args.action == "setup-key":
        key_setup(args.key_file)
        return 0
    return download(args.key_file, args.out)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("Local archive operation blocked: " + type(exc).__name__ + ". No secret or provider body displayed.")
        raise SystemExit(1)
