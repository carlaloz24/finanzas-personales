const CACHE = 'fivvo-v24';
const ASSETS = [
  './index.html',
  './sync.js',
  './manifest.json',
  './chart.umd.js',
  './icon-192.png?v=2',
  './icon-512.png?v=2',
  './fonts/Saans-TRIAL-Regular.otf',
  './fonts/Saans-TRIAL-Medium.otf',
  './fonts/Saans-TRIAL-SemiBold.otf',
  './fonts/Saans-TRIAL-Bold.otf'
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const url = e.request.url;
  if (url.includes('googleapis.com') || url.includes('accounts.google.com')) {
    e.respondWith(fetch(e.request));
    return;
  }
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
