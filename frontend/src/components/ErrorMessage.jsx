export default function ErrorMessage({message}) {return message?<div className="error-box" role="alert"><b>Unable to continue</b><span>{message}</span></div>:null}
