// Service Worker for Crypto Engine PWA
const CACHE_NAME = 'crypto-platform-v2';
const STATIC_ASSETS = [
  '/manifest.json',
  '/static/icon-192.svg',
  '/static/icon-512.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Let network handle API, WebSocket, and dynamic dashboard calls
  if (event.request.url.includes('/api/') || event.request.url.includes('/ws/')) {
    return;
  }
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
