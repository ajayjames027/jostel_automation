const CACHE_NAME = 'jostel-cache-v10';
const urlsToCache = [
  '/jostel_automation/',
  '/jostel_automation/index.html',
  '/jostel_automation/Student_Exam_Lookup.html',
  '/jostel_automation/exam.html',
  '/jostel_automation/find.html',
  '/jostel_automation/exam/',
  '/jostel_automation/find/',
  '/jostel_automation/Grade_Fetcher_Dashboard.html',
  '/jostel_automation/Earn_While_You_Learn.html',
  '/jostel_automation/Usage_Analytics.html',
  '/jostel_automation/Empty_Quiz_Finder.html',
  '/jostel_automation/Component_1_Master_Hub.html',
  '/jostel_automation/jostel_logo.png',
  '/jostel_automation/college_logo.png'
];

// Install Event
self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

// Fetch Event (Network First, fallback to Cache)
self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Automatically cache the fresh response to keep things updated
        if (response && response.status === 200 && response.type === 'basic') {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
        }
        return response;
      })
      .catch(() => {
        // If network fails, serve from cache
        return caches.match(event.request);
      })
  );
});

// Activate Event (Cleanup old caches instantly)
self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
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
