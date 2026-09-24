// KasirKu Service Worker — PWA offline basic caching
//
// PENTING: setiap kali file di /api/static (index.html, dll) diubah/di-deploy,
// NAIKKAN angka versi CACHE di bawah ini (v1 -> v2 -> v3, dst).
// Ini memaksa browser & PWA yang sudah ter-install untuk membuang cache lama
// dan mengambil versi baru, tanpa perlu instruksikan user clear cache manual.
const CACHE = 'kasirku-v2';
const PRECACHE = ['/', '/static/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

// Network-first strategy: try network, fallback to cache
self.addEventListener('fetch', e => {
  // Don't cache API calls
  if (e.request.url.includes('/api/')) return;

  e.respondWith(
    fetch(e.request)
      .then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});
