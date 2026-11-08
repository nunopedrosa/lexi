'use strict';
const chat=document.querySelector('#chat'),form=document.querySelector('#form'),input=document.querySelector('#question');
const dialog=document.querySelector('#options'),external=document.querySelector('#external');
let meta=null,lastWord='',lastQuery=null,lastEntry=null,lastSenseOffset=0;const cache=new Map();let regionalData=null;
async function getRegional(){return regionalData ||= await (await fetch('data/regional.json')).json()}
function regionInfo(word){return regionalData?.terms?.[norm(word)]||null}
function regionExplanation(word){const r=regionInfo(word);if(!r)return null;if(r.pt)return 'No sentido de '+r.sense+', no português europeu usa-se «'+r.pt+'». '+r.note;if(r.br)return 'No sentido de '+r.sense+', no português do Brasil também se usa «'+r.br+'». '+r.note;return null}

const norm=s=>(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const clean=s=>s.replace(/[?!.,;:]+$/g,'').trim();
function add(message,who='bot',word=''){const d=document.createElement('div');d.className='bubble '+who;d.textContent=message;if(word&&external.checked){const p=document.createElement('div');p.className='links';const a=document.createElement('a');a.href='https://dicionario.priberam.org/'+encodeURIComponent(word);a.target='_blank';a.rel='noopener noreferrer';a.textContent='Consultar no Priberam ↗';p.append(a);d.append(p)}chat.append(d);chat.scrollIntoView({block:'end',behavior:'smooth'});}
// Dictionary text remains intact; individual words can be explored by tapping.
// Build DOM nodes rather than interpreting dictionary text as HTML.
async function openLinkedWord(word){
 add(word,'user');
 try{await definition(word)}catch(err){console.error(err);add('Não consegui abrir a definição de «'+word+'».')}
}
function appendLinkedText(parent,text){
 const parts=String(text).split(/([\p{L}]+(?:[’'-][\p{L}]+)*)/u);
 for(const part of parts){
  if(!part)continue;
  if(/^[\p{L}]+(?:[’'-][\p{L}]+)*$/u.test(part)){
   const b=document.createElement('button');b.type='button';b.className='definition-word';
   b.textContent=part;b.setAttribute('aria-label','Consultar «'+part+'»');
   b.addEventListener('click',()=>openLinkedWord(part));parent.append(b);
  }else parent.append(document.createTextNode(part));
 }
}
function addDefinitionText(message,headword){
 const d=document.createElement('div');d.className='bubble bot';
 appendLinkedText(d,message);
 if(headword&&external.checked){
  const p=document.createElement('div');p.className='links';const a=document.createElement('a');
  a.href='https://dicionario.priberam.org/'+encodeURIComponent(headword);
  a.target='_blank';a.rel='noopener noreferrer';a.textContent='Consultar no Priberam ↗';
  p.append(a);d.append(p);
 }
 chat.append(d);chat.scrollIntoView({block:'end',behavior:'smooth'});
}
function appendMorePrompt(parent,suffix){
 if(!suffix)return;
 const tail=document.createElement('div');
 const marker='«mais»';const at=suffix.indexOf(marker);
 if(at<0){tail.textContent=suffix;parent.append(tail);return}
 tail.append(document.createTextNode(suffix.slice(0,at)));
 const b=document.createElement('button');b.type='button';b.className='inline-action';
 b.textContent='mais';b.setAttribute('aria-label','Mostrar mais palavras');
 b.addEventListener('click',async()=>{
  add('mais','user');
  try{await handleQuestion('mais')}catch(err){console.error(err);add('Não consegui mostrar mais palavras.')}
 });
 tail.append(document.createTextNode('«'));tail.append(b);tail.append(document.createTextNode('»'+suffix.slice(at+marker.length)));
 parent.append(tail);
}
// Search results are interactive: select a word to read its dictionary entry.
function addWordResults(prefix,words,suffix=''){
 const d=document.createElement('div');d.className='bubble bot';
 const intro=document.createElement('div');intro.textContent=prefix;d.append(intro);
 const list=document.createElement('div');list.className='word-results';
 words.forEach((word,i)=>{
  if(i){const sep=document.createElement('span');sep.textContent=' · ';sep.setAttribute('aria-hidden','true');list.append(sep)}
  const b=document.createElement('button');b.type='button';b.className='word-link';b.textContent=word;
  b.setAttribute('aria-label','Consultar o significado de '+word);
  b.addEventListener('click',()=>openLinkedWord(word));
  list.append(b);
 });d.append(list);
 appendMorePrompt(d,suffix);
 chat.append(d);chat.scrollIntoView({block:'end',behavior:'smooth'});
}
// A word search excludes isolated letters and recognisable abbreviations.
// Dictionary lookups remain unrestricted; do not reject short real words such as 'pá'.
function isSearchableWord(row){
 const word=row[0];
 if([...word].length<2)return false;
 if(!/^\p{L}+$/u.test(word))return false;
 if(word===word.toUpperCase() && word!==word.toLowerCase())return false;
 const grammar=String(row[1]||'').toLowerCase();
 if(/\b(?:abbr|abrev|sigla|acr[oó]nimo|symbol|s[ií]mbolo)\b/i.test(grammar))return false;
 return true;
}
async function getMeta(){return meta ||= await (await fetch('data/meta.json')).json()}
async function shard(k){if(cache.has(k))return cache.get(k);const m=await getMeta();if(!m.keys.includes(k))return [];const data=await (await fetch('data/'+k+'.json')).json();cache.set(k,data);return data}
function keyOf(w){const x=norm(w)[0];return x&&/[a-z]/.test(x)?x:'_'}
async function find(w){const rows=await shard(keyOf(w));return rows.find(r=>norm(r[0])===norm(w))}
function getWord(q){let m=q.match(/(?:significa|significado (?:de|da|do)|define|defini[cç][aã]o (?:de|da|do)|o que (?:é|e|quer dizer)|quem é|quem e)\s+(?:a palavra\s+|o termo\s+|um\s+|uma\s+)?["“«']?([\p{L}-]+)/iu);if(m)return m[1];m=q.match(/^["“«']?([\p{L}-]+)["”»']?\??$/u);return m?m[1]:null}
function senseList(row){
 // Retain every sense actually shipped with the dictionary, including regional ones.
 // Curated editorial summaries do not replace source senses.
 const senses=(row[2]||[]).map((raw,index)=>({
  index:index+1,text:raw[0]||'',region:raw[1]||'unmarked',flags:raw[2]||[],
  suggestion:raw[3]?.ptpt_suggestion||null,curated:raw[1]==='curated'
 }));
 const isBrazilTerm=!!regionInfo(row[0])?.pt;
 const rank=s=>s.curated?0:s.region==='BR'?(isBrazilTerm?1:3):s.flags.some(f=>/possível PT-BR|planejad|usuário|ônibus|aplicativo/i.test(f))?2:1;
 return senses.sort((a,b)=>rank(a)-rank(b)||a.index-b.index);
}
function displaySenses(offset=0){
 if(!lastEntry)return;
 const row=lastEntry,all=senseList(row),page=all.slice(offset,offset+3);
 if(!page.length){add('Já mostrei todas as aceções disponíveis para «'+row[0]+'».');return}
 const lines=page.map(s=>{
  const tag=s.curated?' [redação editorial PT-PT]':s.region==='BR'?' [uso do Brasil]':s.region==='PT'?' [uso de Portugal]':'';
  const warning=!s.curated&&s.flags.some(f=>/adaptação automática/i.test(f))?' [adaptação PT-PT automática, por rever]':'';
  return s.index+'. '+s.text+tag+warning;
 });
 const regional=offset===0?regionExplanation(row[0]):null;
 if(regional)lines.push(regional);
 if(offset+3<all.length)lines.push('Há mais aceções. Escreve «outros significados».');
 addDefinitionText('«'+row[0]+'»'+(row[1]?' ('+row[1]+')':'')+'\n'+lines.join('\n'),row[0]);
 lastSenseOffset=offset+page.length;
}
// StarDict .syn aliases link a written form to one or more headwords.
const formsCache=new Map();
async function formShard(k){
 if(formsCache.has(k))return formsCache.get(k);
 const manifest=await (await fetch('data/forms-meta.json')).json();
 if(!manifest.shards.includes(k))return [];
 const response=await fetch('data/forms/'+k+'.json');
 if(!response.ok)throw Error('Índice de formas indisponível');
 const rows=await response.json();formsCache.set(k,rows);return rows;
}
async function resolveForm(w){
 const rows=await formShard(keyOf(w));
 const target=norm(w);
 const matches=rows.filter(r=>norm(r[0])===target);
 const headwords=[...new Set(matches.flatMap(r=>r[1]))];
 return headwords;
}
async function definition(w){
 await Promise.all([getMeta(),getRegional()]);const row=await find(w);
 if(!row){
  const heads=await resolveForm(w);
  if(!heads.length){add('Não encontrei «'+w+'» no dicionário. Experimenta outra forma da palavra.');return}
  const available=[];
  for(const h of heads){const entry=await find(h);if(entry)available.push(entry)}
  if(!available.length){add('Encontrei «'+w+'» no índice de formas, mas não consegui abrir a entrada correspondente.');return}
  // Ambiguous forms are not arbitrarily assigned to one headword.
  if(available.length>1){add('«'+w+'» pode corresponder a várias entradas: '+available.map(r=>'«'+r[0]+'»').join(', ')+'. Escreve a palavra que queres consultar.');return}
  lastWord=available[0][0];lastEntry=available[0];lastSenseOffset=0;
  add('«'+w+'» é uma forma associada à entrada «'+lastWord+'».');
  displaySenses(0);return;
 }
 lastWord=row[0];lastEntry=row;lastSenseOffset=0;displaySenses(0);
}
function parseSearch(q){let start=q.match(/(?:come[cç](?:adas?|am)|iniciad[ao]s?)\s+(?:(?:pela?|por|com)\s+)?(?:letra\s+)?["“«']?([a-záàâãéêíóôõúç])/i);let end=q.match(/(?:acab(?:am|adas?|em)|termin(?:am|adas?|em))\s+(?:em\s+|por\s+)?["“«']?([\p{L}]+)/iu);let length=q.match(/(?:com|tenham|t[eê]m)\s+(\d+|tr[eê]s|quatro|cinco|seis|sete|oito|nove|dez|duas|dois|uma|um)\s+letras?/i);let syll=q.match(/(\d+|tr[eê]s|quatro|cinco|seis|sete|oito|duas|dois|uma|um)\s+s[ií]labas?/i);let amount=q.match(/(?:diz(?:-me)?|mostra(?:-me)?)\s+(\d+)\s+palavras?/i);let isSearch=/palavras?|come[cç]|acab|termin|letras?|s[ií]labas?/i.test(q);if(!isSearch)return null;const numbers={'um':1,'uma':1,'dois':2,'duas':2,'três':3,'tres':3,'quatro':4,'cinco':5,'seis':6,'sete':7,'oito':8,'nove':9,'dez':10};const number=x=>x?numbers[norm(x)]||Number(x):null;return {start:start?norm(start[1]):null,end:end?norm(end[1]):null,length:length?number(length[1]):null,syll:syll?number(syll[1]):null,amount:amount?Math.min(30,number(amount[1])):10};}
const syllCache=new Map();
async function syllShard(k){
 if(syllCache.has(k))return syllCache.get(k);
 const r=await fetch('data/syllables/'+k+'.json');
 if(!r.ok)throw Error('Dados silábicos indisponíveis');
 const data=await r.json();syllCache.set(k,data);return data;
}
async function search(q){let p=parseSearch(q);if(!p)return false;const previousQuery=lastQuery;if(previousQuery&&/^(?:e |agora |mais |s[oó] )/i.test(q)){p.start=p.start??previousQuery.start;p.end=p.end??previousQuery.end;p.length=p.length??previousQuery.length;p.syll=p.syll??previousQuery.syll;}lastQuery=p;const keys=p.start?[keyOf(p.start)]: (await getMeta()).keys;let matches=[];for(const k of keys){const syl=p.syll?new Map((await syllShard(k)).map(r=>[r[0],r[1]])):null;for(const r of await shard(k)){let w=norm(r[0]);if(!isSearchableWord(r))continue;if(p.start&&!w.startsWith(p.start))continue;if(p.end&&!w.endsWith(p.end))continue;if(p.length&&[...w].length!==p.length)continue;if(p.syll&&syl?.get(r[0])?.length!==p.syll)continue;matches.push(r[0]);}}matches.sort((a,b)=>a.localeCompare(b,'pt'));if(!matches.length){add('Não encontrei palavras com essas condições.');return true}let start=0;lastQuery._results=matches;lastQuery._offset=start+p.amount;addWordResults((p.syll?'Pesquisa experimental: a contagem usa padrões de translineação PT-PT, que podem diferir da divisão silábica.\n':'')+'Encontrei '+matches.length+' palavras. Aqui tens '+Math.min(p.amount,matches.length-start)+':',matches.slice(start,start+p.amount),matches.length>start+p.amount?'Podes pedir «mais».':'');return true;}
const conversation=LexiConversation;
async function handleQuestion(q){
 const intent=conversation.parse(q,{lastWord,lastQuery});
 switch(intent.type){
 case 'greeting': add('Olá! Que palavra gostavas de descobrir hoje? Também podes pedir palavras por letras ou sílabas.');return;
 case 'thanks':add('De nada! Queres descobrir mais alguma palavra?');return;
 case 'help':add('Podes perguntar «O que significa efémero?», «Diz-me dez palavras começadas por C», «Palavras com três sílabas» ou «Agora com quatro sílabas». Depois de uma definição, podes pedir «Outros significados».');return;
 case 'reset':lastWord='';lastEntry=null;lastQuery=null;lastSenseOffset=0;add('Começámos uma conversa nova. Que palavra queres explorar?');return;
 case 'clarify':add('Desculpa! Podes reformular a pergunta ou escrever só a palavra que queres consultar?');return;
 case 'more_senses':if(lastEntry)displaySenses(lastSenseOffset);else add('Diz-me primeiro qual é a palavra.');return;
 case 'original':if(lastEntry){const original=(lastEntry[2]||[]).filter(x=>x[1]!=='curated').slice(0,3).map(x=>x[3]?.original||x[0]);add(original.length?original.join('\n'):'Não há texto original nesta entrada.')}else add('Diz-me primeiro qual é a palavra.');return;
 case 'more_results':if(lastQuery?._results){const p=lastQuery,amount=intent.amount||p.amount;const words=p._results.slice(p._offset,p._offset+amount);p._offset+=amount;if(words.length)addWordResults('',words,p._offset<p._results.length?'Podes pedir «mais».':'');else add('Já mostrei todas as palavras encontradas.')}else add('Faz primeiro uma pesquisa de palavras.');return;
 case 'regional':{const r=regionInfo(intent.word),br=intent.target.includes('brasil');const answer=r&&(br?r.br:r.pt);add(answer?'No sentido de '+r.sense+', '+(br?'no Brasil':'em Portugal')+' usa-se «'+answer+'». Esta equivalência não se aplica a todos os sentidos da palavra.':'Não tenho uma equivalência regional verificada para «'+intent.word+'» nesse sentido.');return;}
 case 'search':await searchWithParams(intent.params);return;
 case 'definition':await definition(intent.word);return;
 case 'ask_word':add('Qual é a palavra que queres consultar?');return;
 case 'clarify_search':add('Que tipo de palavras procuras? Por exemplo, «Palavras com três sílabas» ou «Palavras começadas por C».');return;
 case 'unsupported':add('Ainda não tenho '+intent.feature+' separados e validados. Posso mostrar a definição de uma palavra.');return;
 default:add('Não percebi bem. Experimenta «O que significa efémero?» ou «Diz-me palavras começadas por C».');
 }
}
// Use the same search implementation, but accept already parsed parameters.
async function searchWithParams(p){
 lastQuery={...p};const keys=p.start?[keyOf(p.start)]:(await getMeta()).keys;const matches=[];
 for(const k of keys){const syl=p.syll?new Map((await syllShard(k)).map(r=>[r[0],r[1]])):null;
  for(const r of await shard(k)){const w=norm(r[0]);if(!isSearchableWord(r))continue;
   if(p.start&&!w.startsWith(p.start))continue;if(p.end&&!w.endsWith(p.end))continue;
   if(p.length&&[...w].length!==p.length)continue;if(p.syll&&syl?.get(r[0])?.length!==p.syll)continue;matches.push(r[0]);}}
 matches.sort((a,b)=>a.localeCompare(b,'pt'));lastQuery._results=matches;lastQuery._offset=p.amount;
 if(!matches.length){add('Não encontrei palavras com essas condições. Podes alterar uma das condições.');return;}
 addWordResults((p.syll?'Pesquisa experimental: a contagem usa padrões de translineação PT-PT, que podem diferir da divisão silábica.\n':'')+'Encontrei '+matches.length+' palavras. Aqui tens '+Math.min(p.amount,matches.length)+':',matches.slice(0,p.amount),matches.length>p.amount?'Podes pedir «mais».':'');
}
form.addEventListener('submit',async e=>{e.preventDefault();const q=clean(input.value);if(!q)return;input.value='';add(q,'user');try{await getRegional();await handleQuestion(q)}catch(err){console.error(err);add('Não consegui abrir os dados. Verifica se o dicionário foi descarregado e tenta novamente.')}});
document.querySelector('#settings').onclick=()=>dialog.showModal();document.querySelector('#close').onclick=()=>dialog.close();external.checked=localStorage.getItem('priberam')==='1';external.onchange=()=>localStorage.setItem('priberam',external.checked?'1':'0');
document.querySelector('#offline').onclick=async()=>{const progress=document.querySelector('#progress');try{const m=await getMeta();let n=0;for(const k of m.keys){await shard(k);await formShard(k);progress.textContent='Carregadas '+(++n)+' de '+m.keys.length+' partes…'}progress.textContent='Dicionário e formas flexionadas carregados. Para utilização offline permanente, mantém a PWA instalada e permite o armazenamento local.'}catch(e){progress.textContent='Falha ao descarregar: '+e.message}};
if('serviceWorker'in navigator)navigator.serviceWorker.register('./sw.js').catch(console.warn);
