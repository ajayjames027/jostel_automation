const CACHE_NAME = 'jostel-cache-v2';
const urlsToCache = [
  '/jostel_automation/',
  '/jostel_automation/index.html',
  '/jostel_automation/Grade_Fetcher_Dashboard.html',
  '/jostel_automation/Earn_While_You_Learn.html',
  '/jostel_automation/Usage_Analytics.html',
  '/jostel_automation/jostel_logo.png',
  '/jostel_automation/college_logo.png'
];

// Install Event
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

// Fetch Event
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return response
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});

// Activate Event (Cleanup old caches)
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
