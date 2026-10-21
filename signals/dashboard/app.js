"use strict";
const FEED = "https://raw.githubusercontent.com/HanSun103/AI-Driven-Portfolio-Research-Showcase/main/signals/feed.json";
const $ = s => document.querySelector(s);
let data, selectedDate, connected = false;
const dateLabel = s => new Date(`${s}T12:00:00Z`).toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric",timeZone:"UTC"});
const timeLabel = s => new Date(s).toLocaleTimeString("en-US",{hour:"numeric",minute:"2-digit",timeZone:"America/New_York"}) + " ET";
const pct = (n,u="%") => `${n>=0?"+":"−"}${Math.abs(n).toFixed(2)}${u}`;
function el(tag,text,cls){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;}
function checkFeed(feed){
  if(feed.schema_version!==1 || !Array.isArray(feed.runs) || !feed.runs.length)throw Error("Invalid feed");
  for(const r of feed.runs){
    if(!/^\d{4}-\d{2}-\d{2}$/.test(r.date)||!Array.isArray(r.picks)||r.picks.length!==8||![20,40].includes(r.active_horizon))throw Error("Invalid run");
    if(!r.picks.some(p=>p.id==="baseline"&&p.horizon===r.active_horizon))throw Error("Preferred model missing");
    for(const p of r.picks)if(!/^[A-Z][A-Z0-9.\-]{0,9}$/.test(p.ticker))throw Error("Invalid ticker");
    if(!Number.isFinite(Date.parse(r.entry_open))||!Number.isFinite(Date.parse(r.expires_at)))throw Error("Missing timing");
  }
}
function render(){
  const r=data.runs.find(x=>x.date===selectedDate);if(!r)return;
  const p=r.picks.find(x=>x.id==="baseline"&&x.horizon===r.active_horizon);
  const archive=r.date!==data.latest_date, stale=Date.now()>=Date.parse(r.expires_at), missed=Date.now()>=Date.parse(r.entry_open)||!r.timely_recording;
  $("#recorded").textContent=`Recorded ${dateLabel(r.date)} · ${timeLabel(r.recorded_at)}`;
  $("#snapshot-state").textContent=archive?"HISTORICAL SNAPSHOT":stale?"AWAITING NEW RUN":"LATEST COMPLETED RUN";
  $("#notice").className=`notice ${archive||stale||missed||!connected?"warn":""}`;
  $("#notice").textContent=!connected?"LIVE FEED UNAVAILABLE — Showing a bundled historical snapshot. Freshness is not confirmed; do not treat it as a new entry instruction.":archive?"HISTORICAL VIEW — This is an earlier model observation. Its entry window is not an opportunity to buy now.":stale?"UPDATE PENDING — No newer successful run has been published. The last dated record stays visible for reference only.":missed?"ENTRY WINDOW PASSED — The snapshot remains available for monitoring. Do not backdate an entry or treat it as a catch-up trade.":"NEXT-SESSION OBSERVATION — The run completed with disclosed limitations. Review the scheduled open, position overlap and risk before deciding independently.";
  $("#ticker").textContent=p.ticker;
  $("#active-horizon").textContent=`H${r.active_horizon}`;
  $("#active-label").textContent=`SCHEDULED HORIZON / H${r.active_horizon}`;
  $("#ticker-sub").textContent=`Four-year taper · Decision ${dateLabel(r.date)}`;
  $("#signal-kind").textContent=archive?"ARCHIVED OBSERVATION":"SAVED MODEL OBSERVATION";
  $("#entry").textContent=dateLabel(p.entry);$("#entry-time").textContent=timeLabel(r.entry_open)+" · next session";
  $("#exit").textContent=dateLabel(p.exit);$("#exit-time").textContent=timeLabel(p.exit_open)+` · ${p.horizon} sessions later`;
  $("#signal-warning").textContent=p.warning?"A selection guardrail warning is present. Review required; this page does not authorize a trade.":"No triggered selection alert in this run. Missing matched history is not a clean risk certificate.";
  $("#horizon-cards").replaceChildren();
  for(const h of [20,40]){
    const m=r.picks.find(x=>x.id==="baseline"&&x.horizon===h);const card=el("article",undefined,`horizon-card ${h===r.active_horizon?"active":""}`);
    const label=el("div",`H${h}`,"horizon-name");label.append(el("span",h===r.active_horizon?"SCHEDULED":"MONITOR ONLY"));
    const dates=el("div","Planned exit ","horizon-dates");dates.append(el("strong",`${dateLabel(m.exit)} · ${timeLabel(m.exit_open)}`));
    card.append(label,el("div",m.ticker,"horizon-ticker"),dates);$("#horizon-cards").append(card);
  }
  $("#research-body").replaceChildren();
  for(const [id,label,status] of [["research-a","Research model A","Not ready for use"],["control","Comparison control","Evaluation only"],["legacy","Legacy baseline","Not preferred"]]){
    const tr=el("tr");tr.append(el("td",label),el("td",status));for(const h of [20,40])tr.append(el("td",r.picks.find(x=>x.id===id&&x.horizon===h).ticker));$("#research-body").append(tr);
  }
  $("#quality").textContent=`This run passed its input and membership gates. Range warnings: ${r.range_warnings}. Selection alerts: ${r.guardrail_warnings}. Auxiliary eligibility filter: ${r.eligibility_filter_active?"active":"inactive"}. These are operational facts, not proof of predictive performance.`;
  $("#switch").textContent=`H20 → H40 · ${dateLabel(data.switch_entry_date)} open`;
  $("#switch-detail").textContent=`November 3’s completed decision supplies the first H40 entry. The recorded H40 window ends at the ${dateLabel(data.switch_end_entry_date)} open. Existing lots keep their original exit dates. The pipeline must confirm the applicable horizon before publishing.`;
  $("#footer-date").textContent=`Latest successful decision: ${data.latest_date}`;
}
function renderEvidence(){
  $("#outcomes").replaceChildren();
  for(const r of data.checkpoint){const tr=el("tr");const name=el("td",r.ticker);name.append(el("small",dateLabel(r.entry)));tr.append(name,el("td",dateLabel(r.exit)));
    for(const [n,u]of[[r.stock_pct,"%"],[r.spy_pct,"%"],[r.active_pp," pp"]])tr.append(el("td",pct(n,u),`num ${n>=0?"positive":"negative"}`));$("#outcomes").append(tr);}
}
async function refresh(initial=false){
  try{
    const response=await fetch(FEED+"?v="+Date.now(),{cache:"no-store"});if(!response.ok)throw Error("Feed unavailable");const next=await response.json();checkFeed(next);data=next;connected=true;
  }catch{
    connected=false;
    if(!data){try{const response=await fetch("snapshot.json");if(!response.ok)throw Error();data=await response.json();checkFeed(data);}catch{$("#notice").textContent="NO VERIFIED FEED — Published data could not be loaded. No new entry information is available.";$("#notice").className="notice error";$("#connection").textContent="Feed unavailable";return;}}
  }
  $("#connection").textContent=connected?"Published feed connected":"Saved snapshot only";
  const wasLatest=!selectedDate||selectedDate===$("#date").options[0]?.value;
  $("#date").replaceChildren(...data.runs.map(r=>{const opt=el("option",dateLabel(r.date)+(r.date===data.latest_date?" · latest":""));opt.value=r.date;return opt;}));
  if(wasLatest||!data.runs.some(r=>r.date===selectedDate))selectedDate=data.latest_date;
  $("#date").value=selectedDate;$("#date").disabled=false;$("#latest").disabled=false;
  render();renderEvidence();
}
$("#date").addEventListener("change",e=>{selectedDate=e.target.value;render();});
$("#latest").addEventListener("click",async()=>{selectedDate=null;await refresh();});
$("#research-toggle").addEventListener("click",()=>{const open=$("#research-toggle").getAttribute("aria-expanded")!=="true";$("#research-toggle").setAttribute("aria-expanded",String(open));$("#research-toggle").textContent=open?"Hide observations −":"Show observations +";$("#research-table").hidden=!open;});
refresh(true);setInterval(()=>{if(!document.hidden)refresh();},300000);setInterval(()=>{if(data)render();},30000);
