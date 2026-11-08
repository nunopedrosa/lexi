const assert=require('node:assert/strict');const {parse}=require('./conversation.js');
const cases=[
 ['O que significa efémero?','definition','efémero'],['Define cavalo','definition','cavalo'],['Explica-me janela','definition','janela'],['correram','definition','correram'],['Olá!','greeting'],['Obrigado','thanks'],['ajuda','help'],['Outros significados','more_senses'],['mais','more_results'],['Mostra mais 5','more_results'],['texto original','original'],['Como se diz ônibus em Portugal?','regional'],['Diz-me dez palavras começadas por C','search'],['Palavras com três sílabas','search'],['Agora com quatro sílabas','search'],['Palavras com cinco letras e duas sílabas','search'],['Palavras acabadas em ão','search'],['O que significa?','definition','janela']];
for(const [q,type,word] of cases){const p=parse(q,{lastWord:'janela',lastQuery:{start:'c',syll:3}});assert.equal(p.type,type,`${q}: ${JSON.stringify(p)}`);if(word)assert.equal(p.word,word);}
assert.deepEqual(parse('Agora com quatro sílabas',{lastQuery:{start:'c',syll:3}}).params.start,'c');
assert.equal(parse('Agora com quatro sílabas',{lastQuery:{start:'c',syll:3}}).params.syll,4);
console.log(`${cases.length+2} conversation parser assertions passed`);
