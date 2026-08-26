import {useState} from "react";
import FaultAlerts from "./components/FaultAlerts";
import LoadChart from "./components/LoadChart";
import ScenarioComparison from "./components/ScenarioComparison";
import TariffEditor from "./components/TariffEditor";
import UncertaintyPanel from "./components/UncertaintyPanel";
import {downloadReport,loadDemo,optimize,savePassport,uploadCsv} from "./services/api";

const slotToTime=slot=>slot>=96?"23:45":`${String(Math.floor(slot/4)).padStart(2,"0")}:${String((slot%4)*15).padStart(2,"0")}`;
const timeToSlot=time=>{const [hours,minutes]=time.split(":").map(Number);return hours*4+Math.round(minutes/15)};
const modeLabels={balanced:"Balanced",cost:"Lowest Cost",peak:"Peak Reducer",carbon:"Carbon-Aware"};

export default function App(){
  const [analysis,setAnalysis]=useState(null);
  const [passports,setPassports]=useState([]);
  const [tariff,setTariff]=useState([]);
  const [result,setResult]=useState(null);
  const [mode,setMode]=useState("balanced");
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");

  const runAnalysis=async operation=>{setBusy(true);setError("");setResult(null);try{const response=await operation();setAnalysis(response.data);setPassports(response.data.candidate_passports||[]);setTariff(response.data.tariff||[])}catch(exc){setError(exc.response?.data?.detail||exc.message)}finally{setBusy(false)}};
  const edit=(index,field,value)=>setPassports(items=>items.map((passport,itemIndex)=>itemIndex===index?{...passport,[field]:value}:passport));
  const setStatus=async(index,status)=>{const updated={...passports[index],status,verified:status==="confirmed"};setPassports(items=>items.map((passport,itemIndex)=>itemIndex===index?updated:passport));try{await savePassport(updated)}catch(exc){setError(exc.response?.data?.detail||exc.message)}};
  const runOptimizer=async()=>{if(!passports.some(passport=>passport.status==="confirmed"&&passport.criticality!=="critical")){setError("Confirm at least one non-critical Flexibility Passport first.");return}setBusy(true);setError("");try{const response=await optimize({forecast_kw:analysis.forecast_kw,forecast_lower_kw:analysis.forecast_lower_kw,forecast_upper_kw:analysis.forecast_upper_kw,solar_kw:analysis.solar_kw,tariff,passports,max_building_kw:20,mode,include_scenarios:true});setResult(response.data)}catch(exc){setError(exc.response?.data?.detail||exc.message)}finally{setBusy(false)}};
  const getReport=async()=>{const response=await downloadReport({result,source_label:analysis.source_label});const url=URL.createObjectURL(response.data);const anchor=document.createElement("a");anchor.href=url;anchor.download="FlexiGrid-Phase2-Optimization-Report.pdf";anchor.click();URL.revokeObjectURL(url)};

  return <main>
    <header><div><p className="eyebrow">HUMAN-VERIFIED ENERGY FLEXIBILITY</p><h1>FlexiGrid AI</h1><p>Adaptive discovery → uncertainty → digital twin → robust optimization</p></div><span className="status">● Phase 2.0 · Recommendation only</span></header>
    <section className="actions card"><button onClick={()=>runAnalysis(loadDemo)} disabled={busy}>Load 7-Day Demo</button><label className="upload">Upload CSV<input type="file" accept=".csv" onChange={event=>event.target.files[0]&&runAnalysis(()=>uploadCsv(event.target.files[0]))}/></label>{analysis&&<><select value={mode} onChange={event=>setMode(event.target.value)}>{Object.entries(modeLabels).map(([value,label])=><option value={value} key={value}>{label}</option>)}</select><button className="secondary" onClick={runOptimizer} disabled={busy}>Run Robust Optimization</button></>}{busy&&<span className="processing">Processing intelligence…</span>}{error&&<span className="error">{error}</span>}</section>

    {analysis&&<>
      <div className="notice"><b>{analysis.source_label.toUpperCase()}</b> · Results are forecasts and simulated estimates, not measured savings or equipment diagnoses.</div>
      <section className="metrics"><article><strong>{analysis.reading_count}</strong><span>15-minute readings</span></article><article><strong>{analysis.data_quality.quality_score}%</strong><span>data quality</span></article><article><strong>{analysis.events.length}</strong><span>adaptive events</span></article><article><strong>{passports.filter(p=>p.status==="confirmed").length}</strong><span>confirmed passports</span></article></section>

      <section className="card"><div className="titleline"><div><h2>Adaptive event discovery</h2><p>Thresholds adjust to local meter noise using rolling median absolute deviation.</p></div><span className="tag">{analysis.detection?.mode}</span></div><LoadChart data={analysis.readings} events={analysis.events}/></section>

      <section className="grid"><article className="card"><h2>Forecast model comparison</h2><p>Chronological last-day holdout; lower MAE is selected.</p><table><thead><tr><th>Model</th><th>MAE</th><th>RMSE</th><th>MAPE</th></tr></thead><tbody>{Object.entries(analysis.forecast_evaluation.models||{}).map(([name,metrics])=><tr className={name===analysis.forecast_evaluation.selected_model?"winner":""} key={name}><td>{name}</td><td>{metrics.mae_kw} kW</td><td>{metrics.rmse_kw} kW</td><td>{metrics.mape_percent??"—"}%</td></tr>)}</tbody></table><p><b>Selected:</b> {analysis.forecast_evaluation.selected_model||analysis.forecast_model}</p></article><UncertaintyPanel analysis={analysis}/></section>

      <FaultAlerts alerts={analysis.fault_alerts}/>

      <section className="card"><div className="titleline"><div><h2>Uncertainty-aware Flexibility Passports</h2><p>Confirm, edit or reject every candidate before optimization.</p></div><span className="tag">Human in the loop</span></div>{passports.map((passport,index)=><div className={`passport ${passport.status}`} key={passport.pattern_id}>
        <div><b>{passport.pattern_id}</b><small>{Math.round(passport.confidence*100)}% confidence · {passport.evidence_days||1} evidence days</small></div>
        <label>Load name<input value={passport.label} onChange={event=>edit(index,"label",event.target.value)}/></label>
        <label>Power kW<input type="number" step=".1" value={passport.estimated_power_kw} onChange={event=>edit(index,"estimated_power_kw",+event.target.value)}/></label>
        <label>Runtime<input type="time" value={slotToTime(passport.duration_slots)} onChange={event=>edit(index,"duration_slots",Math.max(1,timeToSlot(event.target.value)))}/></label>
        <label>Earliest start<input type="time" value={slotToTime(passport.earliest_start_slot)} onChange={event=>edit(index,"earliest_start_slot",timeToSlot(event.target.value))}/></label>
        <label>Latest finish<input type="time" value={slotToTime(passport.latest_finish_slot)} onChange={event=>edit(index,"latest_finish_slot",timeToSlot(event.target.value))}/></label>
        <label>Criticality<select value={passport.criticality} onChange={event=>edit(index,"criticality",event.target.value)}>{["low","medium","high","critical"].map(value=><option key={value}>{value}</option>)}</select></label>
        <div className="workflow"><button onClick={()=>setStatus(index,"confirmed")}>Confirm</button><button className="edit" onClick={()=>setStatus(index,"candidate")}>Save edit</button><button className="reject" onClick={()=>setStatus(index,"rejected")}>Reject</button></div>
        <small>Power range {passport.power_min_kw??passport.estimated_power_kw}–{passport.power_max_kw??passport.estimated_power_kw} kW · Duration {passport.duration_min_minutes||passport.duration_minutes}–{passport.duration_max_minutes||passport.duration_minutes} min · Start uncertainty ±{passport.start_uncertainty_minutes||15} min · <b>{passport.status}</b></small>
      </div>)}{passports.length===0&&<p>No recurring candidate passed the current adaptive confidence requirements.</p>}</section>

      <TariffEditor tariff={tariff} onChange={setTariff}/>

      <section className="card"><div className="titleline"><div><h2>Next-day forecast with uncertainty</h2><p>The amber upper bound is used for the building-demand constraint.</p></div><span className="tag">{analysis.forecast_model}</span></div><LoadChart forecast={analysis.forecast_kw} lower={analysis.forecast_lower_kw} upper={analysis.forecast_upper_kw} optimized={result?.optimized_load_kw}/></section>

      {result&&<>
        <section className="card"><div className="titleline"><div><h2>Before versus optimized</h2><p>{result.solver_engine} · Status: {result.solver_status}</p></div><button onClick={getReport}>Download PDF Report</button></div><table><thead><tr><th>Metric</th><th>Before</th><th>After</th><th>Difference</th></tr></thead><tbody>{[["Peak demand (kW)","peak_kw"],["Cost units","energy_cost_units"],["Solar used (kWh)","solar_used_kwh"],["Grid energy (kWh)","grid_energy_kwh"]].map(([label,key])=><tr key={key}><td>{label}</td><td>{result.before[key]}</td><td>{result.after[key]}</td><td>{result.differences[key]}</td></tr>)}</tbody></table></section>
        <ScenarioComparison scenarios={result.scenarios}/>
        <section className="recommendations"><h2>Explainable recommendations</h2>{result.schedule.map(item=><article className="card explanation" key={item.pattern_id}><div><span className="tag">{modeLabels[mode]}</span><h3>{item.label}</h3><p>{item.explanation}</p><div className="chips">{item.constraints_respected.map(value=><span key={value}>✓ {value}</span>)}</div></div><b>{item.original_time} → {item.recommended_time}</b></article>)}{result.schedule.length===0&&<div className="notice">No feasible shift was found under the upper forecast bound and current constraints.</div>}</section>
        <section className="card"><h2>24-hour schedule timeline</h2><div className="timeline-axis">{[0,6,12,18,24].map(hour=><span key={hour}>{String(hour).padStart(2,"0")}:00</span>)}</div>{result.schedule.map(item=><div className="timeline-row" key={item.pattern_id}><b>{item.label}</b><div className="track"><span className="bar original" style={{left:`${item.original_start_slot/96*100}%`,width:`${item.duration_slots/96*100}%`}}>Original</span><span className="bar optimized" style={{left:`${item.recommended_start_slot/96*100}%`,width:`${item.duration_slots/96*100}%`}}>New</span></div></div>)}</section>
      </>}
    </>}
  </main>;
}
