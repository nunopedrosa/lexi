const assert=require('node:assert/strict');const {parse}=require('./conversation.js');
const cases=[
 ['O que significa efémero?','definition','efémero'],['Define cavalo','definition','cavalo'],['Explica-me janela','definition','janela'],['correram','definition','correram'],['Olá!','greeting'],['Obrigado','thanks'],['ajuda','help'],['Outros significados','more_senses'],['mais','more_results'],['Mostra mais 5','more_results'],['texto original','original'],['Como se diz ônibus em Portugal?','regional'],['Diz-me dez palavras começadas por C','search'],['Palavras com três sílabas','search'],['Agora com quatro sílabas','search'],['Palavras com cinco letras e duas sílabas','search'],['Palavras acabadas em ão','search'],['O que significa?','definition','janela'],
 ['hello','greeting'],['thanks','thanks'],['help','help'],['other meanings','more_senses'],['original text','original'],['more','more_results'],['how do you say bus in Portugal','regional'],['what is the equivalent of autocarro in Brazil','regional'],['what does efémero mean','definition','efémero'],['what is the meaning of casa','definition','casa'],['what does that mean','definition','janela'],['words starting with C','search'],['words ending with ão','search'],['words with 5 letters','search'],['words with three syllables','search'],['show me ten words starting with C','search']
];
for(const [q,type,word] of cases){const p=parse(q,{lastWord:'janela',lastQuery:{start:'c',syll:3}});assert.equal(p.type,type,`${q}: ${JSON.stringify(p)}`);if(word)assert.equal(p.word,word);}
assert.deepEqual(parse('Agora com quatro sílabas',{lastQuery:{start:'c',syll:3}}).params.start,'c');
assert.equal(parse('Agora com quatro sílabas',{lastQuery:{start:'c',syll:3}}).params.syll,4);
assert.equal(parse('words with 5 letters').params.length,5);
assert.equal(parse('words with three syllables').params.syll,3);
assert.equal(parse('how do you say bus in Portugal').target,'portugal');
assert.equal(parse('how do you say bus in Brazil').target,'brasil');
console.log(`${cases.length+6} conversation parser assertions passed`);
