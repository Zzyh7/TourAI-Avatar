const CACHE = 'lingshan-v1';
const ASSETS = [
  '/',
  '/index.html',
  '/map.html',
  '/login',
  '/logo.png',
  '/carousel/0.png',
  '/carousel/1.jpg',
  '/carousel/2.png',
  '/carousel/3.jpg',
  '/carousel/map.png',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
});

self.addEventListener('fetch', e => {
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
