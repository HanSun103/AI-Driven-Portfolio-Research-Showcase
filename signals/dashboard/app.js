"use strict";
const FEED = "https://raw.githubusercontent.com/HanSun103/AI-Driven-Portfolio-Research-Showcase/main/signals/feed.json";
const $ = s => document.querySelector(s);
let data, selectedDate, connected = false, refreshing = false;
const dateLabel = s => new Date(`${s}T12:00:00Z`).toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric",timeZone:"UTC"});
const timeLabel = s => new Date(s).toLocaleTimeString("en-US",{hour:"numeric",minute:"2-digit",timeZone:"America/New_York"}) + " ET";
const pct = (n,u="%") => `${n>=0?"+":"−"}${Math.abs(n).toFixed(2)}${u}`;
function el(tag,text,cls){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;}
function checkFeed(feed){
  if(!feed.archive||!Array.isArray(feed.archive.rows))throw Error("Archive unavailable");
  if(feed.schema_version!==1 || !Array.isArray(feed.runs) || !feed.runs.length)throw Error("Invalid feed");
  for(const r of feed.runs){
    if(!/^\d{4}-\d{2}-\d{2}$/.test(r.date)||!Array.isArray(r.picks)||r.picks.length!==8||![20,40].includes(r.active_horizon))throw Error("Invalid run");
    if(!r.picks.some(p=>p.id==="baseline"&&p.horizon===r.active_horizon))throw Error("Preferred model missing");
    for(const p of r.picks)if(!/^[A-Z][A-Z0-9.\-]{0,9}$/.test(p.ticker))throw Error("Invalid ticker");
    if(!Number.isFinite(Date.parse(r.entry_open))||!Number.isFinite(Date.parse(r.expires_at)))throw Error("Missing timing");
  }
}
// Retired dashboard track. Keep source receipts intact; apply this to every display.
function observations(){return (data.archive?.rows||[]).filter(r=>r.id!=="legacy");}
function displayedSummary(){
  const rows=observations(), forward=rows.filter(r=>r.evidence==="forward");
  return {observations:rows.length,forward:forward.length,
    late_diagnostic:rows.filter(r=>r.evidence==="late_diagnostic").length,
    timestamp_unverified:rows.filter(r=>r.evidence==="timestamp_unverified").length,
    matured_forward:forward.filter(r=>r.status==="matured").length,
    pending_forward:forward.filter(r=>["holding","awaiting_entry"].includes(r.status)).length,
    missing_prices_forward:forward.filter(r=>r.status==="missing_prices").length};
}
function allDates(){return [...new Set([...data.runs.map(r=>r.date),...observations().map(r=>r.date)])].sort().reverse();}
function historyRun(day){
  const rows=observations().filter(r=>r.date===day);if(!rows.length)return null;
  return {date:day,recorded_at:rows.map(r=>r.recorded_at).filter(Boolean).sort().at(-1),active_horizon:rows[0].entry>=data.switch_entry_date&&rows[0].entry<data.switch_end_entry_date?40:20,
    entry_open:rows[0].entry_open,expires_at:rows[0].entry_open,timely_recording:rows.every(r=>r.evidence==="forward"),historical_only:true,
    picks:rows.map(r=>({...r,warning:null}))};
}
function render(){
  const r=data.runs.find(x=>x.date===selectedDate)||historyRun(selectedDate);if(!r)return;
  const p=r.picks.find(x=>x.id==="baseline"&&x.horizon===r.active_horizon);
  const archive=r.date!==data.latest_date, stale=Date.now()>=Date.parse(r.expires_at), missed=Date.now()>=Date.parse(r.entry_open)||!r.timely_recording;
  $("#recorded").textContent=r.recorded_at?`Recorded ${new Date(r.recorded_at).toLocaleDateString("en-US",{timeZone:"America/New_York",month:"short",day:"numeric",year:"numeric"})} · ${timeLabel(r.recorded_at)}`:"Original timestamp unavailable";
  $("#snapshot-state").textContent=archive?"HISTORICAL SNAPSHOT":stale?"AWAITING NEW RUN":"LATEST COMPLETED RUN";
  $("#notice").className=`notice ${archive||stale||missed||!connected?"warn":""}`;
  $("#notice").textContent=!connected?"LIVE FEED UNAVAILABLE — Showing a bundled historical snapshot. Freshness is not confirmed; do not treat it as a new entry instruction.":archive?"HISTORICAL VIEW — This is an earlier model observation. Its entry window is not an opportunity to buy now.":stale?"UPDATE PENDING — No newer successful run has been published. The last dated record stays visible for reference only.":missed?"ENTRY WINDOW PASSED — The snapshot remains available for monitoring. Do not backdate an entry or treat it as a catch-up trade.":"NEXT-SESSION OBSERVATION — The run completed with disclosed limitations. Review the scheduled open, position overlap and risk before deciding independently.";
  $("#ticker").textContent=p?.ticker||"—";
  $("#active-horizon").textContent=`H${r.active_horizon}`;
  $("#active-label").textContent=`SCHEDULED HORIZON / H${r.active_horizon}`;
  $("#ticker-sub").textContent=`${p?"Primary finalist":"Production version not recorded"} · Decision ${dateLabel(r.date)}`;
  $("#signal-kind").textContent=archive?"ARCHIVED OBSERVATION":"SAVED MODEL OBSERVATION";
  $("#entry").textContent=p?dateLabel(p.entry):"Not recorded";$("#entry-time").textContent=timeLabel(r.entry_open)+" · next session";
  $("#exit").textContent=p?dateLabel(p.exit):"Not recorded";$("#exit-time").textContent=p?timeLabel(p.exit_open)+` · ${p.horizon} sessions later`:"See the available earlier model observations below";
  $("#signal-warning").textContent=r.historical_only?"Earlier archive: current production and guardrail coverage must not be inferred from this record.":p?.warning?"A selection guardrail warning is present. Review required; this page does not authorize a trade.":"No triggered selection alert in this run. Missing matched history is not a clean risk certificate.";
  $("#horizon-cards").replaceChildren();
  for(const h of [20,40]){
    const m=r.picks.find(x=>x.id==="baseline"&&x.horizon===h);const card=el("article",undefined,`horizon-card ${h===r.active_horizon?"active":""}`);
    const label=el("div",`H${h}`,"horizon-name");label.append(el("span",h===r.active_horizon?"SCHEDULED":"MONITOR ONLY"));
    const dates=el("div","Planned exit ","horizon-dates");dates.append(el("strong",m?`${dateLabel(m.exit)} · ${timeLabel(m.exit_open)}`:"Not recorded"));
    card.append(label,el("div",m?.ticker||"—","horizon-ticker"),dates);$("#horizon-cards").append(card);
  }
  $("#research-body").replaceChildren();
  for(const [id,label,status] of [["research-a","Research model A","Not ready for use"],["control","Comparison control","Evaluation only"],["paper-baseline","Earlier baseline","Historical vintages"]]){
    const tr=el("tr");tr.append(el("td",label),el("td",status));for(const h of [20,40])tr.append(el("td",r.picks.find(x=>x.id===id&&x.horizon===h)?.ticker||"Not recorded"));$("#research-body").append(tr);
  }
  $("#quality").textContent=r.historical_only?"Recovered earlier saved observations. Their original input policies and validation coverage differ; this archive does not retroactively certify today’s gates.":`This run passed its input and membership gates. Range warnings: ${r.range_warnings}. Selection alerts: ${r.guardrail_warnings}. Auxiliary eligibility filter: ${r.eligibility_filter_active?"active":"inactive"}. These are operational facts, not proof of predictive performance.`;
  $("#switch").textContent=`H20 → H40 · ${dateLabel(data.switch_entry_date)} open`;
  $("#switch-detail").textContent=`November 3’s completed decision supplies the first H40 entry. The recorded H40 window ends at the ${dateLabel(data.switch_end_entry_date)} open. Existing lots keep their original exit dates. The pipeline must confirm the applicable horizon before publishing.`;
  $("#footer-date").textContent=`Latest successful decision: ${data.latest_date}`;
}
function fillOptions(id, items){
  const select=$(id), prior=select.value;select.replaceChildren(...items.map(([value,label])=>{const o=el("option",label);o.value=value;return o;}));
  if(items.some(([v])=>v===prior))select.value=prior;
}
function setupArchive(){
  const rows=observations();
  fillOptions("#outcome-model",[["all","All displayed models"],...[...new Map(rows.map(r=>[r.id,r.name])).entries()]]);
  fillOptions("#outcome-month",[["all","All months"],...[...new Set(rows.map(r=>r.entry.slice(0,7)))].sort().reverse().map(m=>[m,m])]);
  fillOptions("#decision-month",[["all","All dates"],...[...new Set(allDates().map(d=>d.slice(0,7)))].map(m=>[m,m])]);
  $("#history-count").textContent=`· ${allDates().length} dates`;
  renderDecisions();renderEvidence();renderPerformance();
}
function selectDate(day){selectedDate=day;$("#date").value=day;render();$("#latest").textContent=day===data.latest_date?"Latest selected ✓":"Go to latest";}
function renderDecisions(){
  $("#decision-rows").replaceChildren();const month=$("#decision-month").value;
  for(const day of allDates().filter(d=>month==="all"||d.startsWith(month))){
    const rows=observations().filter(r=>r.date===day),tr=el("tr");tr.append(el("td",dateLabel(day)));
    for(const h of [20,40])tr.append(el("td",rows.find(r=>r.id==="baseline"&&r.horizon===h)?.ticker||"Not recorded"));
    const forwards=rows.filter(r=>r.evidence==="forward").length;
    tr.append(el("td",String(rows.length)),el("td",`${forwards} before entry${rows.length>forwards?`; ${rows.length-forwards} late/unverified`:""}`));
    const td=el("td"),button=el("button","View");button.type="button";button.setAttribute("aria-label",`View ${day} decision`);button.onclick=()=>{selectDate(day);$("#signals").scrollIntoView({behavior:"smooth",block:"start"});};td.append(button);tr.append(td);$("#decision-rows").append(tr);
  }
  const gaps=(data.archive?.coverage||[]).filter(r=>r.status!=="recorded").map(r=>r.date);
  $("#coverage-gaps").textContent=`No canonical saved observation recovered for these September-onward sessions: ${gaps.join(", ")||"none"}. These are gaps, not zero-return trades. Quarantined/failed runs are excluded.`;
}
function renderEvidence(){
  const a=data.archive,body=$("#outcomes");body.replaceChildren();if(!a){$("#outcome-summary").textContent="Archive unavailable";return;}
  const selected={};for(const k of ["model","horizon","month","status","evidence","limit"])selected[k]=$("#outcome-"+k).value;
  const summary=displayedSummary();
  const rows=observations().filter(r=>(selected.model==="all"||r.id===selected.model)&&(selected.horizon==="all"||String(r.horizon)===selected.horizon)&&(selected.month==="all"||r.entry.startsWith(selected.month))&&(selected.status==="all"||r.status===selected.status)&&(selected.evidence==="all"||r.evidence===selected.evidence))
    .sort((a,b)=>b.exit.localeCompare(a.exit)||b.date.localeCompare(a.date)||a.name.localeCompare(b.name));
  const visible=selected.limit==="all"?rows:rows.slice(0,Number(selected.limit));
  const status={matured:"Matured",holding:"Still holding",awaiting_entry:"Awaiting entry",missing_prices:"Price verification missing"};
  for(const r of visible){
    const tr=el("tr"),model=el("td",r.name);model.append(el("small",`Vintage ${r.vintage} · H${r.horizon}`));
    const stock=el("td",r.ticker);stock.append(el("small",dateLabel(r.date)));
    const dates=el("td",`${dateLabel(r.entry)} →`);dates.append(el("small",dateLabel(r.exit)+(r.calendar_corrected?" · calendar corrected":"")));
    const state=el("td",status[r.status]);state.append(el("small",r.evidence==="forward"?"Recorded before entry":r.evidence==="late_diagnostic"?"Late diagnostic — not forward":"Timing unverified"));if(r.price_note)state.append(el("small",r.price_note));
    tr.append(model,stock,dates,state);for(const [value,unit]of[[r.stock_pct,"%"],[r.spy_pct,"%"],[r.active_pp," pp"]])tr.append(el("td",value===null?"—":pct(value,unit),`num ${value===null?"":value>=0?"positive":"negative"}`));body.append(tr);
  }
  if(!visible.length){const tr=el("tr"),td=el("td","No observations match these filters. Pending outcomes are not zero returns.");td.colSpan=7;tr.append(td);body.append(tr);}
  $("#outcome-caption").textContent=selected.status==="matured"?"Latest matured observations first":"Sorted by planned maturity, newest first · pending values remain blank";
  $("#outcome-summary").textContent=`Showing ${visible.length} of ${rows.length} matching observations · ${summary.matured_forward} matured forward observations across displayed models.`;
  $("#outcome-cutoff").textContent=`OUTCOMES THROUGH ${dateLabel(a.as_of).toUpperCase()}`;
  const primary=observations().filter(r=>r.id==="baseline"&&r.evidence==="forward");const matured=primary.filter(r=>r.status==="matured");
  const next=primary.filter(r=>r.status!=="matured").map(r=>r.exit).sort()[0];
  $("#primary-maturity").textContent=`Current production version: ${matured.length} matured forward observations${next?`; next scheduled maturity ${dateLabel(next)}`:""}. Earlier models’ results are not its track record.`;
  $("#archive-coverage").textContent=`Displaying ${summary.observations} observations: ${summary.forward} recorded before entry, ${summary.late_diagnostic} late diagnostics, ${summary.timestamp_unverified} with unverified timing. Forward outcomes: ${summary.matured_forward} matured, ${summary.pending_forward} pending, ${summary.missing_prices_forward} missing prices. Repeated revisions are not counted as additional trades. Historical public availability is not implied.`;
}
function renderPerformance(){
  $("#performance-rows").replaceChildren();const groups=new Map();
  for(const r of observations().filter(r=>r.evidence==="forward"&&r.status==="matured")){const key=[r.id,r.vintage,r.horizon].join("|");if(!groups.has(key))groups.set(key,[]);groups.get(key).push(r);}
  for(const rows of groups.values()){const r=rows[0],n=rows.length,tr=el("tr");tr.append(el("td",`${r.name} / ${r.vintage}`),el("td",`H${r.horizon}`),el("td",String(n),"num"),el("td",pct(rows.reduce((s,r)=>s+r.stock_pct,0)/n),"num"),el("td",pct(rows.reduce((s,r)=>s+r.active_pp,0)/n," pp"),"num"),el("td",`${rows.filter(r=>r.stock_pct>0).length}/${n}`,"num"),el("td",`${rows.filter(r=>r.active_pp>0).length}/${n}`,"num"));$("#performance-rows").append(tr);}
}
async function refresh(initial=false){
  if(refreshing)return;refreshing=true;$("#latest").disabled=true;$("#latest").textContent="Checking…";
  try{
    const response=await fetch(FEED+"?v="+Date.now(),{cache:"no-store"});if(!response.ok)throw Error("Feed unavailable");const next=await response.json();checkFeed(next);data=next;connected=true;
  }catch{
    connected=false;
    if(!data){try{const response=await fetch("snapshot.json");if(!response.ok)throw Error();data=await response.json();checkFeed(data);}catch{$("#notice").textContent="NO VERIFIED FEED — Published data could not be loaded. No new entry information is available.";$("#notice").className="notice error";$("#connection").textContent="Feed unavailable";refreshing=false;$("#latest").disabled=false;$("#latest").textContent="Retry feed";return;}}
  }
  $("#connection").textContent=connected?"Published feed connected":"Saved snapshot only";
  const wasLatest=!selectedDate||selectedDate===$("#date").options[0]?.value;
  $("#date").replaceChildren(...allDates().map(day=>{const opt=el("option",dateLabel(day)+(day===data.latest_date?" · latest":""));opt.value=day;return opt;}));
  if(wasLatest||!allDates().includes(selectedDate))selectedDate=data.latest_date;
  $("#date").value=selectedDate;$("#date").disabled=false;$("#latest").disabled=false;
  render();setupArchive();refreshing=false;$("#latest").textContent=selectedDate===data.latest_date?"Latest selected ✓":"Go to latest";
}
$("#date").addEventListener("change",e=>{selectDate(e.target.value);$("#latest").textContent=selectedDate===data.latest_date?"Latest selected ✓":"Go to latest";});
$("#latest").addEventListener("click",async()=>{selectedDate=null;await refresh();});
$("#research-toggle").addEventListener("click",()=>{const open=$("#research-toggle").getAttribute("aria-expanded")!=="true";$("#research-toggle").setAttribute("aria-expanded",String(open));$("#research-toggle").textContent=open?"Hide observations −":"Show observations +";$("#research-table").hidden=!open;});
$("#decision-month").addEventListener("change",renderDecisions);
for(const k of ["model","horizon","month","status","evidence","limit"])$("#outcome-"+k).addEventListener("change",renderEvidence);
$("#reset-outcomes").addEventListener("click",()=>{for(const [k,v]of Object.entries({model:"all",horizon:"all",month:"all",status:"matured",evidence:"forward",limit:"5"}))$("#outcome-"+k).value=v;renderEvidence();});
refresh(true);setInterval(()=>{if(!document.hidden)refresh();},300000);setInterval(()=>{if(data)render();},30000);
