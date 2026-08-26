export default function CsvUploader({onUpload, disabled=false}) {
  return <label className="upload">Upload CSV<input type="file" accept=".csv,text/csv" disabled={disabled} onChange={event=>{
    const file=event.target.files?.[0]; if(file) onUpload(file); event.target.value="";
  }}/></label>;
}
