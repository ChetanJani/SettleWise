export default function Loading({compact=false,label='Finding your next place'}){
 return <div className={`place-loading ${compact?'compact':''}`} role="status" aria-live="polite"><div className="loading-houses" aria-hidden="true">{[0,1,2].map(i=><svg key={i} viewBox="0 0 40 48" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" style={{'--delay':`${i*160}ms`}}><path d="M5 22 20 7l15 15v20H5Z"/><path d="M16 42V29h8v13M11 24h3m12 0h3"/></svg>)}</div><span>{label}</span></div>
}
