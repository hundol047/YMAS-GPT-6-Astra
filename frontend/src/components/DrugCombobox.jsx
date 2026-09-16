import React,{useState,useRef,useEffect,useId} from 'react';
import {matchesQuery} from '../lib/chosung';

// Searchable drug picker: type a name, an id, or Korean 초성 (e.g. "ㅇㅅㅍㄹ" matches 아스피린).
// Selecting a result is the only way to set a value -- free text alone never becomes drug_id, so
// the caller always gets a real catalog entry or ''.
export default function DrugCombobox({catalog,value,onChange,exclude,label,disabled,placeholder}){
 const selected=catalog.find(d=>d.id===value);
 const selectedText=selected?`${selected.name_ko} · ${selected.id}`:'';
 const [text,setText]=useState(selectedText);
 const [open,setOpen]=useState(false);
 const [activeIndex,setActiveIndex]=useState(-1);
 const rootRef=useRef(null);
 const listId=useId();

 useEffect(()=>{setText(selectedText)},[selectedText]);

 useEffect(()=>{
  function onDocPointerDown(e){if(rootRef.current&&!rootRef.current.contains(e.target))setOpen(false)}
  document.addEventListener('mousedown',onDocPointerDown);
  return ()=>document.removeEventListener('mousedown',onDocPointerDown);
 },[]);

 const pool=catalog.filter(d=>!exclude?.has(d.id));
 const searching=text.trim()&&text!==selectedText;
 const results=(searching?pool.filter(d=>matchesQuery(text,d.name_ko,d.id,d.cls_ko||'',d.group_ko||'')):pool).slice(0,30);

 function choose(d){onChange(d.id);setText(`${d.name_ko} · ${d.id}`);setOpen(false);setActiveIndex(-1)}
 function onKeyDown(e){
  if(!open){if(e.key==='ArrowDown'||e.key==='Enter')setOpen(true);return}
  if(e.key==='ArrowDown'){e.preventDefault();setActiveIndex(i=>Math.min(i+1,results.length-1))}
  else if(e.key==='ArrowUp'){e.preventDefault();setActiveIndex(i=>Math.max(i-1,0))}
  else if(e.key==='Enter'){if(activeIndex>=0&&results[activeIndex]){e.preventDefault();choose(results[activeIndex])}}
  else if(e.key==='Escape'){setOpen(false)}
 }

 return <div className="drug-combobox" ref={rootRef}>
 <input role="combobox" aria-expanded={open} aria-controls={listId} aria-autocomplete="list" aria-label={label}
  value={text} disabled={disabled} placeholder={placeholder||'약물명 입력 · 초성 검색 가능'} autoComplete="off"
  onChange={e=>{setText(e.target.value);if(value)onChange('');setOpen(true);setActiveIndex(-1)}}
  onFocus={()=>setOpen(true)} onKeyDown={onKeyDown}/>
 {open&&<ul role="listbox" id={listId} className="drug-combobox-list">
  {results.length
   ?results.map((d,i)=><li key={d.id} role="option" aria-selected={i===activeIndex}
     className={i===activeIndex?'active':''} onMouseDown={e=>{e.preventDefault();choose(d)}}>
     <b>{d.name_ko}</b><span>{d.group_ko} · {d.id}</span>
    </li>)
   :<li className="drug-combobox-empty" aria-disabled="true">검색 결과가 없습니다</li>}
 </ul>}
 </div>;
}
