// Korean initial-consonant (초성) search helper. Pure Unicode arithmetic, no dependency:
// a complete Hangul syllable sits at 0xAC00 + (chosung*21 + jungsung)*28 + jongsung.
const CHOSUNG = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ'];
const CHOSUNG_SET = new Set(CHOSUNG);

export function toChosung(text){
 let out='';
 for(const ch of text){
  const code=ch.codePointAt(0)-0xAC00;
  out+=(code>=0&&code<=11171)?CHOSUNG[Math.floor(code/588)]:ch;
 }
 return out;
}

// True only for non-empty strings made entirely of chosung jamo (e.g. "ㅇㅅㅍㄹ") -- lets normal
// text (Korean words, English, drug ids) fall through to a plain substring match instead.
export function isChosungQuery(text){
 return text.length>0&&[...text].every(ch=>CHOSUNG_SET.has(ch));
}

export function matchesQuery(query,...fields){
 const q=query.trim().toLowerCase();
 if(!q)return true;
 if(isChosungQuery(query))return fields.some(f=>toChosung(f).includes(query));
 return fields.some(f=>f.toLowerCase().includes(q));
}
