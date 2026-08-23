import { CartesianGrid, Legend, Line, LineChart, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function LoadChart({data,events=[],forecast,optimized}) {
  const rows=forecast?forecast.map((value,slot)=>({time:`${String(Math.floor(slot/4)).padStart(2,"0")}:${String((slot%4)*15).padStart(2,"0")}`,forecast:value,optimized:optimized?.[slot]})):data.map(item=>({time:item.timestamp,power:item.power_kw}));
  const powers=new Map((data||[]).map(item=>[item.timestamp,item.power_kw]));
  const formatTick=value=>forecast?value:new Date(value).toLocaleString(undefined,{month:"short",day:"numeric",hour:"2-digit"});
  return <ResponsiveContainer width="100%" height={340}><LineChart data={rows}><CartesianGrid strokeDasharray="3 3" stroke="#243652"/><XAxis dataKey="time" stroke="#94a3b8" minTickGap={55} tickFormatter={formatTick}/><YAxis stroke="#94a3b8" unit=" kW"/><Tooltip labelFormatter={value=>forecast?value:new Date(value).toLocaleString()} contentStyle={{background:"#111d31",border:"1px solid #345"}}/><Legend/>
    {forecast?<Line name="Forecast baseline" type="monotone" dataKey="forecast" stroke="#60a5fa" dot={false}/>:<Line name="Aggregate power" type="monotone" dataKey="power" stroke="#34d399" dot={false}/>}
    {optimized&&<Line name="Optimized estimate" type="monotone" dataKey="optimized" stroke="#fbbf24" dot={false}/>}
    {!forecast&&events.slice(0,80).map((event,i)=><ReferenceDot key={i} x={event.timestamp} y={powers.get(event.timestamp)} r={3} fill={event.event_type==="START"?"#60a5fa":"#fb7185"} stroke="none"/>)}
  </LineChart></ResponsiveContainer>;
}
