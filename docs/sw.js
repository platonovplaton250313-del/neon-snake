/* NEON SNAKE + CHESS ARENA — офлайн-кэш PWA. */
const CACHE = 'neon-snake-v10';
const ASSETS = [
  './',
  './index.html',
  './css/style.css',
  './js/game.js',
  './manifest.webmanifest',
  './icons/favicon.png',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable-512.png',
  './icons/apple-touch-icon.png',
  './chess/',
  './chess/index.html',
  './chess/standalone.html',
  './chess/css/chess.css',
  './chess/js/engine.js',
  './chess/js/puzzles.js',
  './chess/js/puzzle-generator.js',
  './chess/js/stockfish-client.js',
  './chess/js/app.js',
  './chess/js/ai-worker.js',
  './chess/js/stockfish/stockfish-nnue-16-single.js',
  './chess/js/stockfish/stockfish-nnue-16-single.wasm',
  './chess/manifest.webmanifest',
  './chess/icons/favicon.png',
  './chess/icons/apple-touch-icon.png',
  './chess/icons/icon-192.png',
  './chess/icons/icon-512.png',
  './chess/icons/icon-maskable-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy)).catch(() => {});
          return response;
        })
        .catch(() => {
          const onlinePath = url.pathname;
          const fallback = onlinePath.indexOf('/chess') !== -1
            ? './chess/index.html'
            : './index.html';
          return caches.match(fallback).then((hit) => hit || caches.match('./index.html'));
        })
    );
    return;
  }

  event.respondWith(
    caches.match(request, { ignoreSearch: true }).then((hit) => {
      if (hit) return hit;
      return fetch(request).then((response) => {
        if (response && response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy)).catch(() => {});
        }
        return response;
      });
    })
  );
});
