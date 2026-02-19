const CACHE_NAME = 'ai-value-board-v1';
const STATIC_URLS = [
    '/',
    '/static/css/styles.css',
    '/static/img/logo_spark.svg',
    '/manifest.json'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_URLS))
    );
});

self.addEventListener('fetch', (event) => {
    // Try to use the network first, fall back to cache for offline capabilities
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});
