/* Lexi conversation intent parser: deterministic, offline, PT-PT and English commands. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;root.LexiConversation=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 const norm=s=>(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
 const numberWords={um:1,uma:1,dois:2,duas:2,tres:3,quatro:4,cinco:5,seis:6,sete:7,oito:8,nove:9,dez:10,quinze:15,vinte:20,one:1,two:2,three:3,four:4,five:5,six:6,seven:7,eight:8,nine:9,ten:10,fifteen:15,twenty:20};
 const num=s=>{if(s==null)return null;const word=numberWords[norm(s)];if(word!=null)return word;const value=Number(s);return Number.isFinite(value)?value:null;};
 const count='(\\d+|um|uma|dois|duas|tr[eê]s|quatro|cinco|seis|sete|oito|nove|dez|quinze|vinte|one|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty)';
 const continuationStart=/^(agora|e |so |apenas |mas |com |now|and |only |just |but |with )/;
 const tidy=s=>(s||'').trim().replace(/[.!?;,]+$/,'').trim();
 const unquote=s=>tidy(s).replace(/^[«“"']|[»”"']$/g,'').trim();
 function parse(text,context={}){
  const q=tidy(text),n=norm(q);if(!q)return {type:'empty'};
  if(/^(ola|oi|bom dia|boa tarde|boa noite|boas|viva|hello|hi|hey|good morning|good afternoon|good evening)\b/.test(n))return {type:'greeting'};
  if(/^(obrigad[oa]|muito obrigad[oa]|agradecid[oa]|thanks|thank you|many thanks)\b/.test(n))return {type:'thanks'};
  if(/^(ajuda|socorro|o que sabes fazer|como funcionas|exemplos de perguntas|help|what can you do|how do you work|example questions)$/.test(n))return {type:'help'};
  if(/^(limpa|limpar|recomecar|nova conversa|esquece tudo|reiniciar|reset|new conversation|start over|clear|forget everything)$/.test(n))return {type:'reset'};
  if(/^(nao|errado|nao era isso|nao percebeste|nao e isso|wrong|that['’]?s not it|that is not it|you did not understand|not that)$/.test(n))return {type:'clarify'};
  if(/^(outros? significados?|mais significados?|outras? ace[cç][oõ]es|sentidos? seguintes?|e outros? significados?|other meanings?|more meanings?|other senses?|next senses?|and other meanings?)$/i.test(q))return {type:'more_senses'};
  if(/^(significado original|texto original|fonte original|original text|original meaning|source text)$/i.test(q))return {type:'original'};
  if(/^(mais|mostra(?:-me)? mais|continua|mais palavras|more|show(?: me)? more|continue|more words)(?:\s+(\d+))?$/i.test(q)){
   const amountMatch=q.match(/\d+/);
   return {type:'more_results',amount:amountMatch?Number(amountMatch[0]):null};
  }
  const regional=q.match(/^(?:como (?:se )?diz|qual (?:é|e) (?:o )?equivalente (?:de|da palavra)|o que (?:é|e)|how do you say|what is the equivalent of)\s+[«"']?([\p{L} -]+?)[»"']?\s+(?:em|no|na|in)\s+(Portugal|português europeu|Brasil|português brasileiro|European Portuguese|Brazilian Portuguese|Brazil)$/iu);
  if(regional){
   const target=norm(regional[2]);
   return {type:'regional',word:unquote(regional[1]),target:/brasil|brazil/.test(target)?'brasil':'portugal'};
  }
  if(/\b(sinonim|antonim|contrario|exemplo|synonym|antonym|opposite|example)\b/.test(n))return {type:'unsupported',feature:'synonyms'};
  const searchTerms=/\b(palavras?|comecad[ao]s?|comecam|iniciad[ao]s?|acabam|acabadas?|terminam|terminadas?|letras?|silabas?|caracteres?|words?|starting|starts?|beginning|ending|ends?|letters?|syllables?|characters?)\b/i;
  const isSearch=searchTerms.test(n)||(continuationStart.test(n)&&!!context.lastQuery);
  if(isSearch){
   const start=q.match(/(?:come[cç](?:adas?|am)|iniciad[ao]s?|starting with|starts? with|beginning with)\s+(?:(?:pela?|por|com|the letter)\s+)?(?:letra\s+)?[«"']?([\p{L}])/iu);
   const end=q.match(/(?:acab(?:am|adas?|em)|termin(?:am|adas?|em)|(?:that )?(?:end|ends|ending)\s+(?:with|in)|ending (?:with|in)|ends? (?:with|in))\s+(?:em\s+|por\s+|with\s+|in\s+)?[«"']?([\p{L}]+)/iu);
   const len=q.match(new RegExp('(?:com|tenham|t[eê]m|de|with|having|have|of)\\s+'+count+'\\s+(?:letras?|letters?)','i'));
   const syl=q.match(new RegExp('(?:com|tenham|t[eê]m|de|with|having|have|of|\\b)\\s*'+count+'\\s+(?:s[ií]labas?|syllables?)','i'));
   const amt=q.match(new RegExp('(?:diz(?:-me)?|mostra(?:-me)?|quero|da(?:-me)?|show(?: me)?|give(?: me)?|tell(?: me)?|i want)\\s+'+count+'\\s+(?:palavras?|words?)','i'));
   const hasConstraint=!!(start||end||len||syl);
   if(hasConstraint||(context.lastQuery&&continuationStart.test(n))){
    const p={start:start?norm(start[1]):null,end:end?norm(end[1]):null,length:len?num(len[1]):null,syll:syl?num(syl[1]):null,amount:amt?Math.max(1,Math.min(30,num(amt[1])||10)):10};
    const continuation=!!context.lastQuery&&continuationStart.test(n);
    if(continuation){for(const k of ['start','end','length','syll'])if(p[k]===null)p[k]=context.lastQuery[k]==null?null:context.lastQuery[k];}
    if(!p.start&&!p.end&&!p.length&&!p.syll)return {type:'clarify_search'};
    return {type:'search',params:p};
   }
   if(/\bpalavras?\b/.test(n)||/\bwords?\b/.test(n))return {type:'clarify_search'};
  }
  if(/^(e (?:essa|esta|isso)|o que quer dizer|o que significa|explica melhor|diz-me o significado|and (?:that|this)|what does (?:that|it) mean|explain better|tell me the meaning)$/.test(n))return context.lastWord?{type:'definition',word:context.lastWord}:{type:'ask_word'};
  const def=q.match(/(?:o que (?:é|e|significa|quer dizer)|qual (?:é|e) o significado (?:de|da|do)|significa|significado (?:de|da|do)|define|defini[cç][aã]o (?:de|da|do)|explica(?:-me)?(?: o significado de)?|quem (?:é|e)|what does|what is the meaning of|meaning of|define|explain|who is)\s+(?:a palavra\s+|o termo\s+|um\s+|uma\s+|a\s+|o\s+|the word\s+|the term\s+|a\s+|an\s+|the\s+)?[«“"']?([\p{L}-]+)(?:\s+mean)?/iu);
  if(def)return {type:'definition',word:unquote(def[1])};
  const bare=q.match(/^[«“"']?([\p{L}-]+)[»”"']?$/u);
  if(bare)return {type:'definition',word:bare[1]};
  return {type:'unknown'};
 }
 return {parse,norm};
});
