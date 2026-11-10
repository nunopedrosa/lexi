const assert=require('node:assert/strict');const {parse}=require('./conversation.js');
const cases=[
 ['O que é casa de banho?','definition','casa de banho'],
 ['O que significa «ponto de vista»?','definition','ponto de vista'],
 ['Define fim de semana','definition','fim de semana'],
 ['O que é a palavra «casa de banho»?','definition','casa de banho'],
 ['Define água-de-colónia','definition','água-de-colónia'],
 ['palavra de honra','lookup_phrase','palavra de honra'],
 ['palavras','definition','palavras'],
 ['  O que é casa   de banho?  ','definition','casa de banho'],
 ['Olá, o que é casa de banho?','definition','casa de banho'],
 ['What does casa de banho mean?','definition','casa de banho'],
 ['What is the meaning of "fim de semana"?','definition','fim de semana'],
 ['O que é uma expressão inexistente?','definition','expressão inexistente'],
 ['O que é casa de banho e cozinha?','definition','casa de banho e cozinha'],
 ['Explica-me palavra de honra','definition','palavra de honra'],
 ['casa de banho','lookup_phrase','casa de banho'],
 ['«ponto de vista»','lookup_phrase','ponto de vista'],
 ['Uma frase arbitrária sem entrada','lookup_phrase','Uma frase arbitrária sem entrada'],
 ['O que é casa; ajuda','unknown'],
 ['Podes dizer o que é casa?','lookup_phrase','Podes dizer o que é casa'],
 ['O que é <script>alert(1)</script>?','unknown'],
 ['O que significa efémero?','definition','efémero'],['O que são batatas?','definition','batatas'],['o que sao as batatas','definition','batatas'],['O que são os animais?','definition','animais'],['O que são?','definition','janela'],['Olá, o que são batatas?','definition','batatas'],['Bom dia! O que é batata?','definition','batata'],['Olá, tudo bem?','greeting'],['Olá, ajuda','help'],['Olá, obrigado','thanks'],['Define cavalo','definition','cavalo'],['Explica-me janela','definition','janela'],['correram','definition','correram'],['Olá!','greeting'],['Obrigado','thanks'],['ajuda','help'],['Outros significados','more_senses'],['mais','more_results'],['Mostra mais 5','more_results'],['texto original','original'],['Como se diz ônibus em Portugal?','regional'],['Diz-me dez palavras começadas por C','search'],['Palavras com três sílabas','search'],['Agora com quatro sílabas','search'],['Palavras com cinco letras e duas sílabas','search'],['Palavras acabadas em ão','search'],['O que significa?','definition','janela'],
 ['hello','greeting'],['thanks','thanks'],['help','help'],['other meanings','more_senses'],['original text','original'],['more','more_results'],['how do you say bus in Portugal','regional'],['what is the equivalent of autocarro in Brazil','regional'],['what does efémero mean','definition','efémero'],['what is the meaning of casa','definition','casa'],['what are potatoes','definition','potatoes'],['hi, what are potatoes','definition','potatoes'],['hi there','greeting'],['what does that mean','definition','janela'],['words starting with C','search'],['words ending with ão','search'],['words with 5 letters','search'],['words with three syllables','search'],['show me ten words starting with C','search']
];
let assertions=0;
for(const [q,type,word] of cases){const p=parse(q,{lastWord:'janela',lastQuery:{start:'c',syll:3}});assert.equal(p.type,type,`${q}: ${JSON.stringify(p)}`);assertions++;if(word){assert.equal(p.word,word);assertions++;}}
assert.equal(parse('O que é a priori?').literal,'a priori');
assert.deepEqual(parse('Agora com quatro sílabas',{lastQuery:{start:'c',syll:3}}).params.start,'c');
assert.equal(parse('Agora com quatro sílabas',{lastQuery:{start:'c',syll:3}}).params.syll,4);
assert.equal(parse('words with 5 letters').params.length,5);
assert.equal(parse('words with three syllables').params.syll,3);
assert.equal(parse('how do you say bus in Portugal').target,'portugal');
assert.equal(parse('how do you say bus in Brazil').target,'brasil');
console.log(`${assertions+7} conversation parser assertions passed`);
