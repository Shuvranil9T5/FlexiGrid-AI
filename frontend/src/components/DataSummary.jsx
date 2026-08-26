export default function DataSummary({analysis,confirmed=0}) {
  const metrics=[[analysis.reading_count,"15-minute readings"],[`${analysis.data_quality.quality_score}%`,"data quality"],[analysis.events.length,"START/STOP events"],[confirmed,"confirmed passports"]];
  return <section className="metrics">{metrics.map(([value,label])=><article key={label}><strong>{value}</strong><span>{label}</span></article>)}</section>;
}
