/* Lexi conversation intent parser: deterministic, offline, PT-PT. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;root.LexiConversation=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 const norm=s=>(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
 const numberWords={um:1,uma:1,dois:2,duas:2,tres:3,quatro:4,cinco:5,seis:6,sete:7,oito:8,nove:9,dez:10,quinze:15,vinte:20};
 const num=s=>s==null?null:(numberWords[norm(s)]??(Number.isFinite(Number(s))?Number(s):null));
 const count='(\\d+|um|uma|dois|duas|tr[eê]s|quatro|cinco|seis|sete|oito|nove|dez|quinze|vinte)';
 const tidy=s=>(s||'').trim().replace(/[.!?;,]+$/,'').trim();
 const unquote=s=>tidy(s).replace(/^[«“"']|[»”"']$/g,'').trim();
 function parse(text,context={}){
  const q=tidy(text),n=norm(q);if(!q)return {type:'empty'};
  if(/^(ola|oi|bom dia|boa tarde|boa noite|boas|viva)\b/.test(n))return {type:'greeting'};
  if(/^(obrigad[oa]|muito obrigad[oa]|agradecid[oa])\b/.test(n))return {type:'thanks'};
  if(/^(ajuda|socorro|o que sabes fazer|como funcionas|exemplos de perguntas)$/.test(n))return {type:'help'};
  if(/^(limpa|limpar|recomecar|nova conversa|esquece tudo|reiniciar)$/.test(n))return {type:'reset'};
  if(/^(nao|errado|nao era isso|nao percebeste|nao e isso)$/.test(n))return {type:'clarify'};
  if(/^(outros? significados?|mais significados?|outras? ace[cç][oõ]es|sentidos? seguintes?|e outros? significados?)$/i.test(q))return {type:'more_senses'};
  if(/^(significado original|texto original|fonte original)$/i.test(q))return {type:'original'};
  if(/^(mais|mostra(?:-me)? mais|continua|mais palavras)(?:\s+(\d+))?$/i.test(q))return {type:'more_results',amount:Number(q.match(/\d+/)?.[0]||0)||null};
  const regional=q.match(/^(?:como (?:se )?diz|qual (?:é|e) (?:o )?equivalente (?:de|da palavra)|o que (?:é|e))\s+[«"']?([\p{L} -]+?)[»"']?\s+(?:em|no|na)\s+(Portugal|português europeu|Brasil|português brasileiro)$/iu);
  if(regional)return {type:'regional',word:unquote(regional[1]),target:norm(regional[2])};
  if(/\b(sinonim|antonim|contrario|exemplo)\b/.test(n))return {type:'unsupported',feature:'sinónimos, antónimos ou exemplos'};
  const searchTerms=/\b(palavras?|comecad[ao]s?|comecam|iniciad[ao]s?|acabam|acabadas?|terminam|terminadas?|letras?|silabas?|caracteres?)\b/i;
  const isSearch=searchTerms.test(n)||(/^(agora|e |so |apenas |mas |com )/.test(n)&&!!context.lastQuery);
  if(isSearch){
   const start=q.match(/(?:come[cç](?:adas?|am)|iniciad[ao]s?)\s+(?:(?:pela?|por|com)\s+)?(?:letra\s+)?[«"']?([\p{L}])/iu);
   const end=q.match(/(?:acab(?:am|adas?|em)|termin(?:am|adas?|em))\s+(?:em\s+|por\s+)?[«"']?([\p{L}]+)/iu);
   const len=q.match(new RegExp('(?:com|tenham|t[eê]m|de)\\s+'+count+'\\s+letras?','i'));
   const syl=q.match(new RegExp('(?:com|tenham|t[eê]m|de|\\b)\\s*'+count+'\\s+s[ií]labas?','i'));
   const amt=q.match(new RegExp('(?:diz(?:-me)?|mostra(?:-me)?|quero|da(?:-me)?)\\s+'+count+'\\s+palavras?','i'));
   const hasConstraint=!!(start||end||len||syl);
   if(hasConstraint||context.lastQuery&&/^(agora|e |so |apenas |mas |com )/.test(n)){
    const p={start:start?norm(start[1]):null,end:end?norm(end[1]):null,length:len?num(len[1]):null,syll:syl?num(syl[1]):null,amount:amt?Math.max(1,Math.min(30,num(amt[1])||10)):10};
    const continuation=!!context.lastQuery&&/^(agora|e |so |apenas |mas |com )/.test(n);
    if(continuation){for(const k of ['start','end','length','syll'])if(p[k]===null)p[k]=context.lastQuery[k]??null;}
    if(!p.start&&!p.end&&!p.length&&!p.syll)return {type:'clarify_search'};
    return {type:'search',params:p};
   }
   if(/\bpalavras?\b/.test(n))return {type:'clarify_search'};
  }
  const def=q.match(/(?:o que (?:é|e|significa|quer dizer)|qual (?:é|e) o significado (?:de|da|do)|significa|significado (?:de|da|do)|define|defini[cç][aã]o (?:de|da|do)|explica(?:-me)?(?: o significado de)?|quem (?:é|e))\s+(?:a palavra\s+|o termo\s+|um\s+|uma\s+|a\s+|o\s+)?[«“"']?([\p{L}-]+)/iu);
  if(def)return {type:'definition',word:unquote(def[1])};
  if(/^(e (?:essa|esta|isso)|o que quer dizer|o que significa|explica melhor|diz-me o significado)$/.test(n))return context.lastWord?{type:'definition',word:context.lastWord}:{type:'ask_word'};
  const bare=q.match(/^[«“"']?([\p{L}-]+)[»”"']?$/u);
  if(bare)return {type:'definition',word:bare[1]};
  return {type:'unknown'};
 }
 return {parse,norm};
});
