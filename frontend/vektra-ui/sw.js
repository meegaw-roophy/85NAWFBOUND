const CACHE_NAME = 'vektra-v2';

// 1. Core static assets to cache for 100% offline functionality
const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/css/styles.css',    // Adjust paths to match your folder structure
  '/js/app.js',
  '/manifest.json',
  '/favicon.ico'
];

// Install Event: Cache the critical static assets immediately
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(PRECACHE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// Activate Event: Safely clear out OLD versions of Vektra caches only
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
          if (key !== CACHE_NAME) {
            console.log('[Service Worker] Deleting old cache:', key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event: Intelligent routing for assets vs. API network calls
self.addEventListener('fetch', e => {
  const requestUrl = new URL(e.request.url);

  // Strategy A: Direct Network Bypass for API endpoints (Let FastAPI handle data)
  if (requestUrl.pathname.includes('/api/')) {
    e.respondWith(
      fetch(e.request).catch(() => {
        // Fallback response if user is offline and requests API data
        return new Response(
          JSON.stringify({ error: "Offline. Syncing parameters locally." }), 
          { headers: { 'Content-Type': 'application/json' } }
        );
      })
    );
    return;
  }

  // Strategy B: Cache-First, Network-Fallback for local assets
  if (requestUrl.origin === location.origin) {
    e.respondWith(
      caches.match(e.request).then(cachedResponse => {
        if (cachedResponse) {
          return cachedResponse; // Return fast from cache
        }

        // Dynamically cache any new local files accessed while browsing
        return fetch(e.request).then(networkResponse => {
          if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
            return networkResponse;
          }
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(e.request, responseToCache);
          });
          return networkResponse;
        });
      })
    );
  }
});
