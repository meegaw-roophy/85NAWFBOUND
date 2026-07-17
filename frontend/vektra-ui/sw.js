const CACHE_NAME = 'vektra-v3';

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
  self.skipWaiting();
});
// Activate Event: Safely clear out OLD versions of Vektra caches only
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(key => {
            return caches.delete(key);
        })
      );
    })
  );
});

// Fetch Event: Intelligent routing for assets vs. API network calls
self.addEventListener('fetch', e => {
  const requestUrl = new URL(e.request.url);

  // 1. DO NOT cache API calls (already handled)
  // 2. DO NOT cache the root index or service worker updates
  if (requestUrl.pathname.includes('/api/') || requestUrl.pathname.includes('/sw.js')) {
    return e.respondWith(fetch(e.request));
  }

  // 3. For everything else (CSS, JS, images), use network-first or cache-first
    e.respondWith(
    caches.match(e.request).then(cachedResponse => cachedResponse || fetch(e.request))
        );
});

