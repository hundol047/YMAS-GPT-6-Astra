export const BASE=import.meta.env.VITE_API_BASE || (import.meta.env.DEV?'/api':'');

export async function api(path,body,signal,method){
 const m=method||(body===undefined?'GET':'POST');
 const response=await fetch(BASE+path,{method:m,headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal});
 if(!response.ok){let data;try{data=await response.json()}catch{}throw new Error(typeof data?.detail==='string'?data.detail:`요청 실패 (${response.status}). 서버 연결을 확인하십시오.`)}
 return response.json();
}
