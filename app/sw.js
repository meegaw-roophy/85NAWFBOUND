const CACHE_NAME = 'vektra-v4';

// 1. Core static assets to cache for 100% offline functionality
const PRECACHE_ASSETS = [
  '/app/',
  '/app/index.html',
  '/app/css/style.css',
  '/app/js/app.js',
  '/app/manifest.json'
];

// Install Event: Pre-cache the critical static assets immediately
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(PRECACHE_ASSETS))
      .catch(err => console.warn('sw.js precache failed:', err))
  );
  self.skipWaiting();
});
// Activate Event: Safely clear out OLD versions of Vektra caches only
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) return caches.delete(key);
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event: Intelligent routing for assets vs. API network calls
self.addEventListener('fetch', e => {
  const requestUrl = new URL(e.request.url);

  // 1. Only ever handle plain http(s) GET requests for our own origin.
  // Cross-origin requests (API calls, fonts, CDN scripts) and non-GET
  // requests are left alone so the browser's normal network stack
  // handles them — trying to proxy those here is what was throwing
  // "Failed to fetch" errors from this file.
  if (
    e.request.method !== 'GET' ||
    requestUrl.origin !== self.location.origin ||
    requestUrl.pathname.includes('/sw.js')
  ) {
    return;
  }

  // 2. For navigation requests (requests that accept HTML), always serve index.html
  // This enables SPA routing with query parameters like ?offer=quick-money
  const isNavigation = e.request.mode === 'navigate';
  
  if (isNavigation) {
    e.respondWith(
      caches.match('/app/index.html').then(cachedResponse => {
        if (cachedResponse) return cachedResponse;
        return fetch('/app/index.html').then(networkResponse => {
          if (networkResponse && networkResponse.ok) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then(cache => cache.put('/app/index.html', clone));
          }
          return networkResponse;
        });
      }).catch(() => fetch('/app/index.html'))
    );
    return;
  }

  // 3. For same-origin static assets, use cache-first with a network fallback
  e.respondWith(
    caches.match(e.request).then(cachedResponse => {
      if (cachedResponse) return cachedResponse;
      return fetch(e.request).then(networkResponse => {
        if (networkResponse && networkResponse.ok) {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
        }
        return networkResponse;
      });
    }).catch(() => caches.match('/app/index.html'))
  );
});


