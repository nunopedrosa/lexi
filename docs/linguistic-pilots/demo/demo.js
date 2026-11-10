/* Presentation of fixed scenarios. No storage, dictionary requests or inference. */
(function(){
 'use strict';
 var api=window.LexiEditorialDemo;
 var select=document.getElementById('scenario');
 var choices=document.getElementById('choices');
 var reset=document.getElementById('reset');
 var utterance=document.getElementById('utterance');
 var response=document.getElementById('response');
 function clear(element){while(element.firstChild)element.removeChild(element.firstChild);}
 function choose(scenario,choice,button){
  var buttons=choices.getElementsByTagName('button');
  for(var i=0;i<buttons.length;i++)buttons[i].setAttribute('aria-pressed','false');
  button.setAttribute('aria-pressed','true');
  utterance.textContent=choice.utterance;
  utterance.hidden=false;
  response.textContent=api.reply(scenario.id,choice.id).text;
  response.hidden=false;
  reset.hidden=false;
 }
 function render(){
  var scenario=null;
  for(var i=0;i<api.scenarios.length;i++)if(api.scenarios[i].id===select.value)scenario=api.scenarios[i];
  if(!scenario)return;
  document.getElementById('prompt').textContent=scenario.prompt;
  document.getElementById('initial').textContent=api.reply(scenario.id).text;
  document.getElementById('review').textContent=scenario.review;
  utterance.textContent='';utterance.hidden=true;
  response.textContent='';response.hidden=true;
  reset.hidden=true;
  clear(choices);
  for(var c=0;c<scenario.choices.length;c++){
   (function(choice){
    var button=document.createElement('button');
    button.type='button';
    button.textContent=choice.label;
    button.setAttribute('aria-pressed','false');
    button.addEventListener('click',function(){choose(scenario,choice,button);});
    choices.appendChild(button);
   })(scenario.choices[c]);
  }
  var references=document.getElementById('references');
  clear(references);
  references.appendChild(document.createTextNode('Referências de consulta: '));
  for(var r=0;r<scenario.references.length;r++){
   var word=scenario.references[r].slice(9);
   var link=document.createElement('a');
   link.href='https://dicionario.priberam.org/'+encodeURIComponent(word);
   link.textContent=word;
   link.target='_blank';
   link.rel='noopener noreferrer';
   references.appendChild(link);
  }
 }
 clear(select);
 for(var i=0;i<api.scenarios.length;i++){
  var option=document.createElement('option');
  option.value=api.scenarios[i].id;
  option.textContent=api.scenarios[i].label;
  select.appendChild(option);
 }
 select.value=api.initialScenarioId||'sem-06';
 select.addEventListener('change',render);
 reset.addEventListener('click',function(){render();select.focus();});
 render();
})();
