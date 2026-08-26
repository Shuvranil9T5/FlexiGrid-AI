const WINDOWS = [
  {key:"offPeak",label:"Off-peak",detail:"00:00–08:00 and 22:00–24:00",slots:[...Array(32).keys(),...Array.from({length:8},(_,i)=>88+i)]},
  {key:"day",label:"Day rate",detail:"08:00–18:00",slots:Array.from({length:40},(_,i)=>32+i)},
  {key:"peak",label:"Peak rate",detail:"18:00–22:00",slots:Array.from({length:16},(_,i)=>72+i)},
];

export default function TariffEditor({tariff,onChange}) {
  const rate=window=>Number(tariff?.[window.slots[0]]??0);
  const update=(window,value)=>{const next=[...(tariff||Array(96).fill(0))];window.slots.forEach(slot=>{next[slot]=Math.max(0,Number(value)||0)});onChange(next)};
  return <section className="card tariff-card"><div className="titleline"><div><h2>India-ready tariff editor</h2><p>Edit the demonstration time-of-day rates before optimization.</p></div><span className="tag">₹/kWh configurable</span></div><div className="tariff-grid">{WINDOWS.map(window=><label key={window.key}><span>{window.label}<small>{window.detail}</small></span><input type="number" min="0" step="0.1" value={rate(window)} onChange={event=>update(window,event.target.value)}/></label>)}</div></section>;
}
