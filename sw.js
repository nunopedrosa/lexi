importScripts('./version.js');

const VERSION='lexi-'+self.LEXI_VERSION;
const CORE=[
 './',
 './index.html',
 './style.css',
 './app.js',
 './conversation.js',
 './editorial.js',
 './editorial-audit.json',
 './i18n.js',
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
 './data/syllables-meta.json',
 './LICENSE',
 './ATTRIBUTION'
];

self.addEventListener('install',e=>{
 e.waitUntil(caches.open(VERSION).then(c=>c.addAll(CORE)));
});

self.addEventListener('activate',e=>{
 e.waitUntil(caches.keys().then(keys=>Promise.all(
  keys.filter(k=>k.indexOf('lexi-')===0&&k!==VERSION).map(k=>caches.delete(k))
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
