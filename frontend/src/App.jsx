import { useState } from "react";
import LoadChart from "./components/LoadChart";
import { downloadReport, loadDemo, optimize, savePassport, uploadCsv } from "./services/api";

const slotToTime = slot => slot >= 96 ? "23:45" : `${String(Math.floor(slot/4)).padStart(2,"0")}:${String((slot%4)*15).padStart(2,"0")}`;
const timeToSlot = time => { const [h,m] = time.split(":").map(Number); return h*4 + Math.round(m/15); };
const MODEL_ORDER = ["Seasonal baseline", "Random Forest", "LightGBM", "TFT"];

const comparisonRows = analysis => {
  const evaluation = analysis.forecast_evaluation || {};
  const measured = evaluation.models || {};
  const unavailable = evaluation.unavailable_models || {};
  const capabilities = analysis.model_capabilities || {};
  const knownNames = new Set([...MODEL_ORDER, ...Object.keys(measured), ...Object.keys(unavailable), ...Object.keys(capabilities)]);
  return [...knownNames]
    .sort((a,b) => {
      const aIndex = MODEL_ORDER.indexOf(a), bIndex = MODEL_ORDER.indexOf(b);
      return (aIndex < 0 ? MODEL_ORDER.length : aIndex) - (bIndex < 0 ? MODEL_ORDER.length : bIndex) || a.localeCompare(b);
    })
    .map(name => {
      const metrics = measured[name];
      const reason = unavailable[name];
      const capability = capabilities[name];
      let status = "Not evaluated for this dataset";
      if (metrics) status = name === evaluation.selected_model ? "Selected" : "Evaluated";
      else if (reason) status = reason;
      else if (capability && !capability.available) status = capability.reason || "Setup needed";
      return {name, metrics, status};
    });
};

export default function App() {
  const [analysis,setAnalysis]=useState(null), [passports,setPassports]=useState([]), [result,setResult]=useState(null);
  const [mode,setMode]=useState("balanced"), [busy,setBusy]=useState(false), [error,setError]=useState("");
  const run=async operation=>{setBusy(true);setError("");setResult(null);try{const r=await operation();setAnalysis(r.data);setPassports(r.data.candidate_passports||[]);}catch(e){setError(e.response?.data?.detail||e.message);}finally{setBusy(false);}};
  const edit=(i,field,value)=>setPassports(items=>items.map((p,index)=>index===i?{...p,[field]:value}:p));
  const setStatus=async(i,status)=>{const updated={...passports[i],status,verified:status==="confirmed"};edit(i,"status",status);setPassports(items=>items.map((p,index)=>index===i?updated:p));try{await savePassport(updated);}catch(e){setError(e.response?.data?.detail||e.message);}};
  const runOptimizer=async()=>{if(!passports.some(p=>p.status==="confirmed"&&p.criticality!=="critical")){setError("Confirm at least one non-critical Flexibility Passport first.");return;}setBusy(true);setError("");try{const r=await optimize({forecast_kw:analysis.forecast_kw,solar_kw:analysis.solar_kw,tariff:analysis.tariff,passports,max_building_kw:20,mode});setResult(r.data);}catch(e){setError(e.response?.data?.detail||e.message);}finally{setBusy(false);}};
  const getReport=async()=>{const r=await downloadReport({result,source_label:analysis.source_label});const url=URL.createObjectURL(r.data);const a=document.createElement("a");a.href=url;a.download="FlexiGrid-Optimization-Report.pdf";a.click();URL.revokeObjectURL(url);};
  return <main>
    <header><div><p className="eyebrow">REAL-DATA · ADVANCED FORECASTING · HUMAN-VERIFIED FLEXIBILITY</p><h1>FlexiGrid AI 2.0</h1><p>I-BLEND/UCI ingestion → LightGBM/TFT comparison → Flexibility Passports → optimized schedule</p></div><span className="status">● Recommendation only</span></header>
    <section className="actions card"><button onClick={()=>run(loadDemo)} disabled={busy}>Load 7-Day Demo</button><label className="upload">Upload CSV<input type="file" accept=".csv" onChange={e=>e.target.files[0]&&run(()=>uploadCsv(e.target.files[0]))}/></label>{analysis&&<><select value={mode} onChange={e=>setMode(e.target.value)}><option value="balanced">Balanced</option><option value="cost">Lowest Cost</option><option value="peak">Peak Reducer</option><option value="carbon">Carbon-Aware</option></select><button className="secondary" onClick={runOptimizer}>Optimize Confirmed Loads</button></>}{busy&&<span>Processing…</span>}{error&&<span className="error">{error}</span>}</section>
    {analysis&&<><div className="notice"><b>{analysis.source_label.toUpperCase()}</b> · Forecasts and simulated estimates are not measured savings.</div>
      <section className="metrics"><article><strong>{analysis.reading_count}</strong><span>15-minute readings</span></article><article><strong>{analysis.data_quality.quality_score}%</strong><span>data quality</span></article><article><strong>{analysis.forecast_model}</strong><span>holdout winner</span></article><article><strong>{passports.filter(p=>p.status==="confirmed").length}</strong><span>confirmed passports</span></article></section>
      <section className="card"><div className="titleline"><h2>Date-based aggregate load with event markers</h2><span className="tag">{analysis.source_label}</span></div><LoadChart data={analysis.readings} events={analysis.events}/></section>
      <section className="grid"><article className="card"><h2>Automatic model comparison</h2><p>Chronological final-day holdout; the lowest measured MAE wins.</p><table><thead><tr><th>Model</th><th>MAE</th><th>RMSE</th><th>MAPE</th><th>Status</th></tr></thead><tbody>{comparisonRows(analysis).map(({name,metrics,status})=><tr className={name===analysis.forecast_evaluation.selected_model?"winner":""} key={name}><td>{name}</td><td>{metrics?`${metrics.mae_kw} kW`:"—"}</td><td>{metrics?`${metrics.rmse_kw} kW`:"—"}</td><td>{metrics&&metrics.mape_percent!=null?`${metrics.mape_percent}%`:"—"}</td><td className={metrics?"ready":"pending"}>{status}</td></tr>)}</tbody></table><p><b>Selected:</b> {analysis.forecast_evaluation.selected_model||analysis.forecast_model}</p></article><article className="card"><h2>Advanced model readiness</h2>{MODEL_ORDER.map(name=>[name,analysis.model_capabilities?.[name]]).filter(([,item])=>item).map(([name,item])=><div className="row" key={name}><span>{name}<small>{item.type}</small></span><b className={item.available?"ready":"pending"}>{item.available?"Ready":"Setup needed"}</b></div>)}</article></section>
      <section className="card"><div className="titleline"><div><h2>Flexibility Passport workflow</h2><p>Times are human-readable. Runtime is inferred by START-to-STOP matching and remains editable.</p></div><span className="tag">Confirm · Edit · Reject</span></div>{passports.map((p,i)=><div className={`passport ${p.status}`} key={p.pattern_id}>
        <div><b>{p.pattern_id}</b><small>{Math.round(p.confidence*100)}% confidence · {p.occurrences} occurrences</small></div>
        <label>Load name<input value={p.label} onChange={e=>edit(i,"label",e.target.value)}/></label>
        <label>Power<input type="number" step=".1" value={p.estimated_power_kw} onChange={e=>edit(i,"estimated_power_kw",+e.target.value)}/></label>
        <label>Runtime<input type="time" value={slotToTime(p.duration_slots)} onChange={e=>edit(i,"duration_slots",Math.max(1,timeToSlot(e.target.value)))}/></label>
        <label>Earliest start<input type="time" value={slotToTime(p.earliest_start_slot)} onChange={e=>edit(i,"earliest_start_slot",timeToSlot(e.target.value))}/></label>
        <label>Latest finish<input type="time" value={slotToTime(p.latest_finish_slot)} onChange={e=>edit(i,"latest_finish_slot",timeToSlot(e.target.value))}/></label>
        <label>Criticality<select value={p.criticality} onChange={e=>edit(i,"criticality",e.target.value)}><option>low</option><option>medium</option><option>high</option><option>critical</option></select></label>
        <div className="workflow"><button onClick={()=>setStatus(i,"confirmed")}>Confirm</button><button className="edit" onClick={()=>setStatus(i,"candidate")}>Save edit</button><button className="reject" onClick={()=>setStatus(i,"rejected")}>Reject</button></div>
        <small>Typical {slotToTime(p.typical_start_slot)} · inferred runtime {p.duration_minutes||p.duration_slots*15} min from {p.duration_observations||0} matched cycles · status: <b>{p.status}</b></small>
      </div>)}</section>
      <section className="card"><div className="titleline"><h2>Next-day forecast and optimized estimate</h2><span className="tag">{analysis.forecast_model}</span></div><LoadChart forecast={analysis.forecast_kw} optimized={result?.optimized_load_kw}/></section>
      {result&&<><section className="card"><div className="titleline"><h2>Before vs After</h2><button onClick={getReport}>Download PDF Report</button></div><table><thead><tr><th>Metric</th><th>Before</th><th>After</th><th>Difference</th></tr></thead><tbody>{[["Peak demand (kW)","peak_kw"],["Cost units","energy_cost_units"],["Solar used (kWh)","solar_used_kwh"]].map(([label,key])=><tr key={key}><td>{label}</td><td>{result.before[key]}</td><td>{result.after[key]}</td><td>{result.differences[key]}</td></tr>)}</tbody></table></section>
      <section className="recommendations"><h2>Recommendation explanations</h2>{result.schedule.map(item=><article className="card explanation" key={item.pattern_id}><div><span className="tag">{mode}</span><h3>{item.label}</h3><p>{item.explanation}</p><div className="chips">{item.constraints_respected.map(c=><span key={c}>✓ {c}</span>)}</div></div><b>{item.original_time} → {item.recommended_time}</b></article>)}</section>
      <section className="card"><h2>24-hour schedule timeline</h2><div className="timeline-axis">{[0,6,12,18,24].map(h=><span key={h}>{String(h).padStart(2,"0")}:00</span>)}</div>{result.schedule.map(item=><div className="timeline-row" key={item.pattern_id}><b>{item.label}</b><div className="track"><span className="bar original" style={{left:`${item.original_start_slot/96*100}%`,width:`${item.duration_slots/96*100}%`}}>Original</span><span className="bar optimized" style={{left:`${item.recommended_start_slot/96*100}%`,width:`${item.duration_slots/96*100}%`}}>New</span></div></div>)}</section></>}
    </>}</main>;
}
