// Service Worker for 1Matrix PWA

const CACHE_NAME = '1matrix-cache-v1';
const APP_SHELL = [
  '/',
  '/static/js/onematrix/style.css',
  '/static/js/onematrix/style2.css',
  '/static/js/1matrix/script.js',
  '/static/js/onematrix/script.js',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/static/icons/apple-icon-180x180.png',
  '/offline/',  // Path to offline page
  'https://cdn.tailwindcss.com',
  'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap',
  'https://unpkg.com/@dotlottie/player-component@2.7.12/dist/dotlottie-player.mjs'
];

// URLs to be explicitly cached
const urlsToCache = [...APP_SHELL];

// Install service worker
self.addEventListener('install', event => {
  console.log('[ServiceWorker] Installing Service Worker...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[ServiceWorker] Pre-caching app shell');
        return cache.addAll(urlsToCache);
      })
      .then(() => {
        console.log('[ServiceWorker] Skip waiting on install');
        return self.skipWaiting();
      })
      .catch(error => {
        console.error('[ServiceWorker] Install error:', error);
      })
  );
});

// Activate service worker and clean up old caches
self.addEventListener('activate', event => {
  console.log('[ServiceWorker] Activating Service Worker...');
  
  const cacheWhitelist = [CACHE_NAME];
  
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            console.log('[ServiceWorker] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
    .then(() => {
      console.log('[ServiceWorker] Claiming clients');
      return self.clients.claim();
    })
  );
});

// Fetch resources
self.addEventListener('fetch', event => {
  console.log('[ServiceWorker] Fetch event for', event.request.url);
  
  // For navigation requests (HTML pages)
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          console.log('[ServiceWorker] Fallback to offline page for navigation');
          return caches.match('/offline/');
        })
    );
    return;
  }

  // For other requests, try cache first, then network
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - return the response
        if (response) {
          console.log('[ServiceWorker] Found in cache:', event.request.url);
          return response;
        }

        console.log('[ServiceWorker] Network request for:', event.request.url);
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
                
                console.log('[ServiceWorker] Caching new resource:', event.request.url);
                cache.put(cacheKey, responseToCache);
              });

            return response;
          })
          .catch(error => {
            console.error('[ServiceWorker] Fetch failed:', error);
            
            // Check if request is for an image and provide a fallback
            if (event.request.url.match(/\.(jpg|jpeg|png|gif|svg)$/i)) {
              return caches.match('/static/icons/icon-192x192.png');
            }
            
            // Check for HTML request
            if (event.request.headers.get('Accept').includes('text/html')) {
              return caches.match('/offline/');
            }
            
            // Default fallback
            return new Response('Network error occurred', {
              status: 408,
              headers: new Headers({
                'Content-Type': 'text/plain'
              })
            });
          });
      })
  );
});

// Handle push notifications
self.addEventListener('push', event => {
  console.log('[ServiceWorker] Push received:', event);
  
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
  console.log('[ServiceWorker] Notification click received:', event);
  
  event.notification.close();
  
  event.waitUntil(
    clients.openWindow(event.notification.data.url)
  );
}); 