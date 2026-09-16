import {afterAll} from 'vitest';
import {configure} from '@testing-library/react';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import path from 'node:path';
configure({asyncUtilTimeout:6000,getElementError:(message,container)=>new Error(message+'\nPAGE TEXT: '+container.textContent)});
const python=process.env.SYNEX_TEST_PYTHON||path.resolve('..','.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
const bridge=spawn(python,[path.resolve('..','scripts/api_test_bridge.py')],{stdio:['pipe','pipe','pipe']});
let nextId=0;const pending=new Map();
createInterface({input:bridge.stdout}).on('line',line=>{const r=JSON.parse(line);const request=pending.get(r.id);if(request){pending.delete(r.id);request.resolve({ok:r.status>=200&&r.status<300,status:r.status,json:async()=>JSON.parse(r.body),text:async()=>r.body})}});
bridge.on('error',err=>{for(const p of pending.values())p.reject(err);pending.clear()});
bridge.stderr.on('data',()=>{});
bridge.on('exit',()=>{for(const p of pending.values())p.reject(new Error('API bridge exited'));pending.clear()});
afterAll(()=>{bridge.stdin.end();bridge.kill()});
// Forwards options.headers to the bridge (beyond just method/body) so tests can exercise
// header-driven server behavior -- e.g. the Idempotency-Key header on medication order creation --
// through the same real backend/app.main path a browser fetch(..., {headers}) would use.
globalThis.fetch=(url,options={})=>new Promise((resolve,reject)=>{const id=++nextId;pending.set(id,{resolve,reject});bridge.stdin.write(JSON.stringify({id,path:url.replace(/^\/api/,''),method:options.method||'GET',body:options.body,headers:options.headers})+'\n')});
window.matchMedia=()=>({matches:true,addListener(){},removeListener(){},addEventListener(){},removeEventListener(){}});
globalThis.ResizeObserver=class {observe(){}unobserve(){}disconnect(){}};
// jsdom has no SSE implementation. Replay the actual FastAPI SSE response over stdio.
// No patient, rule, or model response is fabricated.
globalThis.EventSource=class extends EventTarget{
 constructor(url){super();this.closed=false;this.start(url)}
 async start(url){try{const r=await fetch(url);const text=await r.text();for(const block of text.split('\n\n')){if(this.closed)return;const lines=block.split('\n');const event=lines.find(l=>l.startsWith('event: '))?.slice(7),data=lines.find(l=>l.startsWith('data: '))?.slice(6);if(event)this.dispatchEvent(new MessageEvent(event,{data}));}}catch{if(!this.closed)this.onerror?.()}}
 close(){this.closed=true}
};
