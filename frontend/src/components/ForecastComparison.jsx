export default function ForecastComparison({evaluation={},fallbackModel}) {
  const models=evaluation.models||{};
  return <article className="card"><h2>Automatic model comparison</h2><p>Chronological last-day holdout; lower MAE wins.</p><table><thead><tr><th>Model</th><th>MAE</th><th>RMSE</th><th>MAPE</th></tr></thead><tbody>{Object.entries(models).map(([name,m])=><tr className={name===evaluation.selected_model?"winner":""} key={name}><td>{name}</td><td>{m.mae_kw} kW</td><td>{m.rmse_kw} kW</td><td>{m.mape_percent??"—"}%</td></tr>)}</tbody></table><p><b>Selected:</b> {evaluation.selected_model||fallbackModel}</p>{evaluation.status!=="measured"&&<p>{evaluation.reason}</p>}</article>;
}
