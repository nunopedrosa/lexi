/* Small, user-approved PT-PT presentation layer; source corpus stays unchanged. */
(function(root,factory){
 var api=factory();
 if(typeof module==='object'&&module.exports)module.exports=api;
 else root.LexiEditorial=api;
})(typeof self!=='undefined'?self:this,function(){
 var entries={
  legal:'Na aceção jurídica, «legal» diz respeito à lei ou ao que está de acordo com ela.',
  apelido:'Em Portugal, «apelido» designa o nome de família.',
  propina:'No ensino superior, «propina» é a taxa devida pela inscrição no curso.',
  fato:'Em Portugal, no vestuário, «fato» pode designar um conjunto de casaco e calças ou de casaco e saia, geralmente feitos do mesmo tecido.',
  camisola:'Em Portugal, «camisola» designa uma peça de roupa para a parte superior do corpo, vestida pela cabeça, com ou sem mangas.',
  rapariga:'Em Portugal, «rapariga» pode designar uma menina, uma adolescente ou uma mulher jovem.',
  "autocarro":"Veículo rodoviário destinado ao transporte coletivo de passageiros.",
  "ônibus":"No português do Brasil, «ônibus» designa um veículo rodoviário de transporte coletivo de passageiros, chamado «autocarro» em Portugal.",
  "frigorífico":"Eletrodoméstico que mantém alimentos e bebidas a baixa temperatura para ajudar à sua conservação.",
  "geladeira":"No português do Brasil, «geladeira» é o eletrodoméstico que conserva alimentos e bebidas a baixa temperatura, chamado «frigorífico» em Portugal.",
  "telemóvel":"Telefone portátil que permite comunicar através de uma rede de comunicações móveis.",
  "celular":"Quando designa um telefone, «celular» é a palavra usada no português do Brasil para o aparelho portátil chamado «telemóvel» em Portugal.",
  "sumo":"No contexto das bebidas, «sumo» designa o líquido obtido de frutos ou de outros vegetais.",
  "suco":"No contexto das bebidas, «suco» é a designação usada no português do Brasil para o líquido obtido de frutos ou de outros vegetais, chamado «sumo» em Portugal.",
  "pequeno-almoço":"Refeição tomada habitualmente no início da manhã, antes das restantes refeições do dia.",
  "café da manhã":"No português do Brasil, «café da manhã» designa a refeição da manhã chamada «pequeno-almoço» em Portugal.",
  "ecrã":"Superfície onde se apresentam ou projetam imagens e informação, como num televisor, computador ou sala de cinema.",
  "tela":"Na pintura, «tela» é o tecido que serve de suporte à tinta, ou a pintura realizada nesse suporte.",
  "aplicação":"Em informática, uma «aplicação» é um programa concebido para realizar determinadas tarefas.",
  "aplicativo":"Em informática, no português do Brasil, «aplicativo» é um programa destinado a realizar determinadas tarefas, chamado «aplicação» em Portugal.",
  "utilizador":"Pessoa que utiliza um serviço, sistema, equipamento ou aplicação.",
  "usuário":"No contexto do direito de uso, «usuário» é quem tem o direito de utilizar algo, sem que isso implique ser seu proprietário.",
  "planeado":"Concebido ou organizado de acordo com um plano.",
  "planejado":"No português do Brasil, «planejado» designa o que foi concebido ou organizado de acordo com um plano; corresponde a «planeado» em Portugal.",
  "talho":"Na aceção comercial, «talho» é um estabelecimento onde se prepara e vende carne para alimentação.",
  "açougue":"No português do Brasil, «açougue» é um estabelecimento onde se vende carne para alimentação; em Portugal, nesse sentido, usa-se «talho».",
  "bicha":"Em Portugal, no uso informal, «bicha» pode designar uma fila de pessoas à espera da sua vez.",
  "trem":"Em Portugal, «trem» pode designar um conjunto de utensílios destinados a uma atividade, como em «trem de cozinha».",
  "banheiro":"Na aceção portuguesa ligada à praia, «banheiro» pode designar um nadador-salvador.",
  "peão":"Na circulação rodoviária, «peão» é a pessoa que se desloca a pé numa via pública.",
  "sítio":"Lugar ou local onde algo se encontra, acontece ou pode acontecer.",
  "bica":"Em Lisboa e noutros usos portugueses, «bica» pode designar um café expresso, servido numa chávena pequena.",
  "copa":"Numa árvore, «copa» é a parte superior formada pelos ramos, com ou sem folhas.",
  "cueca":"Peça de roupa interior que cobre a zona genital, usada por mulheres ou homens; em Portugal, usa-se também a forma plural «cuecas».",
  "desporto":"Prática de atividades físicas, organizada ou informal, com fins de recreação, desenvolvimento físico, convívio ou competição.",
  "esporte":"No português do Brasil, «esporte» é a designação correspondente a «desporto», no sentido de prática de atividades físicas, por recreação ou competição."
 };
 function get(word){
  var key=String(word||'').toLowerCase();
  return Object.prototype.hasOwnProperty.call(entries,key)?entries[key]:null;
 }
 function sourceSenses(row,original){
  var senses=(row[2]||[]).map(function(raw,index){
   var extra=raw[3]||{};
   return {
    index:index+1,
    text:original?(extra.original||raw[0]||''):(raw[0]||''),
    region:raw[1]||'unmarked',
    flags:(raw[2]||[]).slice(),
    suggestion:extra.ptpt_suggestion||null,
    curated:raw[1]==='curated'
   };
  });
  return original?senses.filter(function(s){return !s.curated;}):senses;
 }
 return {get:get,sourceSenses:sourceSenses};
});
