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
var editor=byId('editor');
var editorTitle=byId('editor-title');
var editorWord=byId('editor-word');
var editorNote=byId('editor-note');
var editorLabel=byId('editor-label');
var editorText=byId('editor-text');
var editorStatus=byId('editor-status');
var editorSaveButton=byId('editor-save');
var editorCancelButton=byId('editor-cancel');
var editorRemoveButton=byId('editor-remove');
var editorCloseButton=byId('editor-close');
var tagPanel=byId('tag-panel');
var tagTitle=byId('tag-title');
var tagWord=byId('tag-word');
var tagNoteIntro=byId('tag-note-intro');
var tagActionLabel=byId('tag-action-label');
var tagAction=byId('tag-action');
var tagNoteLabel=byId('tag-note-label');
var tagNoteText=byId('tag-note-text');
var tagUrlLabel=byId('tag-url-label');
var tagUrl=byId('tag-url');
var tagUrlHint=byId('tag-url-hint');
var tagStatus=byId('tag-status');
var tagSaveButton=byId('tag-save');
var tagCancelButton=byId('tag-cancel');
var tagRemoveButton=byId('tag-remove');
var tagCloseButton=byId('tag-close');

var t=LexiI18n.t;
var conversation=LexiConversation;
var APP_VERSION=(typeof self!=='undefined'&&self.LEXI_VERSION)?self.LEXI_VERSION:'dev';
var CACHE_NAME='lexi2-'+APP_VERSION;
var MAX_RESULTS=1000;
var MAX_CHAT_MESSAGES=300;

var meta=null,metaPromise=null;
var regionalData=null,regionalPromise=null;
var formsManifest=null,formsManifestPromise=null;
var missingManifest=null,missingManifestPromise=null;
var imagesManifest=null,imagesManifestPromise=null;
var cache=new Map();
var formsCache=new Map();
var missingCache=new Map();
var lastWord='',lastQuery=null,lastEntry=null,lastSenseOffset=0;
var lastSenseView='preferred';
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
var USER_DEF_KEY='lexi2.userDefinitions';
var USER_DEF_MAX=600;
var USER_DEF_LIMIT=2000;
var IMAGE_TAG_KEY='lexi2.imageTags';
var IMAGE_TAG_LIMIT=200;
var IMAGE_TAG_ACTIONS={wrong:true,better:true,remove:true,wanted:true};
var userDefinitions={};
var userDefViews={};
var imageTags={};
var tagState=null;
var tagLastFocus=null;
var editorState=null;
var editorLastFocus=null;
var offlineSizeMb=92;

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
  var raw=localStorage.getItem('lexi2.prefs')||localStorage.getItem('lexi.prefs');
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
  if(!result.language)result.language=LexiI18n.normalise(localStorage.getItem('lexi2.lang'))||LexiI18n.normalise(localStorage.getItem('lexi.lang'));
  if(!hasPriberam)result.priberam=localStorage.getItem('lexi2.priberam')==='1'||localStorage.getItem('priberam')==='1';
 }catch(e){}
 return result;
}

function persistPrefs(){
 try{
  localStorage.setItem('lexi2.prefs',JSON.stringify({
   priberam:!!prefs.priberam,
   language:languageExplicit?currentLanguage:null
  }));
  return true;
 }catch(e){
  return false;
 }
}

function safeWordKey(word){
 return typeof word==='string'&&word.length>0&&word.length<=200&&
  word!=='__proto__'&&word!=='prototype'&&word!=='constructor';
}

function cleanDefinitionText(text){
 if(typeof text!=='string')return '';
 var value=text.replace(/^\s+|\s+$/g,'');
 if(value.length>USER_DEF_MAX)value=value.slice(0,USER_DEF_MAX);
 return value;
}

function readUserDefinitions(){
 var result={};
 try{
  var raw=localStorage.getItem(USER_DEF_KEY);
  if(!raw)return result;
  var parsed=JSON.parse(raw);
  var source=null;
  if(parsed&&typeof parsed==='object'){
   source=(parsed.definitions&&typeof parsed.definitions==='object')?parsed.definitions:parsed;
  }
  if(!source||typeof source!=='object'||Array.isArray(source))return result;
  var count=0;
  for(var word in source){
   if(!Object.prototype.hasOwnProperty.call(source,word))continue;
   if(!safeWordKey(word))continue;
   var item=source[word];
   var text=item&&typeof item==='object'?item.text:item;
   text=cleanDefinitionText(text);
   if(!text)continue;
   var updated=(item&&typeof item==='object'&&typeof item.updated==='string')?item.updated:'';
   result[word]={text:text,updated:updated};
   count++;
   if(count>=USER_DEF_LIMIT)break;
  }
 }catch(e){}
 return result;
}

function persistUserDefinitions(){
 try{
  localStorage.setItem(USER_DEF_KEY,JSON.stringify({schema:1,definitions:userDefinitions}));
  return true;
 }catch(e){
  return false;
 }
}

function getUserDefinition(word){
 if(!safeWordKey(word))return null;
 if(!Object.prototype.hasOwnProperty.call(userDefinitions,word))return null;
 return userDefinitions[word];
}

function readImageTags(){
 var result={};
 try{
  var raw=localStorage.getItem(IMAGE_TAG_KEY);
  if(!raw)return result;
  var parsed=JSON.parse(raw);
  var source=(parsed&&parsed.tags&&typeof parsed.tags==='object')?parsed.tags:null;
  if(!source||Array.isArray(source))return result;
  var count=0;
  for(var lemma in source){
   if(!Object.prototype.hasOwnProperty.call(source,lemma))continue;
   if(!safeWordKey(lemma))continue;
   var item=source[lemma];
   if(!item||typeof item!=='object')continue;
   var action=(item.action&&IMAGE_TAG_ACTIONS[item.action])?item.action:'wrong';
   var note=(typeof item.note==='string')?item.note.slice(0,300):'';
   var url=(typeof item.url==='string')?item.url.slice(0,300):'';
   var tagged=(typeof item.tagged==='string')?item.tagged:'';
   result[lemma]={file:(typeof item.file==='string')?item.file:'',action:action,note:note,url:url,tagged:tagged};
   count++;
   if(count>=IMAGE_TAG_LIMIT)break;
  }
 }catch(e){}
 return result;
}

function persistImageTags(){
 try{
  localStorage.setItem(IMAGE_TAG_KEY,JSON.stringify({schema:1,tags:imageTags}));
  return true;
 }catch(e){
  return false;
 }
}

function getImageTag(lemma){
 if(!safeWordKey(lemma))return null;
 if(!Object.prototype.hasOwnProperty.call(imageTags,lemma))return null;
 return imageTags[lemma];
}

function setImageTag(lemma,file,action,note,url){
 if(!safeWordKey(lemma))return false;
 if(!IMAGE_TAG_ACTIONS[action])return false;
 var previous=Object.prototype.hasOwnProperty.call(imageTags,lemma)?imageTags[lemma]:null;
 imageTags[lemma]={file:file||'',action:action,note:note||'',url:url||'',tagged:new Date().toISOString()};
 if(!persistImageTags()){
  if(previous)imageTags[lemma]=previous;
  else delete imageTags[lemma];
  return false;
 }
 return true;
}

function clearImageTag(lemma){
 if(!safeWordKey(lemma))return false;
 if(!Object.prototype.hasOwnProperty.call(imageTags,lemma))return false;
 delete imageTags[lemma];
 return persistImageTags();
}

function imageTagsForExport(){
 var list=[];
 for(var lemma in imageTags){
  if(!Object.prototype.hasOwnProperty.call(imageTags,lemma))continue;
  var item=imageTags[lemma];
  list.push({
   lemma:lemma,
   file:item.file||'',
   action:item.action,
   note:item.note||'',
   url:item.url||'',
   tagged:item.tagged||''
  });
 }
 list.sort(function(a,b){return a.lemma<b.lemma?-1:(a.lemma>b.lemma?1:0);});
 return list;
}

function readImportedImageTags(list){
 if(!Array.isArray(list))return [];
 var result=[];
 for(var i=0;i<list.length;i++){
  var item=list[i];
  if(!item||typeof item!=='object')continue;
  if(!safeWordKey(item.lemma))continue;
  if(!item.action||!IMAGE_TAG_ACTIONS[item.action])continue;
  result.push({
   lemma:item.lemma,
   file:(typeof item.file==='string')?item.file:'',
   action:item.action,
   note:(typeof item.note==='string')?item.note.slice(0,300):'',
   url:(typeof item.url==='string')?item.url.slice(0,300):'',
   tagged:(typeof item.tagged==='string')?item.tagged:''
  });
  if(result.length>=IMAGE_TAG_LIMIT)break;
 }
 return result;
}

function mergeImageTags(list){
 if(!list||!list.length)return 0;
 var merged=0;
 for(var i=0;i<list.length;i++){
  var item=list[i];
  var existing=getImageTag(item.lemma);
  if(existing&&(existing.tagged||'')>=(item.tagged||''))continue;
  imageTags[item.lemma]={file:item.file||'',action:item.action,note:item.note||'',url:item.url||'',tagged:item.tagged||''};
  merged++;
 }
 if(merged)persistImageTags();
 return merged;
}

function setUserDefinition(word,text){
 if(!safeWordKey(word))return false;
 var value=cleanDefinitionText(text);
 if(!value)return false;
 var previous=Object.prototype.hasOwnProperty.call(userDefinitions,word)?userDefinitions[word]:null;
 userDefinitions[word]={text:value,updated:new Date().toISOString()};
 if(!persistUserDefinitions()){
  if(previous)userDefinitions[word]=previous;
  else delete userDefinitions[word];
  return false;
 }
 return true;
}

function deleteUserDefinition(word){
 if(!safeWordKey(word))return false;
 if(!Object.prototype.hasOwnProperty.call(userDefinitions,word))return true;
 var previous=userDefinitions[word];
 delete userDefinitions[word];
 if(!persistUserDefinitions()){
  userDefinitions[word]=previous;
  return false;
 }
 return true;
}

function definitionCount(){
 var count=0;
 for(var word in userDefinitions){
  if(Object.prototype.hasOwnProperty.call(userDefinitions,word))count++;
 }
 return count;
}

function renderDefinitionsCount(){
 var node=byId('definitions-count');
 if(!node)return;
 var count=definitionCount();
 if(!count)node.textContent=t('settings.personalDefinitionsNone');
 else if(count===1)node.textContent=t('settings.personalDefinitionsOne');
 else node.textContent=t('settings.personalDefinitionsCount',{count:String(count)});
}

function definitionsSignature(){
 var latest='';
 var count=0;
 for(var word in userDefinitions){
  if(!Object.prototype.hasOwnProperty.call(userDefinitions,word))continue;
  count++;
  var updated=userDefinitions[word].updated||'';
  if(updated>latest)latest=updated;
 }
 return count+':'+latest;
}

function readBackupMeta(){
 try{
  var raw=localStorage.getItem('lexi2.backup')||localStorage.getItem('lexi.backup');
  if(!raw)return;
  var parsed=JSON.parse(raw);
  if(parsed&&parsed.at)backupMeta={at:parsed.at,signature:parsed.signature||null};
 }catch(e){}
}

function saveBackupMeta(){
 try{
  localStorage.setItem('lexi2.backup',JSON.stringify(backupMeta));
  return true;
 }catch(e){
  return false;
 }
}

function prefsSignature(){
 return JSON.stringify({
  language:currentLanguage,
  priberam:!!prefs.priberam,
  definitions:definitionsSignature()
 });
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
  priberam:pendingImport.priberam?t('common.yes'):t('common.no'),
  definitions:String((pendingImport.definitions||[]).length)
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
 renderDefinitionsCount();
 renderOfflineIntro();
 setText('storage-note','settings.storageNote');
 setText('definitions-note','settings.definitionsNote');
 setText('help-text','settings.helpText');
 setText('privacy-text','settings.privacyText');
 setText('sources-text','settings.sources');
 setText('missing-link','settings.missingList');
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
 setText('editor-save','editor.save');
 setText('editor-cancel','editor.cancel');
 setText('editor-remove','editor.remove');
 setText('editor-label','editor.label');
 setAria('editor-close','editor.close');
 if(editorNote)editorNote.textContent=t('editor.note');
 if(editorText)editorText.setAttribute('placeholder',t('editor.placeholder'));
 if(editor&&!editor.hidden&&editorState){
  var hasStored=!!getUserDefinition(editorState.word);
  if(editorTitle)editorTitle.textContent=t(hasStored?'editor.titleEdit':'editor.titleAdd');
  if(editorWord)editorWord.textContent=t('editor.word',{word:editorState.word});
  if(editorStatus)editorStatus.textContent='';
  if(editorRemoveButton)editorRemoveButton.hidden=!hasStored;
 }
 renderTagPanelText();
 if(tagPanel&&!tagPanel.hidden&&tagState){
  var tagStored=getImageTag(tagState.lemma);
  if(tagWord)tagWord.textContent=t('imagetag.word',{word:tagState.lemma});
  if(tagRemoveButton)tagRemoveButton.hidden=!tagStored;
  if(tagStatus)tagStatus.textContent='';
 }
 setText('attribution-link','settings.attribution');
 setText('credits-link','settings.imageCredits');
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

async function getImagesManifest(){
 if(imagesManifest)return imagesManifest;
 if(!imagesManifestPromise){
  imagesManifestPromise=fetch('images/manifest.json').then(function(response){
   if(!response.ok)throw Error('images/manifest.json');
   return response.json();
  }).then(function(data){
   var map={};
   var list=(data&&data.images)||[];
   for(var i=0;i<list.length;i++){
    var record=list[i];
    if(record&&record.lemma&&record.file)map[record.lemma]=record;
   }
   imagesManifest={data:data,map:map};
   return imagesManifest;
  }).catch(function(error){
   imagesManifestPromise=null;
   throw error;
  });
 }
 return imagesManifestPromise;
}

function imageText(record,field){
 var value=record[field]||{};
 return value[currentLanguage]||value['pt-PT']||'';
}

function imageSearchDescription(text){
 var value=String(text||'').replace(/\s+/g,' ');
 value=value.replace(/^[\s«»"“”'.,;:!?()\[\]–—-]+/,'');
 value=value.replace(/[\s«»"“”'.,;:!?()\[\]–—-]+$/,'');
 if(!value)return '';
 var words=value.split(' ');
 if(words.length>18)words=words.slice(0,18);
 value=words.join(' ');
 if(value.length>180)value=value.slice(0,180).replace(/\s+\S*$/,'');
 return value;
}

function imageSearchQuery(lemma,context){
 var base=imageSearchDescription(lemma);
 var detail=imageSearchDescription(context);
 if(detail&&norm(detail)!==norm(base)){
  base=(base+' '+detail).slice(0,220);
 }
 return base;
}

function imageSearchUrl(query){
 return 'https://www.google.com/search?tbm=isch&hl='+encodeURIComponent(currentLanguage)+
  '&q='+encodeURIComponent(query+' fotografia OR ilustração Wikimedia Commons');
}

function preferredImageContext(row){
 if(!row||!row[2]||!row[2].length)return '';
 var list=senseList(row,false);
 if(!list.length)return '';
 return list[0].modernized||list[0].text||'';
}

function updateImageSearchState(figure,lemma){
 if(!figure)return;
 var stored=getImageTag(lemma);
 var flagged=!!(stored&&stored.action==='wanted');
 var status=figure.querySelector('.figure-search-status');
 var clear=figure.querySelector('.figure-search-clear');
 if(status)status.textContent=flagged?t('message.imageSearchFlagged'):'';
 if(clear)clear.hidden=!flagged;
}

function buildIllustrationSearch(lemma,context){
 var query=imageSearchQuery(lemma,context);
 var figure=document.createElement('figure');
 figure.className='entry-figure figure-search';
 figure.setAttribute('data-lemma',lemma);
 var caption=document.createElement('figcaption');
 caption.setAttribute('data-lemma',lemma);
 var text=document.createElement('span');
 text.className='figure-caption';
 text.textContent=t('message.imageMissing',{word:lemma});
 caption.appendChild(text);
 var hint=document.createElement('span');
 hint.className='figure-credit';
 hint.textContent=t('message.imageSearchHint',{query:query});
 caption.appendChild(hint);
 var link=document.createElement('a');
 link.className='figure-search-link';
 link.href=imageSearchUrl(query);
 link.target='_blank';
 link.rel='noopener noreferrer';
 link.textContent=t('message.imageSearchLink',{word:lemma});
 link.addEventListener('click',function(){
  var ok=setImageTag(lemma,'','wanted',query,link.href);
  if(!ok){
   var status=figure.querySelector('.figure-search-status');
   if(status)status.textContent=t('message.imageSearchFlagFailed');
   return;
  }
  updateImageSearchState(figure,lemma);
 });
 caption.appendChild(link);
 var status=document.createElement('span');
 status.className='figure-search-status';
 status.setAttribute('role','status');
 status.setAttribute('aria-live','polite');
 caption.appendChild(status);
 var clear=document.createElement('button');
 clear.type='button';
 clear.className='figure-search-clear';
 clear.textContent=t('message.imageSearchClear');
 clear.addEventListener('click',function(){
  if(clearImageTag(lemma))updateImageSearchState(figure,lemma);
 });
 caption.appendChild(clear);
 figure.appendChild(caption);
 updateImageSearchState(figure,lemma);
 return figure;
}

function insertIllustrationNode(node,anchor){
 if(anchor&&anchor.parentNode===chat){
  chat.insertBefore(node,anchor.nextSibling);
  revealNode(anchor);
 }else{
  chat.appendChild(node);
  revealNode(node);
 }
 trimChat();
}

function buildIllustration(record,context){
 var figure=document.createElement('figure');
 figure.className='entry-figure';
 var img=document.createElement('img');
 img.src='images/'+record.file;
 img.width=record.width;
 img.height=record.height;
 img.loading='lazy';
 img.decoding='async';
 img.alt=imageText(record,'alt')||record.lemma;
 img.addEventListener('error',function(){
  if(!figure.parentNode)return;
  figure.parentNode.replaceChild(buildIllustrationSearch(record.lemma,imageText(record,'caption')||context),figure);
 });
 figure.appendChild(img);
 var caption=document.createElement('figcaption');
 caption.setAttribute('data-lemma',record.lemma);
 var text=document.createElement('span');
 text.className='figure-caption';
 text.textContent=imageText(record,'caption');
 caption.appendChild(text);
 var credit=document.createElement('span');
 credit.className='figure-credit';
 credit.appendChild(document.createTextNode(t('message.imageCredit',{author:record.author})+' · '));
 if(record.licence_url){
  var licence=document.createElement('a');
  licence.href=record.licence_url;
  licence.target='_blank';
  licence.rel='noopener noreferrer';
  licence.textContent=record.licence;
  credit.appendChild(licence);
 }else{
  credit.appendChild(document.createTextNode(record.licence||''));
 }
 credit.appendChild(document.createTextNode(' · '));
 var source=document.createElement('a');
 source.href=record.source;
 source.target='_blank';
 source.rel='noopener noreferrer';
 source.textContent=t('message.imageSource');
 credit.appendChild(source);
 caption.appendChild(credit);
 var tagButton=document.createElement('button');
 tagButton.type='button';
 var tagStored=getImageTag(record.lemma);
 if(tagStored&&tagStored.action==='wanted')tagStored=null;
 tagButton.className=tagStored?'figure-tag tagged':'figure-tag';
 tagButton.textContent=t(tagStored?'imagetag.openTagged':'imagetag.open');
 tagButton.addEventListener('click',function(){
  openImageTagPanel(record,tagButton);
 });
 caption.appendChild(tagButton);
 figure.appendChild(caption);
 return figure;
}

function showIllustration(lemma,anchor,context){
 if(!lemma)return;
 getImagesManifest().then(function(manifest){
  var record=manifest.map[lemma];
  if(!record){
   insertIllustrationNode(buildIllustrationSearch(lemma,context),anchor);
   return;
  }
  var figure=buildIllustration(record,context);
  insertIllustrationNode(figure,anchor);
 }).catch(function(){
  insertIllustrationNode(buildIllustrationSearch(lemma,context),anchor);
 });
}

function showIllustrationSearch(lemma,context,anchor){
 if(!lemma)return;
 insertIllustrationNode(buildIllustrationSearch(lemma,context),anchor);
}

function refreshOfflineSize(){
 return Promise.all([getMeta(),getFormsMeta(),getMissingMeta(),getImagesManifest()]).then(function(values){
  var bytes=(values[0].bytes||0)+(values[1].bytes||0)+(values[2].bytes||0)+(values[3].data.bytes||0);
  if(bytes>0)offlineSizeMb=Math.max(1,Math.round(bytes/1048576));
  renderOfflineIntro();
 }).catch(function(){});
}

function renderOfflineIntro(){
 var node=byId('offline-intro');
 if(node)node.textContent=t('settings.offlineIntro',{size:String(offlineSizeMb)});
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

function scrollContainer(){
 // The chat scrolls inside #main when it has a bounded height; otherwise the
 // document is the scroller. Scroll whichever is actually scrollable.
 if(main&&main.scrollHeight>main.clientHeight+1)return main;
 return document.scrollingElement||document.documentElement;
}

function scrollChat(){
 var scroller=scrollContainer();
 scroller.scrollTop=scroller.scrollHeight;
}

function revealNode(node){
 if(!node)return;
 var scroller=scrollContainer();
 var offset=8;
 if(scroller===main){
  main.scrollTop=Math.max(0,
   main.scrollTop+node.getBoundingClientRect().top-main.getBoundingClientRect().top-offset);
  return;
 }
 var top=node.getBoundingClientRect().top+(window.pageYOffset||scroller.scrollTop||0)-offset;
 if(typeof window.scrollTo==='function')window.scrollTo(0,Math.max(0,top));
 else scroller.scrollTop=Math.max(0,top);
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
 return d;
}

function isAttached(node){
 return !!(node&&node.parentNode&&document.body&&document.body.contains(node));
}

function userDefView(word){
 if(!userDefViews[word])userDefViews[word]={nodes:[],buttons:[]};
 return userDefViews[word];
}

function registerUserDefButton(word,button){
 var view=userDefView(word);
 button._personalWord=word;
 view.buttons.push(button);
 updateUserDefButton(button,!!getUserDefinition(word));
}

function updateUserDefButton(button,hasDefinition){
 button.textContent=t(hasDefinition?'message.personalDefinitionEditEntry':'message.personalDefinitionAdd');
 button.setAttribute('aria-label',t(hasDefinition?'message.personalDefinitionEditAria':'message.personalDefinitionAddAria',{word:button._personalWord||''}));
}

function registerUserDefNode(word,node){
 userDefView(word).nodes.push(node);
 node._personalWord=word;
}

function refreshUserDefinitions(word){
 var view=userDefViews[word];
 if(!view)return;
 var stored=getUserDefinition(word);
 var i;
 for(i=0;i<view.buttons.length;i++){
  var button=view.buttons[i];
  if(!isAttached(button))continue;
  updateUserDefButton(button,!!stored);
 }
 var keep=[];
 for(i=0;i<view.nodes.length;i++){
  var node=view.nodes[i];
  if(!isAttached(node))continue;
  if(!stored){
   node.parentNode.removeChild(node);
   continue;
  }
  if(node._personalText&&node._personalText.textContent!==stored.text){
   node._personalText.textContent=stored.text;
  }
  keep.push(node);
 }
 view.nodes=keep;
 var live=[];
 for(i=0;i<view.buttons.length;i++){
  if(isAttached(view.buttons[i]))live.push(view.buttons[i]);
 }
 view.buttons=live;
}

function refreshAllUserDefinitions(){
 for(var word in userDefViews){
  if(Object.prototype.hasOwnProperty.call(userDefViews,word))refreshUserDefinitions(word);
 }
}

function buildUserDefinitionBubble(word,record){
 var d=document.createElement('div');
 d.className='bubble bot user-definition';
 var label=document.createElement('p');
 label.className='user-definition-label';
 label.textContent=t('message.personalDefinitionLabel');
 d.appendChild(label);
 var text=document.createElement('p');
 text.className='user-definition-text';
 text.textContent=record.text;
 d.appendChild(text);
 var note=document.createElement('p');
 note.className='user-definition-note';
 note.textContent=t('message.personalDefinitionNote');
 d.appendChild(note);
 var row=document.createElement('div');
 row.className='links';
 var edit=document.createElement('button');
 edit.type='button';
 edit.className='inline-action';
 edit.textContent=t('message.personalDefinitionEdit');
 edit.setAttribute('aria-label',t('message.personalDefinitionEditAria',{word:word}));
 edit.addEventListener('click',function(){openDefinitionEditor(word,d);});
 row.appendChild(edit);
 var remove=document.createElement('button');
 remove.type='button';
 remove.className='inline-action';
 remove.textContent=t('message.personalDefinitionRemove');
 remove.addEventListener('click',function(){confirmRemovePersonalDefinition(word);});
 row.appendChild(remove);
 d.appendChild(row);
 d._personalText=text;
 return d;
}

function showPersonalDefinition(word,anchor){
 var stored=getUserDefinition(word);
 if(!stored)return null;
 var node=buildUserDefinitionBubble(word,stored);
 var target=anchor;
 if(target&&target.nextSibling&&target.nextSibling.classList&&target.nextSibling.classList.contains('entry-figure')){
  target=target.nextSibling;
 }
 if(target&&target.parentNode===chat)chat.insertBefore(node,target.nextSibling);
 else chat.appendChild(node);
 registerUserDefNode(word,node);
 trimChat();
 return node;
}

function appendPersonalDefinitionAction(parent,word){
 var row=document.createElement('div');
 row.className='links';
 var button=document.createElement('button');
 button.type='button';
 button.className='inline-action';
 button.textContent=t('message.personalDefinitionAdd');
 button.setAttribute('aria-label',t('message.personalDefinitionAddAria',{word:word}));
 button.addEventListener('click',function(){openDefinitionEditor(word,parent);});
 row.appendChild(button);
 parent.appendChild(row);
 registerUserDefButton(word,button);
 return button;
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

async function openLinkedCommand(command){
 add(command,'user');
 try{
  await handleQuestion(command);
 }catch(err){
  console.error(err);
  add(t('message.defaultReply'));
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

function addDefinitionText(message,headword,moreSenses){
 var d=document.createElement('div');
 d.className='bubble bot';
 appendLinkedText(d,message);
 if(moreSenses)appendMoreSensesHint(d);
 if(headword)appendPriberam(d,headword);
 chat.appendChild(d);
 trimChat();
 scrollChat();
}

function appendMoreSensesHint(parent){
 var command=t('message.moreSensesCommand');
 var parts=t('message.moreSensesHint',{command:'\u0000'}).split('\u0000');
 var row=document.createElement('div');
 row.className='links';
 if(parts[0])row.appendChild(document.createTextNode(parts[0]));
 var b=document.createElement('button');
 b.type='button';
 b.className='inline-action';
 b.textContent=command;
 b.setAttribute('aria-label',t('message.moreSensesAria'));
 b.addEventListener('click',function(){openLinkedCommand(command);});
 row.appendChild(b);
 if(parts[1])row.appendChild(document.createTextNode(parts[1]));
 parent.appendChild(row);
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

function senseList(row,original){
 var senses=row[2]||[];
 var list=senses.map(function(s,index){
  return {
   index:index+1,
   text:s[0],
   region:s[1]||'',
   flags:s[2]||[],
   modernized:s[3]||'',
   source:s[4]||row[0]
  };
 });
 if(original)return list;
 function rank(s){
  if(s.region==='BR')return 3;
  if(s.flags.indexOf('arch')>=0)return 2;
  if(s.flags.indexOf('reg')>=0)return 1;
  return 0;
 }
 return list.sort(function(a,b){
  return rank(a)-rank(b)||a.index-b.index;
 });
}

function senseTags(s,modernizedView){
 var tags=[];
 if(s.region==='BR')tags.push(t('message.tagBrazil'));
 var map={
  arch:'message.tagArchaic',
  reg:'message.tagRegional',
  tech:'message.tagTechnical',
  pop:'message.tagPopular',
  poet:'message.tagPoetic',
  neo:'message.tagNeologism',
  old:'message.tagOldSpelling',
  mod:'message.tagModernization',
  cit:'message.tagCitation',
  rev:'message.tagReview',
  editorial:'message.tagEditorial',
  wikt:'message.tagWiktionary'
 };
 for(var i=0;i<s.flags.length;i++){
  var flag=s.flags[i];
  if(modernizedView&&(flag==='old'||flag==='mod'))continue;
  var key=map[flag];
  if(key){
   var text=t(key);
   if(tags.indexOf(text)<0)tags.push(text);
  }
 }
 return tags.join('');
}

function appendModernizedHint(parent){
 var row=document.createElement('div');
 row.className='links';
 var b=document.createElement('button');
 b.type='button';
 b.className='inline-action';
 b.textContent=t('message.modernizedCommand');
 b.setAttribute('aria-label',t('message.modernizedAria'));
 b.addEventListener('click',function(){
  add(t('message.modernizedCommand'),'user');
  lastSenseView='modernized';
  lastSenseOffset=0;
  displaySenses(0);
 });
 row.appendChild(b);
 parent.appendChild(row);
}

function displaySenses(offset){
 offset=offset||0;
 if(!lastEntry)return;
 var row=lastEntry;
 var original=lastSenseView==='original';
 var modernized=lastSenseView==='modernized';
 var all=senseList(row,original||modernized);
 if(modernized)all=all.filter(function(s){return s.modernized;});
 var page=all.slice(offset,offset+3);
 if(!page.length){
  add(t(modernized?'message.noModernized':'message.noMoreSenses',{word:row[0]}));
  return;
 }
 var heading='«'+row[0]+'»'+(row[1]?' ('+row[1]+')':'')+'\n';
 if(row[3]==='br')heading+=t('message.entryBrazil');
 else if(row[3]==='historical')heading+=t('message.entryHistorical');
 var sources=[];
 for(var q=0;q<page.length;q++){
  if(page[q].source&&sources.indexOf(page[q].source)<0)sources.push(page[q].source);
 }
 if(sources.length===1&&sources[0]!==row[0]){
  heading+=t('message.sourceHeadwordLine',{headword:sources[0]});
 }
 var lines=page.map(function(s){
  var text=modernized?s.modernized:s.text;
  var tags=senseTags(s,modernized);
  var source=(sources.length>1&&s.source&&s.source!==row[0])
   ?t('message.sourceHeadword',{headword:s.source})
   :'';
  return s.index+'. '+text+tags+source;
 });
 if(offset===0&&!modernized){
  var regional=regionExplanation(row[0]);
  if(regional)lines.push(regional);
 }
 var hasMore=offset+3<all.length;
 var hasEditorial=page.some(function(s){return s.flags.indexOf('editorial')>=0;});
 var hasWikt=page.some(function(s){return s.flags.indexOf('wikt')>=0;});
 var introduction=modernized
  ?t('message.modernizedSenses')
  :original
   ?t('message.originalSenses')
   :hasEditorial
    ?t('message.editorialSenses')
    :hasWikt
     ?t('message.wiktSenses')
     :t('message.sourceSenses');
 var hasMod=!modernized&&!original&&(row[2]||[]).some(function(s){return s[3];});
 var d=document.createElement('div');
 d.className='bubble bot';
 appendLinkedText(d,heading+introduction+lines.join('\n'));
 if(hasMore)appendMoreSensesHint(d);
 if(hasMod)appendModernizedHint(d);
 if(offset===0&&row[0])appendPersonalDefinitionAction(d,row[0]);
 if(row[0])appendPriberam(d,row[0]);
 chat.appendChild(d);
 trimChat();
 revealNode(d);
 lastSenseOffset=offset+page.length;
 return d;
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

async function getMissingMeta(){
 if(missingManifest)return missingManifest;
 if(!missingManifestPromise){
  missingManifestPromise=fetch('data/missing-meta.json').then(function(response){
   if(!response.ok)throw Error('missing-meta.json');
   return response.json();
  }).then(function(data){
   missingManifest=data;
   return data;
  }).catch(function(error){
   missingManifestPromise=null;
   throw error;
  });
 }
 return missingManifestPromise;
}

async function missingShard(k){
 if(missingCache.has(k))return missingCache.get(k);
 var manifest=await getMissingMeta();
 if(manifest.shards.indexOf(k)<0)return [];
 var response=await fetch('data/missing/'+k+'.json');
 if(!response.ok)throw Error('missing/'+k+'.json');
 var rows=await response.json();
 return remember(missingCache,k,rows,4);
}

async function findMissing(word){
 var rows=await missingShard(keyOf(word));
 var target=norm(word);
 for(var i=0;i<rows.length;i++){
  if(norm(rows[i][0])===target)return rows[i];
 }
 return null;
}

async function resolveForm(word){
 var rows=await formShard(keyOf(word));
 var target=norm(word);
 var headwords=[];
 var seen={};
 for(var i=0;i<rows.length;i++){
  if(norm(rows[i][0])!==target)continue;
  var payload=rows[i][1];
  var list=Array.isArray(payload)?payload:[payload];
  for(var j=0;j<list.length;j++){
   if(list[j]&&!seen[list[j]]){
    seen[list[j]]=true;
    headwords.push(list[j]);
   }
  }
 }
 return headwords;
}

function addMissingListLink(){
 var d=document.createElement('div');
 d.className='bubble bot';
 var row=document.createElement('div');
 row.className='links';
 var link=document.createElement('a');
 link.href='missing.html';
 link.textContent=t('message.openMissingList');
 row.appendChild(link);
 d.appendChild(row);
 chat.appendChild(d);
 trimChat();
 scrollChat();
}

function showMissing(missing){
 var bubble=add(t('message.missing',{word:missing[0],pos:missing[1]||''}));
 if(bubble)appendPersonalDefinitionAction(bubble,missing[0]);
 showPersonalDefinition(missing[0],bubble);
 showIllustrationSearch(missing[0],'',bubble);
 var regional=regionExplanation(missing[0]);
 if(regional)add(regional);
 if(missing[3])add(t('message.missingNear',{word:missing[0],headword:missing[3]}));
 addMissingListLink();
}

async function definition(word){
 await getMeta();
 await getRegional();
 var row=await find(word);
 if(!row){
  var heads=await resolveForm(word);
  if(!heads.length){
   var missing=await findMissing(word);
   if(missing){
    showMissing(missing);
    return;
   }
   add(t('message.notFound',{word:word}));
   return;
  }
  var available=[];
  for(var i=0;i<heads.length;i++){
   var entry=await find(heads[i]);
   if(entry)available.push(entry);
  }
  if(!available.length){
   for(var h=0;h<heads.length;h++){
    var resolvedMissing=await findMissing(heads[h]);
    if(resolvedMissing){
     showMissing(resolvedMissing);
     return;
    }
   }
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
  lastSenseView='preferred';
  add(t('message.formAlias',{word:word,entry:lastWord}));
  var aliasView=displaySenses(0);
  showPersonalDefinition(lastWord,aliasView);
  showIllustration(lastWord,aliasView,preferredImageContext(lastEntry));
  return;
 }
 lastWord=row[0];
 lastEntry=row;
 lastSenseOffset=0;
 lastSenseView='preferred';
 var entryView=displaySenses(0);
 showPersonalDefinition(lastWord,entryView);
 showIllustration(lastWord,entryView,preferredImageContext(lastEntry));
}

async function searchWithParams(p){
 if(p.syll){
  add(t('message.syllablesUnavailable'));
  return;
 }
 lastQuery={
  start:p.start||null,
  end:p.end||null,
  length:p.length||null,
  amount:p.amount||10
 };
 var m=await getMeta();
 var keys=lastQuery.start?[keyOf(lastQuery.start)]:m.keys;
 var matches=[];
 for(var i=0;i<keys.length;i++){
  var k=keys[i];
  var rows=await shard(k);
  for(var r=0;r<rows.length;r++){
   var row=rows[r];
   if(!isSearchableWord(row))continue;
   var word=norm(row[0]);
   if(lastQuery.start&&word.indexOf(lastQuery.start)!==0)continue;
   if(lastQuery.end&&word.slice(-lastQuery.end.length)!==lastQuery.end)continue;
   if(lastQuery.length&&Array.from(word).length!==lastQuery.length)continue;
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
   lastSenseView='preferred';
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
    if(senseList(lastEntry,true).length){
     lastSenseView='original';
     displaySenses(0);
    }else add(t('message.noOriginal'));
   }else add(t('message.needWord'));
   return;
  case 'modernized':
   if(lastEntry){
    lastSenseView='modernized';
    displaySenses(0);
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
   var literalEntry=intent.literal?await find(intent.literal):null;
   await definition(literalEntry?literalEntry[0]:intent.word);
   return;
  case 'lookup_phrase':{
   // Bare phrases are lookup candidates, not assumed dictionary entries.
   var phraseEntry=await find(intent.word);
   if(phraseEntry)await definition(phraseEntry[0]);
   else add(t(intent.fallback==='clarify_search'?'message.clarifySearch':'message.defaultReply'));
   return;
  }
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
 refreshOfflineSize();
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
 trapFocus(options,event);
}

function trapFocus(panel,event){
 if(event.key!=='Tab'||!panel)return;
 var nodes=panel.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
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

function openDefinitionEditor(word,anchor){
 if(!editor||!safeWordKey(word))return;
 var stored=getUserDefinition(word);
 editorState={word:word,anchor:anchor||null};
 editorLastFocus=document.activeElement;
 if(editorTitle)editorTitle.textContent=t(stored?'editor.titleEdit':'editor.titleAdd');
 if(editorWord)editorWord.textContent=t('editor.word',{word:word});
 if(editorNote)editorNote.textContent=t('editor.note');
 if(editorLabel)editorLabel.textContent=t('editor.label');
 if(editorText){
  editorText.value=stored?stored.text:'';
  editorText.setAttribute('placeholder',t('editor.placeholder'));
  editorText.setAttribute('aria-label',t('editor.label'));
 }
 if(editorSaveButton)editorSaveButton.textContent=t('editor.save');
 if(editorCancelButton)editorCancelButton.textContent=t('editor.cancel');
 if(editorRemoveButton){
  editorRemoveButton.textContent=t('editor.remove');
  editorRemoveButton.hidden=!stored;
 }
 if(editorStatus)editorStatus.textContent='';
 editor.hidden=false;
 document.body.classList.add('panel-open');
 document.addEventListener('keydown',onEditorKey);
 try{editorText.focus();}catch(e){}
}

function closeDefinitionEditor(){
 if(!editor||editor.hidden)return;
 editor.hidden=true;
 document.removeEventListener('keydown',onEditorKey);
 if(!options||options.hidden)document.body.classList.remove('panel-open');
 if(editorText)editorText.value='';
 if(editorStatus)editorStatus.textContent='';
 var focus=editorLastFocus;
 editorLastFocus=null;
 editorState=null;
 if(focus&&typeof focus.focus==='function'){
  try{focus.focus();}catch(e){}
 }
}

function renderTagPanelText(){
 if(tagTitle)tagTitle.textContent=t('imagetag.title');
 if(tagNoteIntro)tagNoteIntro.textContent=t('imagetag.noteIntro');
 if(tagActionLabel)tagActionLabel.textContent=t('imagetag.actionLabel');
 if(tagAction){
  var options=tagAction.options;
  if(options&&options.length>=3){
   options[0].textContent=t('imagetag.actionWrong');
   options[1].textContent=t('imagetag.actionBetter');
   options[2].textContent=t('imagetag.actionRemove');
  }
 }
 if(tagNoteLabel)tagNoteLabel.textContent=t('imagetag.noteLabel');
 if(tagNoteText)tagNoteText.setAttribute('placeholder',t('imagetag.notePlaceholder'));
 if(tagUrlLabel)tagUrlLabel.textContent=t('imagetag.urlLabel');
 if(tagUrlHint)tagUrlHint.textContent=t('imagetag.urlHint');
 if(tagSaveButton)tagSaveButton.textContent=t('imagetag.save');
 if(tagCancelButton)tagCancelButton.textContent=t('imagetag.cancel');
 if(tagRemoveButton)tagRemoveButton.textContent=t('editor.remove');
 setAria('tag-close','editor.close');
 if(tagUrl)tagUrl.setAttribute('placeholder','https://commons.wikimedia.org/wiki/File:…');
}

function openImageTagPanel(record,anchorButton){
 if(!tagPanel||!record||!safeWordKey(record.lemma))return;
 var stored=getImageTag(record.lemma);
 if(stored&&stored.action==='wanted')stored=null;
 tagState={lemma:record.lemma,file:record.file||'',button:anchorButton||null};
 tagLastFocus=document.activeElement;
 renderTagPanelText();
 if(tagWord)tagWord.textContent=t('imagetag.word',{word:record.lemma});
 if(tagAction)tagAction.value=stored?stored.action:'wrong';
 if(tagNoteText)tagNoteText.value=stored?stored.note:'';
 if(tagUrl)tagUrl.value=stored?stored.url:'';
 if(tagRemoveButton)tagRemoveButton.hidden=!stored;
 if(tagStatus)tagStatus.textContent='';
 tagPanel.hidden=false;
 document.body.classList.add('panel-open');
 document.addEventListener('keydown',onTagPanelKey);
 try{if(tagAction)tagAction.focus();}catch(e){}
}

function closeImageTagPanel(){
 if(!tagPanel||tagPanel.hidden)return;
 tagPanel.hidden=true;
 document.removeEventListener('keydown',onTagPanelKey);
 if(!options||options.hidden)document.body.classList.remove('panel-open');
 if(tagNoteText)tagNoteText.value='';
 if(tagUrl)tagUrl.value='';
 if(tagStatus)tagStatus.textContent='';
 var focus=tagLastFocus;
 tagLastFocus=null;
 tagState=null;
 if(focus&&typeof focus.focus==='function'){
  try{focus.focus();}catch(e){}
 }
}

function onTagPanelKey(event){
 if(event.key==='Escape'){
  event.preventDefault();
  closeImageTagPanel();
 }
}

function saveImageTag(){
 if(!tagState)return;
 var action=tagAction?tagAction.value:'wrong';
 if(!IMAGE_TAG_ACTIONS[action])action='wrong';
 var note=tagNoteText?tagNoteText.value:'';
 var url=tagUrl?tagUrl.value:'';
 url=url.replace(/^\s+|\s+$/g,'');
 if(url&&!/^https:\/\/commons\.wikimedia\.org\/wiki\/File:[^/]+/i.test(url)){
  if(tagStatus)tagStatus.textContent=t('imagetag.invalidUrl');
  return;
 }
 if(note)note=note.replace(/\s+/g,' ').slice(0,300);
 if(setImageTag(tagState.lemma,tagState.file,action,note,url)){
  if(tagState.button){
   tagState.button.textContent=t('imagetag.openTagged');
   tagState.button.className='figure-tag tagged';
  }
  if(tagStatus)tagStatus.textContent=t('imagetag.saved');
  window.setTimeout(closeImageTagPanel,450);
 }else if(tagStatus){
  tagStatus.textContent=t('settings.exportFailed');
 }
}

function removeImageTag(){
 if(!tagState)return;
 var lemma=tagState.lemma;
 var button=tagState.button;
 if(clearImageTag(lemma)){
  if(button){
   button.textContent=t('imagetag.open');
   button.className='figure-tag';
  }
  if(tagStatus)tagStatus.textContent=t('imagetag.removed');
  window.setTimeout(closeImageTagPanel,450);
 }
}

function refreshTagButtonStates(){
 var buttons=document.querySelectorAll('figure.entry-figure .figure-tag');
 for(var i=0;i<buttons.length;i++){
  var button=buttons[i];
  var figure=button.parentNode;
  var captionText=figure&&figure.querySelector('.figure-caption');
  if(!captionText)continue;
  var lemma=captionText.getAttribute('data-lemma')||'';
  var stored=getImageTag(lemma);
  if(stored&&stored.action==='wanted')stored=null;
  button.textContent=t(stored?'imagetag.openTagged':'imagetag.open');
  button.className=stored?'figure-tag tagged':'figure-tag';
 }
}

function ensurePersonalDefinitionView(word,anchor){
 var view=userDefViews[word];
 var has=false;
 if(view){
  for(var i=0;i<view.nodes.length;i++){
   if(isAttached(view.nodes[i])){has=true;break;}
  }
 }
 if(!has)showPersonalDefinition(word,anchor);
 refreshUserDefinitions(word);
}

function saveDefinitionEditor(){
 if(!editorState||!editorText)return;
 var word=editorState.word;
 var anchor=editorState.anchor;
 var text=cleanDefinitionText(editorText.value);
 if(!text){
  if(editorStatus)editorStatus.textContent=t('editor.empty');
  try{editorText.focus();}catch(e){}
  return;
 }
 if(!getUserDefinition(word)&&definitionCount()>=USER_DEF_LIMIT){
  if(editorStatus)editorStatus.textContent=t('editor.limit');
  return;
 }
 if(!setUserDefinition(word,text)){
  if(editorStatus)editorStatus.textContent=t('message.personalDefinitionSaveFailed');
  return;
 }
 ensurePersonalDefinitionView(word,anchor);
 renderDefinitionsCount();
 renderBackupStatus();
 closeDefinitionEditor();
}

function confirmRemovePersonalDefinition(word){
 if(!getUserDefinition(word))return false;
 if(!window.confirm(t('message.personalDefinitionRemoveConfirm',{word:word})))return false;
 if(!deleteUserDefinition(word)){
  add(t('message.personalDefinitionSaveFailed'));
  return false;
 }
 refreshUserDefinitions(word);
 renderDefinitionsCount();
 renderBackupStatus();
 if(editorState&&editorState.word===word)closeDefinitionEditor();
 return true;
}

function onEditorKey(event){
 if(event.key==='Escape'){
  event.preventDefault();
  closeDefinitionEditor();
  return;
 }
 trapFocus(editor,event);
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

function readImportedDefinitions(list){
 var result=[];
 var seen={};
 if(!Array.isArray(list))return result;
 for(var i=0;i<list.length;i++){
  var item=list[i];
  if(!item||typeof item!=='object')continue;
  var word=typeof item.word==='string'?item.word.replace(/^\s+|\s+$/g,''):'';
  if(!safeWordKey(word))continue;
  var text=cleanDefinitionText(item.text);
  if(!text)continue;
  if(Object.prototype.hasOwnProperty.call(seen,word))continue;
  seen[word]=true;
  result.push({
   word:word,
   text:text,
   updated:typeof item.updated==='string'?item.updated:''
  });
  if(result.length>=USER_DEF_LIMIT)break;
 }
 return result;
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
   if(!data||(data.format!=='lexi2-backup'&&data.format!=='lexi-backup')||(data.schema!==1&&data.schema!==2)||!data.preferences||typeof data.preferences!=='object'||Array.isArray(data.preferences)){
    throw Error('invalid');
   }
   var language=LexiI18n.normalise(data.preferences.language)||currentLanguage;
   pendingImport={
    language:language,
    priberam:data.preferences.priberam===true,
    exportedAt:data.exportedAt||'',
    definitions:readImportedDefinitions(data.personalDefinitions),
    tags:readImportedImageTags(data.imageTags)
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
 var restored=0;
 if(item.definitions&&item.definitions.length){
  var total=definitionCount();
  for(var i=0;i<item.definitions.length;i++){
   var entry=item.definitions[i];
   if(!safeWordKey(entry.word))continue;
   var isNew=!Object.prototype.hasOwnProperty.call(userDefinitions,entry.word);
   if(isNew&&total>=USER_DEF_LIMIT)continue;
   if(isNew)total++;
   userDefinitions[entry.word]={
    text:entry.text,
    updated:entry.updated||new Date().toISOString()
   };
   restored++;
  }
  if(restored)saved=persistUserDefinitions()&&saved;
  refreshAllUserDefinitions();
  renderDefinitionsCount();
 }
 if(item.tags&&item.tags.length){
  if(mergeImageTags(item.tags))saved=true;
 }
 applyLanguage();
 renderBackupStatus();
 showStatus('data-status',saved?'settings.importDone':'settings.importSaveFailed');
}

function exportBackup(){
 try{
  var personal=[];
  for(var word in userDefinitions){
   if(!Object.prototype.hasOwnProperty.call(userDefinitions,word))continue;
   personal.push({
    word:word,
    text:userDefinitions[word].text,
    updated:userDefinitions[word].updated||''
   });
  }
  var data={
   format:'lexi2-backup',
   schema:2,
   app:'lexi',
   version:APP_VERSION,
   exportedAt:new Date().toISOString(),
   preferences:{
    language:currentLanguage,
    priberam:!!external.checked
   },
   personalDefinitions:personal,
   imageTags:imageTagsForExport()
  };
  var blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
  var url=URL.createObjectURL(blob);
  var link=document.createElement('a');
  link.href=url;
  link.download='lexi2-backup-'+new Date().toISOString().slice(0,10)+'.json';
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
  var mm=await getMissingMeta();
  var im=await getImagesManifest();
  var urls=['data/regional.json','images/manifest.json'];
  for(var g=0;g<im.data.images.length;g++)urls.push('images/'+im.data.images[g].file);
  for(var i=0;i<m.keys.length;i++)urls.push('data/'+m.keys[i]+'.json');
  for(var f=0;f<fm.shards.length;f++)if(fm.shards[f]!=='')urls.push('data/forms/'+fm.shards[f]+'.json');
  for(var x=0;x<mm.shards.length;x++)if(mm.shards[x]!=='')urls.push('data/missing/'+mm.shards[x]+'.json');
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
 var watched=null;
 function watch(worker){
  if(!worker||worker===watched)return;
  watched=worker;
  worker.addEventListener('statechange',function(){
   if(worker.state==='redundant'){
    // A failed or displaced install must not be reported as "up to date".
    // The old controller keeps serving the previous release.
    if(navigator.serviceWorker.controller!==worker)setUpdateState('failed');
    return;
   }
   if(worker.state==='installed'&&navigator.serviceWorker.controller)setUpdateState('ready');
  });
 }
 reg.addEventListener('updatefound',function(){watch(reg.installing);});
 watch(reg.installing);
 if(reg.waiting&&navigator.serviceWorker.controller)setUpdateState('ready');
}

function waitForWorkerState(worker){
 return new Promise(function(resolve){
  if(worker.state==='installed'||worker.state==='activated'||worker.state==='redundant'){
   resolve(worker.state);
   return;
  }
  var settled=false;
  var timer=window.setTimeout(function(){finish(worker.state);},15000);
  function finish(state){
   if(settled)return;
   settled=true;
   worker.removeEventListener('statechange',onState);
   window.clearTimeout(timer);
   resolve(state);
  }
  function onState(){finish(worker.state);}
  worker.addEventListener('statechange',onState);
 });
}

function backgroundUpdateCheck(){
 if(!swRegistration)return;
 var now=Date.now();
 if(now-lastUpdateCheck<5*60*1000)return;
 lastUpdateCheck=now;
 swRegistration.update().catch(function(){});
}

function doUpdateCheck(){
 var reg=swRegistration;
 if(!reg){
  setUpdateState('unavailable');
  return;
 }
 lastUpdateCheck=Date.now();
 setUpdateState('checking');
 reg.update().then(function(){
  if(reg.waiting&&navigator.serviceWorker.controller){
   setUpdateState('ready');
   return;
  }
  var worker=reg.installing;
  if(!worker){
   setUpdateState('uptodate');
   return;
  }
  setUpdateState('installing');
  return waitForWorkerState(worker).then(function(state){
   if(state==='redundant'){
    setUpdateState('failed');
    return;
   }
   if(reg.waiting&&navigator.serviceWorker.controller)setUpdateState('ready');
   else if(reg.installing)setUpdateState('installing');
   else setUpdateState('uptodate');
  });
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
 if(!swRegistration){
  setUpdateState('unavailable');
  return;
 }
 if(questionBusy||offlineBusy){
  var busyNote=byId('update-status');
  if(busyNote)busyNote.textContent=t('settings.updateBusy');
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
  setUpdateState('installing');
  var settled=false;
  var timer=window.setTimeout(function(){
   if(settled)return;
   settled=true;
   if(swRegistration&&swRegistration.waiting)requestUpdateActivation(swRegistration.waiting);
   else setUpdateState('applyfailed');
  },15000);
  installing.addEventListener('statechange',function handler(){
   if(installing.state==='redundant'){
    settled=true;
    window.clearTimeout(timer);
    installing.removeEventListener('statechange',handler);
    setUpdateState('applyfailed');
    return;
   }
   if(installing.state!=='installed')return;
   settled=true;
   window.clearTimeout(timer);
   installing.removeEventListener('statechange',handler);
   if(swRegistration&&swRegistration.waiting){
    requestUpdateActivation(swRegistration.waiting);
   }else{
    setUpdateState('applyfailed');
   }
  });
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
 if(editorSaveButton)editorSaveButton.addEventListener('click',saveDefinitionEditor);
 if(editorCancelButton)editorCancelButton.addEventListener('click',closeDefinitionEditor);
 if(editorRemoveButton)editorRemoveButton.addEventListener('click',function(){
  if(editorState)confirmRemovePersonalDefinition(editorState.word);
 });
 if(editorCloseButton)editorCloseButton.addEventListener('click',closeDefinitionEditor);
 if(editor)editor.addEventListener('click',function(event){
  if(event.target===editor)closeDefinitionEditor();
 });
 if(editorText)editorText.addEventListener('keydown',function(event){
  if((event.ctrlKey||event.metaKey)&&event.key==='Enter'){
   event.preventDefault();
   saveDefinitionEditor();
  }
 });
 if(tagSaveButton)tagSaveButton.addEventListener('click',saveImageTag);
 if(tagCancelButton)tagCancelButton.addEventListener('click',closeImageTagPanel);
 if(tagRemoveButton)tagRemoveButton.addEventListener('click',removeImageTag);
 if(tagCloseButton)tagCloseButton.addEventListener('click',closeImageTagPanel);
 if(tagPanel)tagPanel.addEventListener('click',function(event){
  if(event.target===tagPanel)closeImageTagPanel();
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
  if(event.key==='lexi2.prefs'){
   var next=readPrefs();
   var nextLanguage=next.language||currentLanguage;
   prefs=next;
   languageExplicit=!!next.language;
   currentLanguage=LexiI18n.setLanguage(nextLanguage);
   if(external)external.checked=prefs.priberam;
   applyLanguage();
   renderBackupStatus();
  }else if(event.key==='lexi2.backup'){
   readBackupMeta();
   renderBackupStatus();
  }else if(event.key===USER_DEF_KEY){
   userDefinitions=readUserDefinitions();
   refreshAllUserDefinitions();
   renderDefinitionsCount();
   renderBackupStatus();
  }else if(event.key===IMAGE_TAG_KEY){
   imageTags=readImageTags();
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
 userDefinitions=readUserDefinitions();
 imageTags=readImageTags();
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
