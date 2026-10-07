import {useEffect,useRef} from 'react';
import {X} from 'lucide-react';
export default function Modal({title,onClose,children,wide=false,className=''}){
  const ref=useRef(null);const closeRef=useRef(onClose);closeRef.current=onClose;
  useEffect(()=>{
    const previous=document.activeElement;const overflow=document.body.style.overflow;
    document.body.style.overflow='hidden';ref.current.showModal();
    history.pushState({swOverlay:true},'',location.href);
    const back=()=>closeRef.current();window.addEventListener('popstate',back);
    return ()=>{window.removeEventListener('popstate',back);document.body.style.overflow=overflow;if(history.state?.swOverlay)history.back();previous?.focus?.()};
  },[]);
  return <dialog ref={ref} className={`modal ${wide?'wide':''} ${className}`} onCancel={e=>{e.preventDefault();onClose()}} onClick={e=>{if(e.target===e.currentTarget){const r=e.currentTarget.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)onClose()}}} aria-labelledby="dialog-title"><header className="modal-header"><h2 id="dialog-title">{title}</h2><button className="icon-button" onClick={onClose} aria-label="Close panel"><X size={20}/></button></header>{children}</dialog>;
}
