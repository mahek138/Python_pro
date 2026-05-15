self.addEventListener('install', (event) => {
  // Activate this service worker immediately.
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  // Clear old caches so the app always uses fresh network responses.
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.map((key) => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Network-only strategy: no runtime caching.
  if (event.request.method !== 'GET') return;
  event.respondWith(fetch(event.request));
});
