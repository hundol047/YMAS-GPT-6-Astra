export const BASE=import.meta.env.VITE_API_BASE || (import.meta.env.DEV?'/api':'');

// credentials:'include' on every call (here and in streamSSE below) is the whole auth story on
// this side: in AUTH_MODE=oidc, POST /auth/session (backend/app/services/auth.py) exchanges an
// already-obtained bearer token for an HttpOnly synex_auth_session cookie ONCE; every request
// after that authenticates via that cookie automatically, the same way SMART's synex_session
// cookie already carries patient context. This app never stores a token in localStorage,
// sessionStorage, a URL, or React state -- there is no client-side token to store, since the
// browser only ever holds an opaque, non-readable session cookie. AUTH_MODE=demo (the default)
// needs none of this; every request just works, unchanged.
export async function api(path,body,signal,method,extraHeaders){
 const m=method||(body===undefined?'GET':'POST');
 const response=await fetch(BASE+path,{method:m,headers:{'Content-Type':'application/json',...extraHeaders},body:body===undefined?undefined:JSON.stringify(body),signal,credentials:'include'});
 if(!response.ok){let data;try{data=await response.json()}catch{}throw new Error(typeof data?.detail==='string'?data.detail:`요청 실패 (${response.status}). 서버 연결을 확인하십시오.`)}
 return response.json();
}

// Server-Sent Events, consumed via fetch+ReadableStream rather than the browser's native
// EventSource -- EventSource cannot send credentials/auth headers on a cross-origin request and
// has no way to carry a bearer token at all (and a token in the URL as a query param is exactly
// what's NOT done here, since that would leak into browser history/logs/proxies). fetch already
// carries the same-origin/CORS credentials (cookies) every other api() call does, so an
// authenticated SSE endpoint works the same way an authenticated JSON endpoint does.
function parseSSEChunk(chunk,onEvent){
 let event='message',data='';
 for(const line of chunk.split('\n')){
  if(line.startsWith('event:'))event=line.slice(6).trim();
  else if(line.startsWith('data:'))data+=line.slice(5).trim();
 }
 if(data)onEvent(event,data);
}

export async function streamSSE(path,{onEvent,signal}){
 const response=await fetch(BASE+path,{signal,credentials:'include'});
 if(!response.ok){let data;try{data=await response.json()}catch{}throw new Error(typeof data?.detail==='string'?data.detail:`요청 실패 (${response.status}). 서버 연결을 확인하십시오.`)}
 // Real browsers stream response.body incrementally; a test/bridge fetch that only implements
 // text() (no ReadableStream body -- see frontend/tests/setup.js) still works via the fallback
 // below, just without incremental delivery.
 if(!response.body?.getReader){
  const text=await response.text();
  for(const chunk of text.split('\n\n'))parseSSEChunk(chunk,onEvent);
  return;
 }
 const reader=response.body.getReader();const decoder=new TextDecoder();let buffer='';
 while(true){
  const {done,value}=await reader.read();
  if(done)break;
  buffer+=decoder.decode(value,{stream:true});
  let sep;
  while((sep=buffer.indexOf('\n\n'))!==-1){
   parseSSEChunk(buffer.slice(0,sep),onEvent);buffer=buffer.slice(sep+2);
  }
 }
}
