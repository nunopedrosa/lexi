importScripts('./version.js');

const VERSION='lexi2-'+self.LEXI_VERSION;
const CORE=[
 './',
 './index.html',
 './style.css',
 './app.js',
 './conversation.js',
 './editorial.js',
 './i18n.js',
 './missing.html',
 './missing.js',
 './credits.html',
 './version.js',
 './manifest.webmanifest',
 './icons/icon.svg',
 './icons/mark.svg',
 './icons/icon-180.png',
 './icons/icon-192.png',
 './icons/icon-512.png',
 './data/meta.json',
 './data/regional.json',
 './data/forms-meta.json',
 './data/missing-meta.json',
 './images/manifest.json',
 './LICENSE',
 './ATTRIBUTION.md'
];

// Precache every app-shell file with cache:'reload' so a release is never
// assembled from a stale HTTP-cache copy. Installation is all-or-nothing: if a
// file is missing or a cache write fails, the previous worker and its offline
// data stay in charge. scripts/check_publish.py catches an incomplete
// publication before deployment, and app.js reports the failed install.
function precache(){
 return caches.open(VERSION).then(function(cache){
  return Promise.all(CORE.map(function(url){
   var request;
   try{
    request=new Request(url,{cache:'reload'});
   }catch(e){
    // Older Safari builds may reject the cache option; a plain fetch is still
    // better than a failed install.
    request=url;
   }
   return fetch(request).then(function(response){
    if(!response.ok)throw Error(url+' ('+response.status+')');
    return cache.put(url,response);
   });
  }));
 });
}

self.addEventListener('install',e=>{
 e.waitUntil(precache().catch(function(error){
  // Leave the previous worker and its cache untouched. A partial cache for a
  // release that never installs is harmless and is removed when a later
  // release activates.
  console.error('Lexi2 precache failed: '+error.message);
  throw error;
 }));
});

self.addEventListener('activate',e=>{
 e.waitUntil(caches.keys().then(keys=>Promise.all(
  keys.filter(k=>(k.indexOf('lexi2-')===0||k.indexOf('lexi-')===0)&&k!==VERSION).map(k=>caches.delete(k))
 )).then(()=>self.clients.claim()));
});

self.addEventListener('message',e=>{
 if(e.data&&e.data.type==='SKIP_WAITING')self.skipWaiting();
});

self.addEventListener('fetch',e=>{
 if(e.request.method!=='GET')return;
 const url=new URL(e.request.url);
 if(url.origin!==location.origin)return;
 if(e.request.cache==='no-store')return;
 e.respondWith(caches.match(e.request).then(hit=>{
  if(hit)return hit;
  return fetch(e.request).then(r=>{
   if(r&&r.ok&&r.type==='basic'){
    const copy=r.clone();
    e.waitUntil(caches.open(VERSION).then(c=>c.put(e.request,copy)).catch(()=>{}));
   }
   return r;
  });
 }));
});
