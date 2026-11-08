'use strict';

function byId(id){return document.getElementById(id);}

var chat=byId('chat');
var form=byId('form');
var input=byId('question');
var submitButton=byId('send');
var main=byId('main');
var options=byId('options');
var closeButton=byId('close');
var settingsButton=byId('settings');
var languageSelect=byId('language');
var languageSettings=byId('languageSettings');
var external=byId('external');
var installButton=byId('install');
var installText=byId('install-text');
var offlineButton=byId('offline');
var offlineCancelButton=byId('offlineCancel');
var progress=byId('progress');
var checkUpdatesButton=byId('checkUpdates');
var updateAppButton=byId('updateApp');
var exportBackupButton=byId('exportBackup');
var importBackupButton=byId('importBackup');
var importFile=byId('importFile');
var importPanel=byId('import-panel');
var importPreview=byId('import-preview');
var restorePrefs=byId('restorePrefs');
var applyImportButton=byId('applyImport');
var cancelImportButton=byId('cancelImport');

var t=LexiI18n.t;
var conversation=LexiConversation;
var APP_VERSION=(typeof self!=='undefined'&&self.LEXI_VERSION)?self.LEXI_VERSION:'dev';
var CACHE_NAME='lexi-'+APP_VERSION;
var MAX_RESULTS=1000;
var MAX_CHAT_MESSAGES=300;

var meta=null,metaPromise=null;
var regionalData=null,regionalPromise=null;
var formsManifest=null,formsManifestPromise=null;
var cache=new Map();
var formsCache=new Map();
var syllCache=new Map();
var lastWord='',lastQuery=null,lastEntry=null,lastSenseOffset=0;
var questionBusy=false;
var offlineBusy=false,offlineCancel=false;
var pendingImport=null;
var currentLanguage='pt-PT';
var languageExplicit=false;
var prefs={priberam:false,language:null};
var lastFocus=null;
var deferredInstallPrompt=null;
var installState='instructions';
var swRegistration=null;
var updateState='idle';
var reloadAfterUpdate=false;
var lastUpdateCheck=0;
var backupMeta={at:null,signature:null};

function remember(map,key,value,max){
 if(map.has(key))map.delete(key);
 map.set(key,value);
 while(map.size>max){
  var oldest=map.keys().next().value;
  map.delete(oldest);
 }
 return value;
}

function withTimeout(promise,milliseconds){
 return new Promise(function(resolve,reject){
  var settled=false;
  var timer=window.setTimeout(function(){
   if(settled)return;
   settled=true;
   reject(Error(t('settings.offlineUnavailable')));
  },milliseconds);
  promise.then(function(value){
   if(settled)return;
   settled=true;
   window.clearTimeout(timer);
   resolve(value);
  },function(error){
   if(settled)return;
   settled=true;
   window.clearTimeout(timer);
   reject(error);
  });
 });
}

function norm(s){
 return (s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
}

function clean(s){
 return s.replace(/[?!.,;:]+$/g,'').trim();
}

function readPrefs(){
 var result={priberam:false,language:null};
 var hasPriberam=false;
 try{
  var raw=localStorage.getItem('lexi.prefs');
  if(raw){
   var parsed=JSON.parse(raw);
   if(parsed&&typeof parsed==='object'){
    if(typeof parsed.priberam==='boolean'){
     result.priberam=parsed.priberam;
     hasPriberam=true;
    }
    result.language=LexiI18n.normalise(parsed.language);
   }
  }
  if(!result.language)result.language=LexiI18n.normalise(localStorage.getItem('lexi.lang'));
  if(!hasPriberam)result.priberam=localStorage.getItem('priberam')==='1';
 }catch(e){}
 return result;
}

function persistPrefs(){
 try{
  localStorage.setItem('lexi.prefs',JSON.stringify({
   priberam:!!prefs.priberam,
   language:languageExplicit?currentLanguage:null
  }));
  return true;
 }catch(e){
  return false;
 }
}

function readBackupMeta(){
 try{
  var raw=localStorage.getItem('lexi.backup');
  if(!raw)return;
  var parsed=JSON.parse(raw);
  if(parsed&&parsed.at)backupMeta={at:parsed.at,signature:parsed.signature||null};
 }catch(e){}
}

function saveBackupMeta(){
 try{
  localStorage.setItem('lexi.backup',JSON.stringify(backupMeta));
  return true;
 }catch(e){
  return false;
 }
}

function prefsSignature(){
 return JSON.stringify({language:currentLanguage,priberam:!!prefs.priberam});
}

function renderBackupStatus(){
 var node=byId('backup-status');
 if(!node)return;
 if(!backupMeta.at){
  node.textContent=t('settings.backupNever');
  return;
 }
 var key=backupMeta.signature===prefsSignature()?'settings.backupCurrent':'settings.backupStale';
 node.textContent=t(key,{date:formatDate(backupMeta.at)});
}

function detectLanguage(){
 var list=(navigator.languages&&navigator.languages.length)?navigator.languages:[navigator.language||''];
 for(var i=0;i<list.length;i++){
  var next=LexiI18n.normalise(list[i]);
  if(next)return next;
 }
 return 'en';
}

function languageAria(){
 var name=currentLanguage==='en'?t('language.nameEn'):t('language.namePt');
 return t('language.aria',{language:name});
}

function setText(id,key){
 var node=byId(id);
 if(node)node.textContent=t(key);
}

function setAria(id,key){
 var node=byId(id);
 if(node)node.setAttribute('aria-label',t(key));
}

function setPlaceholder(id,key){
 var node=byId(id);
 if(node)node.setAttribute('placeholder',t(key));
}

function showStatus(id,key,vars){
 var node=byId(id);
 if(!node)return;
 node.textContent=key?t(key,vars||{}):'';
}

function renderVersion(){
 var text=t('settings.version',{version:APP_VERSION});
 var line=byId('version-line');
 var footer=byId('version-footer');
 if(line)line.textContent=text;
 if(footer)footer.textContent=text;
}

function renderInstallText(){
 if(installText)installText.textContent=t('settings.installInstructions');
}

function renderInstallStatus(){
 var node=byId('install-status');
 if(!node)return;
 var key=installState==='installed'?'settings.installed':installState==='ready'?'settings.installReady':'';
 node.textContent=key?t(key):'';
}

function setUpdateStatus(){
 var node=byId('update-status');
 if(!node)return;
 var key='';
 if(updateState==='checking')key='settings.checking';
 else if(updateState==='uptodate')key='settings.upToDate';
 else if(updateState==='ready')key='settings.updateReady';
 else if(updateState==='installing')key='settings.updateInstalling';
 else if(updateState==='unavailable')key='settings.updateUnavailable';
 else if(updateState==='failed')key='settings.updateFailed';
 else if(updateState==='applyfailed')key='settings.updateApplyFailed';
 else if(updateState==='applying')key='settings.updateApplying';
 node.textContent=key?t(key):'';
}

function setUpdateState(state){
 updateState=state;
 if(updateAppButton)updateAppButton.hidden=state!=='ready';
 setUpdateStatus();
}

function renderImportPreview(){
 if(!pendingImport||!importPreview)return;
 var languageName=pendingImport.language==='en'?t('language.nameEn'):t('language.namePt');
 importPreview.textContent=t('settings.importPreview',{
  date:formatDate(pendingImport.exportedAt),
  language:languageName,
  priberam:pendingImport.priberam?t('common.yes'):t('common.no')
 });
}

function formatDate(value){
 var date=new Date(value);
 if(!value||isNaN(date.getTime()))return String(value||'');
 try{
  return date.toLocaleDateString(currentLanguage==='pt-PT'?'pt-PT':'en');
 }catch(e){
  return date.toISOString().slice(0,10);
 }
}

function applyLanguage(){
 document.documentElement.lang=currentLanguage;
 document.title=t('app.title');
 setText('subtitle','app.subtitle');
 setText('intro','app.greeting');
 setText('options-title','settings.title');
 setText('language-title','settings.languageTitle');
 setText('data-title','settings.dataTitle');
 setText('install-title','settings.installTitle');
 setText('updates-title','settings.updatesTitle');
 setText('help-title','settings.helpTitle');
 setText('data-description','settings.dataDescription');
 setText('offline-intro','settings.offlineIntro');
 setText('storage-note','settings.storageNote');
 setText('definitions-note','settings.definitionsNote');
 setText('help-text','settings.helpText');
 setText('privacy-text','settings.privacyText');
 setText('sources-text','settings.sources');
 setText('external-label','settings.external');
 setText('restore-prefs-label','settings.restorePreferences');
 setText('exportBackup','settings.export');
 setText('importBackup','settings.import');
 setText('applyImport','settings.applyImport');
 setText('cancelImport','settings.cancel');
 setText('install','settings.installButton');
 setText('offline','settings.offlineButton');
 setText('offlineCancel','settings.offlineCancel');
 setText('checkUpdates','settings.check');
 setText('updateApp','settings.update');
 setText('attribution-link','settings.attribution');
 setText('license-link','settings.license');
 setAria('settings','settings.title');
 setAria('close','settings.close');
 setAria('question','app.inputLabel');
 setAria('send','app.send');
 setPlaceholder('question','app.inputPlaceholder');
 var aria=languageAria();
 if(languageSelect){
  languageSelect.value=currentLanguage;
  languageSelect.setAttribute('aria-label',aria);
 }
 if(languageSettings){
  languageSettings.value=currentLanguage;
  languageSettings.setAttribute('aria-label',aria);
 }
 renderInstallText();
 renderInstallStatus();
 renderVersion();
 setUpdateStatus();
 renderImportPreview();
 renderBackupStatus();
}

async function getMeta(){
 if(meta)return meta;
 if(!metaPromise){
  metaPromise=fetch('data/meta.json').then(function(response){
   if(!response.ok)throw Error('meta.json');
   return response.json();
  }).then(function(data){
   meta=data;
   return data;
  }).catch(function(error){
   metaPromise=null;
   throw error;
  });
 }
 return metaPromise;
}

async function getRegional(){
 if(regionalData)return regionalData;
 if(!regionalPromise){
  regionalPromise=fetch('data/regional.json').then(function(response){
   if(!response.ok)throw Error('regional.json');
   return response.json();
  }).then(function(data){
   regionalData=data;
   return data;
  }).catch(function(error){
   regionalPromise=null;
   throw error;
  });
 }
 return regionalPromise;
}

async function getFormsMeta(){
 if(formsManifest)return formsManifest;
 if(!formsManifestPromise){
  formsManifestPromise=fetch('data/forms-meta.json').then(function(response){
   if(!response.ok)throw Error('forms-meta.json');
   return response.json();
  }).then(function(data){
   formsManifest=data;
   return data;
  }).catch(function(error){
   formsManifestPromise=null;
   throw error;
  });
 }
 return formsManifestPromise;
}

function regionInfo(word){
 if(!regionalData||!regionalData.terms)return null;
 return regionalData.terms[norm(word)]||null;
}

function regionExplanation(word){
 var r=regionInfo(word);
 if(!r)return null;
 var note=' '+t('message.regionalScope');
 if(r.pt)return t('message.regionPt',{sense:r.sense,answer:r.pt,note:note});
 if(r.br)return t('message.regionBr',{sense:r.sense,answer:r.br,note:note});
 return null;
}

function scrollChat(){
 if(main)main.scrollTop=main.scrollHeight;
}

function trimChat(){
 while(chat.children.length>MAX_CHAT_MESSAGES){
  chat.removeChild(chat.firstElementChild);
 }
}

function appendPriberam(parent,word){
 if(!external.checked)return;
 var p=document.createElement('div');
 p.className='links';
 var a=document.createElement('a');
 a.href='https://dicionario.priberam.org/'+encodeURIComponent(word);
 a.target='_blank';
 a.rel='noopener noreferrer';
 a.textContent=t('message.priberam');
 p.appendChild(a);
 parent.appendChild(p);
}

function add(message,who,word){
 who=who||'bot';
 var d=document.createElement('div');
 d.className='bubble '+who;
 d.textContent=message;
 if(word)appendPriberam(d,word);
 chat.appendChild(d);
 trimChat();
 scrollChat();
}

async function openLinkedWord(word){
 add(word,'user');
 try{
  await definition(word);
 }catch(err){
  console.error(err);
  add(t('message.openDefinitionFailed',{word:word}));
 }
}

function appendLinkedText(parent,text){
 var parts=String(text).split(/([\p{L}]+(?:[’'-][\p{L}]+)*)/u);
 for(var i=0;i<parts.length;i++){
  var part=parts[i];
  if(!part)continue;
  if(/^[\p{L}]+(?:[’'-][\p{L}]+)*$/u.test(part)){
   var b=document.createElement('button');
   b.type='button';
   b.className='definition-word';
   b.textContent=part;
   b.setAttribute('aria-label',t('message.consultWord',{word:part}));
   (function(word){
    b.addEventListener('click',function(){openLinkedWord(word);});
   })(part);
   parent.appendChild(b);
  }else{
   parent.appendChild(document.createTextNode(part));
  }
 }
}

function addDefinitionText(message,headword){
 var d=document.createElement('div');
 d.className='bubble bot';
 appendLinkedText(d,message);
 if(headword)appendPriberam(d,headword);
 chat.appendChild(d);
 trimChat();
 scrollChat();
}

function appendMoreResultsButton(parent){
 var row=document.createElement('div');
 row.className='links';
 var b=document.createElement('button');
 b.type='button';
 b.className='word-link';
 b.textContent=t('message.more');
 b.setAttribute('aria-label',t('message.moreWordsAria'));
 b.addEventListener('click',function(){
  add(t('message.more'),'user');
  loadMoreResults();
 });
 row.appendChild(b);
 parent.appendChild(row);
}

function addWordResults(prefix,words,showMore){
 var d=document.createElement('div');
 d.className='bubble bot';
 if(prefix){
  var intro=document.createElement('div');
  intro.textContent=prefix;
  d.appendChild(intro);
 }
 var list=document.createElement('div');
 list.className='word-results';
 for(var i=0;i<words.length;i++){
  if(i){
   var sep=document.createElement('span');
   sep.textContent=' · ';
   sep.setAttribute('aria-hidden','true');
   list.appendChild(sep);
  }
  var b=document.createElement('button');
  b.type='button';
  b.className='word-link';
  b.textContent=words[i];
  b.setAttribute('aria-label',t('message.consultMeaning',{word:words[i]}));
  (function(word){
   b.addEventListener('click',function(){openLinkedWord(word);});
  })(words[i]);
  list.appendChild(b);
 }
 d.appendChild(list);
 if(showMore)appendMoreResultsButton(d);
 chat.appendChild(d);
 trimChat();
 scrollChat();
}

function isSearchableWord(row){
 var word=row[0];
 if(Array.from(word).length<2)return false;
 if(!/^\p{L}+$/u.test(word))return false;
 if(word===word.toUpperCase()&&word!==word.toLowerCase())return false;
 var grammar=String(row[1]||'').toLowerCase();
 if(/\b(?:abbr|abrev|sigla|acr[oó]nimo|symbol|s[ií]mbolo)\b/i.test(grammar))return false;
 return true;
}

async function shard(k){
 if(cache.has(k))return cache.get(k);
 var m=await getMeta();
 if(m.keys.indexOf(k)<0)return [];
 var response=await fetch('data/'+k+'.json');
 if(!response.ok)throw Error('data/'+k+'.json');
 var data=await response.json();
 return remember(cache,k,data,6);
}

function keyOf(word){
 var first=norm(word).charAt(0);
 return first&&/[a-z]/.test(first)?first:'_';
}

async function find(word){
 var rows=await shard(keyOf(word));
 var target=norm(word);
 var lower=String(word).toLowerCase();
 var i;
 for(i=0;i<rows.length;i++)if(rows[i][0]===word)return rows[i];
 for(i=0;i<rows.length;i++)if(rows[i][0].toLowerCase()===lower)return rows[i];
 for(i=0;i<rows.length;i++)if(norm(rows[i][0])===target)return rows[i];
 return null;
}

function senseList(row){
 var senses=(row[2]||[]).map(function(raw,index){
  var extra=raw[3]||{};
  return {
   index:index+1,
   text:raw[0]||'',
   region:raw[1]||'unmarked',
   flags:raw[2]||[],
   suggestion:extra.ptpt_suggestion||null,
   curated:raw[1]==='curated'
  };
 });
 var info=regionInfo(row[0]);
 var isBrazilTerm=!!(info&&info.pt);
 function rank(s){
  if(s.curated)return 0;
  if(s.region==='BR')return isBrazilTerm?1:3;
  for(var i=0;i<s.flags.length;i++){
   if(/possível PT-BR|planejad|usuário|ônibus|aplicativo/i.test(s.flags[i]))return 2;
  }
  return 1;
 }
 return senses.sort(function(a,b){
  return rank(a)-rank(b)||a.index-b.index;
 });
}

function displaySenses(offset){
 offset=offset||0;
 if(!lastEntry)return;
 var row=lastEntry;
 var all=senseList(row);
 var page=all.slice(offset,offset+3);
 if(!page.length){
  add(t('message.noMoreSenses',{word:row[0]}));
  return;
 }
 var lines=page.map(function(s){
  var tag=s.curated?t('message.tagCurated'):s.region==='BR'?t('message.tagBrazil'):s.region==='PT'?t('message.tagPortugal'):'';
  var warning='';
  for(var i=0;i<s.flags.length;i++){
   if(/adaptação automática/i.test(s.flags[i])){warning=t('message.tagAuto');break;}
  }
  return s.index+'. '+s.text+tag+warning;
 });
 var regional=offset===0?regionExplanation(row[0]):null;
 if(regional)lines.push(regional);
 if(offset+3<all.length)lines.push(t('message.moreSensesHint'));
 addDefinitionText('«'+row[0]+'»'+(row[1]?' ('+row[1]+')':'')+'\n'+lines.join('\n'),row[0]);
 lastSenseOffset=offset+page.length;
}

async function formShard(k){
 if(formsCache.has(k))return formsCache.get(k);
 var manifest=await getFormsMeta();
 if(manifest.shards.indexOf(k)<0)return [];
 var response=await fetch('data/forms/'+k+'.json');
 if(!response.ok)throw Error('Índice de formas indisponível');
 var rows=await response.json();
 return remember(formsCache,k,rows,4);
}

async function resolveForm(word){
 var rows=await formShard(keyOf(word));
 var target=norm(word);
 var headwords=[];
 var seen={};
 for(var i=0;i<rows.length;i++){
  if(norm(rows[i][0])!==target)continue;
  var list=rows[i][1]||[];
  for(var j=0;j<list.length;j++){
   if(!seen[list[j]]){
    seen[list[j]]=true;
    headwords.push(list[j]);
   }
  }
 }
 return headwords;
}

async function definition(word){
 await getMeta();
 await getRegional();
 var row=await find(word);
 if(!row){
  var heads=await resolveForm(word);
  if(!heads.length){
   add(t('message.notFound',{word:word}));
   return;
  }
  var available=[];
  for(var i=0;i<heads.length;i++){
   var entry=await find(heads[i]);
   if(entry)available.push(entry);
  }
  if(!available.length){
   add(t('message.formNoEntry',{word:word}));
   return;
  }
  if(available.length>1){
   var entries=available.map(function(item){return '«'+item[0]+'»';}).join(', ');
   add(t('message.ambiguousForm',{word:word,entries:entries}));
   return;
  }
  lastWord=available[0][0];
  lastEntry=available[0];
  lastSenseOffset=0;
  add(t('message.formAlias',{word:word,entry:lastWord}));
  displaySenses(0);
  return;
 }
 lastWord=row[0];
 lastEntry=row;
 lastSenseOffset=0;
 displaySenses(0);
}

async function syllShard(k){
 if(syllCache.has(k))return syllCache.get(k);
 var response=await fetch('data/syllables/'+k+'.json');
 if(!response.ok)throw Error('Dados silábicos indisponíveis');
 var data=await response.json();
 return remember(syllCache,k,data,4);
}

async function searchWithParams(p){
 lastQuery={
  start:p.start||null,
  end:p.end||null,
  length:p.length||null,
  syll:p.syll||null,
  amount:p.amount||10
 };
 var m=await getMeta();
 var keys=lastQuery.start?[keyOf(lastQuery.start)]:m.keys;
 var matches=[];
 for(var i=0;i<keys.length;i++){
  var k=keys[i];
  var syl=null;
  if(lastQuery.syll){
   var syllRows=await syllShard(k);
   syl=new Map();
   for(var s=0;s<syllRows.length;s++)syl.set(syllRows[s][0],syllRows[s][1]);
  }
  var rows=await shard(k);
  for(var r=0;r<rows.length;r++){
   var row=rows[r];
   if(!isSearchableWord(row))continue;
   var word=norm(row[0]);
   if(lastQuery.start&&word.indexOf(lastQuery.start)!==0)continue;
   if(lastQuery.end&&word.slice(-lastQuery.end.length)!==lastQuery.end)continue;
   if(lastQuery.length&&Array.from(word).length!==lastQuery.length)continue;
   if(lastQuery.syll){
    var syllables=syl?syl.get(row[0]):null;
    if(!syllables||syllables.length!==lastQuery.syll)continue;
   }
   matches.push(row[0]);
  }
 }
 matches.sort(function(a,b){return a.localeCompare(b,'pt');});
 var total=matches.length;
 var stored=matches.slice(0,MAX_RESULTS);
 lastQuery._results=stored;
 lastQuery._total=total;
 lastQuery._truncated=total>MAX_RESULTS;
 if(!total){
  add(t('message.noResults'));
  return;
 }
 var shown=Math.min(lastQuery.amount,stored.length);
 var prefix=lastQuery._truncated
  ?t('message.foundTruncated',{count:total,shown:shown})
  :t('message.found',{count:total,shown:shown});
 if(lastQuery.syll)prefix=t('message.experimental')+prefix;
 addWordResults(prefix,stored.slice(0,shown),stored.length>shown);
 lastQuery._offset=shown;
}

function loadMoreResults(amount){
 if(!lastQuery||!lastQuery._results){
  add(t('message.noResultsQuery'));
  return;
 }
 var size=amount||lastQuery.amount||10;
 var words=lastQuery._results.slice(lastQuery._offset,lastQuery._offset+size);
 if(!words.length){
  add(lastQuery._truncated?t('message.truncatedHint'):t('message.noMoreResults'));
  return;
 }
 lastQuery._offset+=words.length;
 addWordResults('',words,lastQuery._offset<lastQuery._results.length);
 if(lastQuery._offset>=lastQuery._results.length&&lastQuery._truncated){
  add(t('message.truncatedHint'));
 }
}

async function handleQuestion(q){
 var intent=conversation.parse(q,{lastWord:lastWord,lastQuery:lastQuery});
 switch(intent.type){
  case 'greeting':
   add(t('message.greetingReply'));
   return;
  case 'thanks':
   add(t('message.thanksReply'));
   return;
  case 'help':
   add(t('message.helpReply'));
   return;
  case 'reset':
   lastWord='';
   lastEntry=null;
   lastQuery=null;
   lastSenseOffset=0;
   add(t('message.resetReply'));
   return;
  case 'clarify':
   add(t('message.clarifyReply'));
   return;
  case 'more_senses':
   if(lastEntry)displaySenses(lastSenseOffset);
   else add(t('message.needWord'));
   return;
  case 'original':
   if(lastEntry){
    var original=(lastEntry[2]||[]).filter(function(x){return x[1]!=='curated';}).slice(0,3).map(function(x){
     var extra=x[3]||{};
     return extra.original||x[0];
    });
    add(original.length?original.join('\n'):t('message.noOriginal'));
   }else add(t('message.needWord'));
   return;
  case 'more_results':
   loadMoreResults(intent.amount);
   return;
  case 'regional':{
   var r=regionInfo(intent.word);
   var br=intent.target.indexOf('brasil')>=0;
   var answer=r&&(br?r.br:r.pt);
   if(!answer)add(t('message.regionalNoEquivalence',{word:intent.word}));
   else add(t('message.regionalAnswer',{
    sense:r.sense,
    place:br?t('message.placeBrazil'):t('message.placePortugal'),
    answer:answer
   }));
   return;
  }
  case 'search':
   await searchWithParams(intent.params);
   return;
  case 'definition':
   await definition(intent.word);
   return;
  case 'ask_word':
   add(t('message.askWord'));
   return;
  case 'clarify_search':
   add(t('message.clarifySearch'));
   return;
  case 'unsupported':
   add(t('message.unsupported',{feature:t('message.featureSynonyms')}));
   return;
  default:
   add(t('message.defaultReply'));
 }
}

function openSettings(){
 if(!options||!options.hidden)return;
 lastFocus=document.activeElement;
 if(!lastFocus||lastFocus===document.body||lastFocus===document.documentElement)lastFocus=settingsButton;
 options.hidden=false;
 document.body.classList.add('panel-open');
 document.addEventListener('keydown',onPanelKey);
 if(closeButton)closeButton.focus();
}

function closeSettings(){
 if(!options||options.hidden)return;
 options.hidden=true;
 document.body.classList.remove('panel-open');
 document.removeEventListener('keydown',onPanelKey);
 if(lastFocus&&typeof lastFocus.focus==='function'){
  try{lastFocus.focus();}catch(e){}
 }
}

function onPanelKey(event){
 if(event.key==='Escape'){
  event.preventDefault();
  closeSettings();
  return;
 }
 if(event.key!=='Tab')return;
 var nodes=options.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
 var visible=[];
 for(var i=0;i<nodes.length;i++){
  if(!nodes[i].disabled&&nodes[i].getClientRects().length)visible.push(nodes[i]);
 }
 if(!visible.length)return;
 var first=visible[0];
 var last=visible[visible.length-1];
 if(event.shiftKey&&document.activeElement===first){
  event.preventDefault();
  last.focus();
 }else if(!event.shiftKey&&document.activeElement===last){
  event.preventDefault();
  first.focus();
 }
}

function changeLanguage(value){
 var next=LexiI18n.setLanguage(value);
 if(next===currentLanguage){
  if(languageSelect)languageSelect.value=currentLanguage;
  if(languageSettings)languageSettings.value=currentLanguage;
  return;
 }
 currentLanguage=next;
 languageExplicit=true;
 prefs.language=next;
 document.documentElement.lang=next;
 var saved=persistPrefs();
 applyLanguage();
 showStatus('preference-status',saved?'':'settings.prefSaveFailed');
}

function onExternalChange(){
 prefs.priberam=external.checked;
 if(persistPrefs()){
  showStatus('preference-status','');
 }else{
  external.checked=!external.checked;
  prefs.priberam=external.checked;
  showStatus('preference-status','settings.prefSaveFailed');
 }
 renderBackupStatus();
}

function resetImport(){
 pendingImport=null;
 if(importPanel)importPanel.hidden=true;
 if(importPreview)importPreview.textContent='';
 if(importFile)importFile.value='';
}

function startImport(file){
 if(!file)return;
 if(file.size>1048576){
  if(importFile)importFile.value='';
  showStatus('data-status','settings.importTooLarge');
  return;
 }
 var reader=new FileReader();
 reader.onload=function(){
  try{
   var data=JSON.parse(String(reader.result));
   if(!data||data.format!=='lexi-backup'||data.schema!==1||!data.preferences||typeof data.preferences!=='object'||Array.isArray(data.preferences)){
    throw Error('invalid');
   }
   var language=LexiI18n.normalise(data.preferences.language)||currentLanguage;
   pendingImport={
    language:language,
    priberam:data.preferences.priberam===true,
    exportedAt:data.exportedAt||''
   };
   if(restorePrefs)restorePrefs.checked=true;
   if(importPanel)importPanel.hidden=false;
   showStatus('data-status','');
   renderImportPreview();
  }catch(e){
   resetImport();
   showStatus('data-status','settings.importInvalid');
  }
 };
 reader.onerror=function(){
  resetImport();
  showStatus('data-status','settings.importFailed');
 };
 reader.readAsText(file);
}

function applyPendingImport(){
 if(!pendingImport)return;
 var item=pendingImport;
 var restore=restorePrefs?restorePrefs.checked:true;
 resetImport();
 if(!restore){
  showStatus('data-status','settings.importKept');
  return;
 }
 prefs.priberam=item.priberam;
 languageExplicit=true;
 currentLanguage=LexiI18n.setLanguage(item.language||currentLanguage);
 prefs.language=currentLanguage;
 external.checked=prefs.priberam;
 document.documentElement.lang=currentLanguage;
 var saved=persistPrefs();
 applyLanguage();
 showStatus('data-status',saved?'settings.importDone':'settings.prefSaveFailed');
}

function exportBackup(){
 try{
  var data={
   format:'lexi-backup',
   schema:1,
   app:'lexi',
   version:APP_VERSION,
   exportedAt:new Date().toISOString(),
   preferences:{
    language:currentLanguage,
    priberam:!!external.checked
   }
  };
  var blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
  var url=URL.createObjectURL(blob);
  var link=document.createElement('a');
  link.href=url;
  link.download='lexi-backup-'+new Date().toISOString().slice(0,10)+'.json';
  document.body.appendChild(link);
  if('download' in link)link.click();
  else window.open(url,'_blank');
  document.body.removeChild(link);
  window.setTimeout(function(){URL.revokeObjectURL(url);},1000);
  backupMeta={at:new Date().toISOString(),signature:prefsSignature()};
  saveBackupMeta();
  renderBackupStatus();
  showStatus('data-status','settings.exportDone');
 }catch(e){
  showStatus('data-status','settings.exportFailed');
 }
}

async function prepareOffline(){
 if(offlineBusy)return;
 offlineBusy=true;
 offlineCancel=false;
 offlineButton.disabled=true;
 offlineCancelButton.hidden=false;
 offlineCancelButton.disabled=false;
 progress.textContent=t('settings.offlinePreparing');
 try{
  if(!('caches' in window))throw Error(t('settings.offlineUnavailable'));
  if(!('serviceWorker' in navigator))throw Error(t('settings.offlineUnavailable'));
  await withTimeout(navigator.serviceWorker.ready,15000);
  var m=await getMeta();
  var fm=await getFormsMeta();
  var urls=[];
  for(var i=0;i<m.keys.length;i++)urls.push('data/'+m.keys[i]+'.json');
  for(var f=0;f<fm.shards.length;f++)if(fm.shards[f]!=='')urls.push('data/forms/'+fm.shards[f]+'.json');
  for(var s=0;s<m.keys.length;s++)urls.push('data/syllables/'+m.keys[s]+'.json');
  var total=urls.length;
  var done=0;
  var storage=await caches.open(CACHE_NAME);
  for(var u=0;u<urls.length;u++){
   if(offlineCancel){
    progress.textContent=t('settings.offlineCancelled');
    return;
   }
   var response=await fetch(urls[u]);
   if(!response.ok)throw Error(urls[u]+' ('+response.status+')');
   await storage.put(urls[u],response.clone());
   done++;
   progress.textContent=t('settings.offlineProgress',{done:done,total:total});
  }
  if(navigator.storage&&typeof navigator.storage.persist==='function'){
   try{await navigator.storage.persist();}catch(e){}
  }
  progress.textContent=t('settings.offlineDone');
 }catch(e){
  progress.textContent=t('settings.offlineFailed',{error:e.message||String(e)});
 }finally{
  offlineBusy=false;
  offlineButton.disabled=false;
  offlineCancelButton.hidden=true;
 }
}

function watchRegistration(reg){
 reg.addEventListener('updatefound',function(){
  var worker=reg.installing;
  if(!worker)return;
  worker.addEventListener('statechange',function(){
   if(worker.state==='installed'&&navigator.serviceWorker.controller){
    setUpdateState('ready');
   }
  });
 });
 if(reg.waiting&&navigator.serviceWorker.controller)setUpdateState('ready');
}

function backgroundUpdateCheck(){
 if(!swRegistration)return;
 var now=Date.now();
 if(now-lastUpdateCheck<5*60*1000)return;
 lastUpdateCheck=now;
 swRegistration.update().catch(function(){});
}

function doUpdateCheck(){
 lastUpdateCheck=Date.now();
 setUpdateState('checking');
 swRegistration.update().then(function(){
  window.setTimeout(function(){
   if(!swRegistration)return;
   if(swRegistration.waiting&&navigator.serviceWorker.controller){
    setUpdateState('ready');
   }else if(swRegistration.installing&&navigator.serviceWorker.controller){
    setUpdateState('installing');
   }else{
    setUpdateState('uptodate');
   }
  },1200);
 }).catch(function(){
  setUpdateState('failed');
 });
}

function checkForUpdates(){
 if(!('serviceWorker' in navigator)){
  setUpdateState('unavailable');
  return;
 }
 if(swRegistration){
  doUpdateCheck();
  return;
 }
 navigator.serviceWorker.getRegistration().then(function(reg){
  if(!reg){
   setUpdateState('unavailable');
   return;
  }
  swRegistration=reg;
  watchRegistration(reg);
  doUpdateCheck();
 }).catch(function(){
  setUpdateState('unavailable');
 });
}

function requestUpdateActivation(worker){
 reloadAfterUpdate=true;
 worker.postMessage({type:'SKIP_WAITING'});
 window.setTimeout(function(){
  if(reloadAfterUpdate){
   reloadAfterUpdate=false;
   setUpdateState('applyfailed');
  }
 },8000);
}

function applyUpdate(){
 if(!('serviceWorker' in navigator)||!navigator.serviceWorker.controller){
  setUpdateState('unavailable');
  return;
 }
 if(!window.confirm(t('settings.updateConfirm')))return;
 setUpdateState('applying');
 var waiting=swRegistration&&swRegistration.waiting;
 if(waiting){
  requestUpdateActivation(waiting);
  return;
 }
 var installing=swRegistration&&swRegistration.installing;
 if(installing){
  installing.addEventListener('statechange',function handler(){
   if(installing.state!=='installed')return;
   installing.removeEventListener('statechange',handler);
   if(swRegistration&&swRegistration.waiting){
    requestUpdateActivation(swRegistration.waiting);
   }else{
    setUpdateState('applyfailed');
   }
  });
  setUpdateState('installing');
  return;
 }
 setUpdateState('uptodate');
}

function setupServiceWorker(){
 if(!('serviceWorker' in navigator)){
  setUpdateState('unavailable');
  return;
 }
 navigator.serviceWorker.addEventListener('controllerchange',function(){
  if(reloadAfterUpdate){
   reloadAfterUpdate=false;
   window.location.reload();
  }
 });
 navigator.serviceWorker.register('./sw.js',{updateViaCache:'none'}).then(function(reg){
  swRegistration=reg;
  watchRegistration(reg);
  if(reg.waiting&&navigator.serviceWorker.controller)setUpdateState('ready');
  window.setTimeout(backgroundUpdateCheck,3000);
 }).catch(function(){
  setUpdateState('unavailable');
 });
 document.addEventListener('visibilitychange',function(){
  if(!document.hidden)backgroundUpdateCheck();
 });
 window.addEventListener('online',backgroundUpdateCheck);
}

function installApp(){
 if(!deferredInstallPrompt){
  installState='instructions';
  renderInstallText();
  renderInstallStatus();
  return;
 }
 var prompt=deferredInstallPrompt;
 deferredInstallPrompt=null;
 prompt.prompt();
 prompt.userChoice.then(function(choice){
  if(choice&&choice.outcome==='accepted'){
   installState='installed';
   installButton.hidden=true;
  }else{
   installState='instructions';
  }
  renderInstallText();
  renderInstallStatus();
 }).catch(function(){
  installState='instructions';
  renderInstallText();
  renderInstallStatus();
 });
}

function setupInstall(){
 window.addEventListener('beforeinstallprompt',function(event){
  event.preventDefault();
  deferredInstallPrompt=event;
  installState='ready';
  if(installButton)installButton.hidden=false;
  renderInstallText();
  renderInstallStatus();
 });
 window.addEventListener('appinstalled',function(){
  deferredInstallPrompt=null;
  installState='installed';
  if(installButton)installButton.hidden=true;
  renderInstallText();
  renderInstallStatus();
 });
 if(installButton)installButton.addEventListener('click',installApp);
}

function setupSettings(){
 if(settingsButton)settingsButton.addEventListener('click',openSettings);
 if(closeButton)closeButton.addEventListener('click',closeSettings);
 if(options)options.addEventListener('click',function(event){
  if(event.target===options)closeSettings();
 });
 if(external)external.addEventListener('change',onExternalChange);
 if(languageSelect)languageSelect.addEventListener('change',function(){changeLanguage(languageSelect.value);});
 if(languageSettings)languageSettings.addEventListener('change',function(){changeLanguage(languageSettings.value);});
 if(exportBackupButton)exportBackupButton.addEventListener('click',exportBackup);
 if(importBackupButton)importBackupButton.addEventListener('click',function(){if(importFile)importFile.click();});
 if(importFile)importFile.addEventListener('change',function(){startImport(importFile.files&&importFile.files[0]);});
 if(applyImportButton)applyImportButton.addEventListener('click',applyPendingImport);
 if(cancelImportButton)cancelImportButton.addEventListener('click',function(){
  resetImport();
  showStatus('data-status','');
 });
 if(offlineButton)offlineButton.addEventListener('click',prepareOffline);
 if(offlineCancelButton)offlineCancelButton.addEventListener('click',function(){
  offlineCancel=true;
  offlineCancelButton.disabled=true;
  progress.textContent=t('settings.offlineCancelling');
 });
 if(checkUpdatesButton)checkUpdatesButton.addEventListener('click',checkForUpdates);
 if(updateAppButton)updateAppButton.addEventListener('click',applyUpdate);
 window.addEventListener('storage',function(event){
  if(event.key==='lexi.prefs'){
   var next=readPrefs();
   var nextLanguage=next.language||currentLanguage;
   prefs=next;
   languageExplicit=!!next.language;
   currentLanguage=LexiI18n.setLanguage(nextLanguage);
   if(external)external.checked=prefs.priberam;
   applyLanguage();
   renderBackupStatus();
  }else if(event.key==='lexi.backup'){
   readBackupMeta();
   renderBackupStatus();
  }
 });
}

form.addEventListener('submit',async function(event){
 event.preventDefault();
 if(questionBusy)return;
 var q=clean(input.value);
 if(!q){
  add(t('message.emptyQuestion'));
  return;
 }
 if(q.length>200)q=q.slice(0,200);
 input.value='';
 add(q,'user');
 questionBusy=true;
 if(submitButton)submitButton.disabled=true;
 try{
  await getRegional();
  await handleQuestion(q);
 }catch(err){
  console.error(err);
  add(t('message.dataError'));
 }finally{
  questionBusy=false;
  if(submitButton)submitButton.disabled=false;
 }
});

function init(){
 prefs=readPrefs();
 languageExplicit=!!prefs.language;
 currentLanguage=LexiI18n.setLanguage(prefs.language||detectLanguage());
 prefs.language=currentLanguage;
 readBackupMeta();
 if(external)external.checked=prefs.priberam;
 applyLanguage();
 setupSettings();
 setupInstall();
 setupServiceWorker();
}

init();
