import {slotToTime} from "../utils/formatTime";
export default function EventTable({events=[]}) {
  return <div className="table-scroll"><table><thead><tr><th>Time</th><th>Type</th><th>Change</th><th>Confidence</th></tr></thead><tbody>{events.slice(0,30).map((event,index)=><tr key={`${event.timestamp}-${index}`}><td>{new Date(event.timestamp).toLocaleString()}</td><td>{event.event_type}</td><td>{event.change_kw} kW</td><td>{Math.round(event.confidence*100)}%</td></tr>)}</tbody></table>{events.length===0&&<p>No events passed the selected threshold.</p>}</div>;
}
