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

  // 1. ABSOLUTE BYPASS: If it hits your Render API domain, or uses POST/PUT methods, let it go to the internet directly
  if (
    requestUrl.hostname === '://onrender.com' || 
    requestUrl.pathname.includes('/api/v1') || 
    e.request.method !== 'GET'
  ) {
    return; // Returning nothing completely hands control back to the browser network layer, bypassing sw.js entirely
  }

  // 2. DO NOT cache the service worker itself
  if (requestUrl.pathname.includes('/sw.js')) {
    return;
  }

  // 3. For static assets (CSS, JS, UI Images), use cache-first strategy
  e.respondWith(
    caches.match(e.request).then(cachedResponse => {
      return cachedResponse || fetch(e.request);
    })
  );
});


