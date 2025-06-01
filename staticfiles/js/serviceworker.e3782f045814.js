// Service Worker for 1Matrix PWA

const CACHE_NAME = '1matrix-cache-v1';
const urlsToCache = [
  '/',
  '/static/js/onematrix/style.css',
  '/static/js/onematrix/style2.css',
  '/static/js/1matrix/script.js',
  '/static/js/onematrix/script.js',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/static/icons/apple-icon-180x180.png',
  'https://cdn.tailwindcss.com',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
  'https://unpkg.com/@dotlottie/player-component@2.7.12/dist/dotlottie-player.mjs'
];

// Install service worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Cache opened');
        return cache.addAll(urlsToCache);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate service worker and clean up old caches
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
    .then(() => self.clients.claim())
  );
});

// Fetch resources
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return the response
        if (response) {
          return response;
        }

        // Clone the request
        const fetchRequest = event.request.clone();

        return fetch(fetchRequest)
          .then(response => {
            // Check if valid response
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // Clone the response
            const responseToCache = response.clone();

            caches.open(CACHE_NAME)
              .then(cache => {
                // Omit queries and fragments from the cache key
                const url = new URL(event.request.url);
                const cacheKey = event.request.mode === 'navigate' 
                  ? new Request(url.origin + url.pathname) 
                  : event.request;
                
                cache.put(cacheKey, responseToCache);
              });

            return response;
          })
          .catch(error => {
            // Provide a fallback for navigation requests if offline
            if (event.request.mode === 'navigate') {
              return caches.match('/');
            }
            
            console.error('Fetch failed:', error);
            // You might want to return a custom offline page here
          });
      })
  );
});

// Handle push notifications
self.addEventListener('push', event => {
  if (event.data) {
    const data = event.data.json();
    const options = {
      body: data.body || 'New notification from 1Matrix',
      icon: '/static/icons/icon-192x192.png',
      badge: '/static/icons/icon-192x192.png',
      data: {
        url: data.url || '/'
      }
    };
    
    event.waitUntil(
      self.registration.showNotification(data.title || '1Matrix', options)
    );
  }
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  event.waitUntil(
    clients.openWindow(event.notification.data.url)
  );
}); 