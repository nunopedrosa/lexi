/* Fixed editorial examples only. This module is not loaded by Lexi. */
(function(root,factory){
 var api=factory();
 if(typeof module==='object'&&module.exports)module.exports=api;
 else root.LexiEditorialDemo=api;
})(typeof self!=='undefined'?self:this,function(){
 function answer(text,id,relation){return {kind:'answer',text:text,sourceCaseId:id,relation:relation};}
 function withheld(text){return {kind:'withheld',text:text};}
 function clarification(text){return {kind:'clarification',text:text};}
 function exclusion(text){return {kind:'scope_exclusion',text:text};}
 var scenarios=[
  {id:'sem-01',caseId:'sem-01',label:'Feliz: emoção e outros sentidos',productionApproved:false,
   prompt:'Diz-me um sinónimo de feliz.',
   initial:clarification('Em que sentido usas «feliz»? Podes indicar uma frase?'),
   choices:[
    {id:'emotion',label:'Uma pessoa contente',utterance:'Ela ficou feliz com a notícia.',reply:answer('Nesse contexto, «contente» pode ser um sinónimo de «feliz».','sem-01','synonym')},
    {id:'lucky',label:'Uma pessoa com sorte',utterance:'Quero dizer que ela teve muita sorte.',reply:withheld('Ainda não tenho um sinónimo revisto para esse sentido de «feliz».')}
   ],review:'Retido apenas para o estado emocional. A resposta sobre sorte fica pendente.',references:['priberam-feliz','priberam-contente']},
  {id:'sem-02',caseId:'sem-02',label:'Veloz: velocidade de deslocação',productionApproved:false,
   prompt:'Diz-me um sinónimo de veloz.',
   initial:clarification('Usas «veloz» para falar de algo que se desloca depressa?'),
   choices:[
    {id:'movement',label:'Velocidade de um atleta',utterance:'Estou a falar de um atleta veloz.',reply:answer('Para descrever a velocidade de deslocação, podes usar «rápido» como sinónimo de «veloz».','sem-02','synonym')},
    {id:'task',label:'Conclusão de uma tarefa',utterance:'Estou a falar da conclusão veloz de uma tarefa.',reply:withheld('Esse uso ainda não tem um sinónimo revisto nesta seleção.')}
   ],review:'Só é ensaiada a relação adjetival no domínio da deslocação.',references:['priberam-veloz']},
  {id:'sem-03',caseId:'sem-03',label:'Quente: temperatura e outros sentidos',productionApproved:false,
   prompt:'Qual é o contrário de quente?',
   initial:clarification('Falas de temperatura ou de outro sentido de «quente»?'),
   choices:[
    {id:'temperature',label:'Temperatura de uma bebida',utterance:'Estou a falar da temperatura de uma bebida.',reply:answer('Ao falar da temperatura de uma bebida, «frio» é um contrário de «quente».','sem-03','antonym')},
    {id:'spicy',label:'Comida picante',utterance:'Quero dizer comida picante.',reply:withheld('Ainda não tenho um contrário revisto para esse uso de «quente».')}
   ],review:'Oposição escalar de temperatura. Não implica que tudo o que não é quente seja frio.',references:['priberam-frio']},
  {id:'sem-04',caseId:'sem-04',label:'Abrir: ação física',productionApproved:false,
   prompt:'Qual é o contrário de abrir?',
   initial:clarification('O que estás a abrir?'),
   choices:[
    {id:'window',label:'Uma janela',utterance:'Uma janela.',reply:answer('Para uma janela, a ação contrária a «abrir» é «fechar».','sem-04','antonym')},
    {id:'hole',label:'Um buraco',utterance:'Um buraco.',reply:withheld('Ainda não tenho um contrário revisto para esse uso de «abrir».')}
   ],review:'A resposta fica limitada ao contexto físico conferido. Não se aprovam os restantes usos do synset.',references:['priberam-abrir']},
  {id:'sem-05',caseId:'sem-05',label:'Rosa: flor ou cor',productionApproved:false,
   prompt:'Que relação há entre rosa e flor?',
   initial:clarification('Usas «rosa» para falar da flor ou de outro sentido?'),
   choices:[
    {id:'flower',label:'A flor da roseira',utterance:'Estou a falar da flor da roseira.',reply:answer('Nesse sentido, uma rosa é um tipo de flor.','sem-05','hyponym')},
    {id:'colour',label:'A cor de uma camisola',utterance:'Estou a falar da cor de uma camisola.',reply:exclusion('A relação «tipo de flor» não se aplica a «rosa» enquanto cor.')}
   ],review:'Conserva a direção rosa → flor. Não afirma que toda a flor seja uma rosa.',references:['priberam-rosa']},
  {id:'sem-06',caseId:'sem-06',label:'Banco: objeto ou domínio financeiro',productionApproved:false,
   prompt:'Que relação há entre banco e assento?',
   initial:clarification('Falas de um banco para sentar ou de outro sentido?'),
   choices:[
    {id:'garden',label:'Um banco de jardim',utterance:'Um banco de jardim.',reply:answer('No sentido de objeto para sentar, um banco é um tipo de assento.','sem-06','hyponym')},
    {id:'finance',label:'Um banco financeiro',utterance:'Um banco financeiro.',reply:exclusion('A relação com «assento» não se aplica ao banco financeiro.')}
   ],review:'Retida a hiponímia no contexto físico. Não se converte em sinonímia irrestrita.',references:['priberam-banco']},
  {id:'sem-07',caseId:'sem-07',label:'Equivalência rejeitada: autocarro / possível',productionApproved:false,
   prompt:'«Possível» é sinónimo de «autocarro»?',
   initial:withheld('Não tenho essa equivalência confirmada para o sentido de transporte.'),choices:[],
   review:'Rejeitado no piloto apesar da pertença ao mesmo grupo de origem. Não apagar nem corrigir o grupo original.',references:['priberam-autocarro','priberam-possível']},
  {id:'sem-08',caseId:'sem-08',label:'Sinónimos gerais: banco / assento',productionApproved:false,
   prompt:'«Banco» e «assento» são sempre sinónimos?',
   initial:withheld('Ainda não tenho uma equivalência geral revista entre «banco» e «assento».'),choices:[],
   review:'A fonte contém hiponímia. Não promover esse arco a sinonímia geral; comparar com o exemplo do banco de jardim.',references:['priberam-banco']},
  {id:'sem-09',caseId:'sem-09',label:'Relação adiada: cão / animal',productionApproved:false,
   prompt:'O cão é um tipo de animal?',
   initial:withheld('Esta relação ainda não está disponível nas respostas revistas.'),choices:[],
   review:'Indisponibilidade da seleção, não dúvida sobre a classificação zoológica. Não foi extraído um arco direto para este piloto.',references:['priberam-cão','priberam-animal']},
  {id:'sem-10',caseId:'sem-10',label:'Sentido por rever: roda / bicicleta',productionApproved:false,
   prompt:'Posso usar «roda» como sinónimo de «bicicleta»?',
   initial:withheld('Ainda não tenho uma equivalência revista entre essas palavras para esse uso.'),choices:[],
   review:'Adiado. Esclarecer sentido, metonímia e eventual uso regional ou histórico; não concluir ausência absoluta de tal uso.',references:['priberam-roda','priberam-bicicleta']}
 ];
 var unavailable={kind:'unavailable',text:'Este exemplo não tem uma resposta prevista para esse contexto.'};
 function reply(id,choiceId){
  for(var i=0;i<scenarios.length;i++){
   var scenario=scenarios[i];
   if(scenario.id!==id)continue;
   if(choiceId==null)return scenario.initial;
   for(var c=0;c<scenario.choices.length;c++){
    if(scenario.choices[c].id===choiceId)return scenario.choices[c].reply;
   }
   return unavailable;
  }
  return unavailable;
 }
 return {scenarios:scenarios,reply:reply};
});
