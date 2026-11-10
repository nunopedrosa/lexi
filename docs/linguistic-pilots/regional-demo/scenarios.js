/* Regional review fixtures. Not loaded by Lexi; not production definitions. */
(function(root,factory){
 var api=factory();
 if(typeof module==='object'&&module.exports)module.exports=api;
 else root.LexiEditorialDemo=api;
})(typeof self!=='undefined'?self:this,function(){
 var scenarios=[
  {id:'regional-legal',label:'Legal: sentido jurídico e uso informal',productionApproved:false,
   prompt:'O que significa legal?',
   initial:{kind:'pt_pt_priority',text:'Na aceção jurídica, «legal» diz respeito à lei ou ao que está de acordo com ela.'},
   choices:[
    {id:'law',label:'Uma decisão legal',utterance:'Estou a falar de uma decisão legal.',
     reply:{kind:'contextual_answer',text:'Aqui, «legal» descreve uma decisão que está de acordo com a lei.'}},
    {id:'br_informal',label:'Uma frase ouvida no Brasil',utterance:'Ouvi no Brasil: «Que filme legal!».',explicitBrazilContext:true,
     reply:{kind:'regional_explanation',region:'Brazil',text:'Nesse uso informal do Brasil, «legal» é uma apreciação positiva, próxima de «fixe» ou «giro» em Portugal.'}}
   ],review:'Prioridade à aceção jurídica; o uso informal brasileiro só aparece após contexto explícito. São excertos editoriais para avaliação, não uma lista completa de aceções.',references:['priberam-legal']},
  {id:'regional-apelido',label:'Apelido: nome de família e alcunha',productionApproved:false,
   prompt:'O que é um apelido?',
   initial:{kind:'pt_pt_priority',text:'Em Portugal, «apelido» designa o nome de família.'},
   choices:[
    {id:'family',label:'Um nome de família',utterance:'Estou a falar do nome de família de uma pessoa.',
     reply:{kind:'contextual_answer',text:'Nesse contexto, trata-se do apelido familiar.'}},
    {id:'nickname',label:'O nome pelo qual os amigos tratam alguém',utterance:'Na frase, é o nome pelo qual os amigos tratam alguém.',
     reply:{kind:'contextual_answer',region:'not_established',text:'Nesse contexto, trata-se de uma alcunha. Esse sentido deve ser distinguido do nome de família.'}}
   ],review:'A fonte marca Portugal no sentido de nome de família. O outro sentido não é classificado aqui como exclusivamente brasileiro. Evitar transformar preferência de apresentação em exclusividade regional.',references:['priberam-apelido']},
  {id:'regional-propina',label:'Propina: ensino superior e outro contexto regional',productionApproved:false,
   prompt:'O que é uma propina?',
   initial:{kind:'pt_pt_priority',text:'No ensino superior, «propina» é a taxa devida pela inscrição no curso.'},
   choices:[
    {id:'course',label:'A propina da universidade',utterance:'Estou a falar da propina da universidade.',
     reply:{kind:'contextual_answer',text:'Neste contexto, a propina está ligada à inscrição no curso.'}},
    {id:'br_bribe',label:'Uma notícia do Brasil',utterance:'Ouvi numa notícia do Brasil: «receber propina».',explicitBrazilContext:true,
     reply:{kind:'regional_explanation',region:'Brazil',text:'Nesse contexto brasileiro, «propina» pode referir-se a um suborno. É um sentido diferente da taxa académica.'}}
   ],review:'O ensaio privilegia o contexto académico português. O sentido brasileiro é explicado num pedido contextualizado. Outros sentidos portugueses existentes não são apagados nem declarados inválidos.',references:['priberam-propina']}
 ];
 var withheld={kind:'withheld',text:'Ainda não tenho uma resposta revista para esse contexto.'};
 function reply(id,choiceId){
  for(var i=0;i<scenarios.length;i++){
   var scenario=scenarios[i];
   if(scenario.id!==id)continue;
   if(choiceId==null)return scenario.initial;
   for(var c=0;c<scenario.choices.length;c++){
    if(scenario.choices[c].id===choiceId)return scenario.choices[c].reply;
   }
   return withheld;
  }
  return withheld;
 }
 return {scenarios:scenarios,reply:reply,initialScenarioId:'regional-legal'};
});
