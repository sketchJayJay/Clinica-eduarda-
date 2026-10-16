// V56: apenas arquivos da interface. Prontuários e respostas de APIs não são armazenados.
const CACHE_NAME = 'eduarda-clinica-v56';
const CORE_ASSETS = [
  '/static/app.css?v=56', '/static/app.js?v=56',
  '/static/vendor/bootstrap.min.css', '/static/vendor/bootstrap.bundle.min.js',
  '/static/vendor/bootstrap-icons.min.css', '/static/vendor/fonts/bootstrap-icons.woff2',
  '/static/vendor/fullcalendar.min.js', '/static/vendor/fullcalendar-locales.min.js',
  '/static/logo.png', '/static/logo_symbol.png'
];
self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS)).catch(() => null));
  self.skipWaiting();
});
self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys
    .filter((key) => key.startsWith('eduarda-clinica-') && key !== CACHE_NAME)
    .map((key) => caches.delete(key)))));
  self.clients.claim();
});
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || !url.pathname.startsWith('/static/')) return;
  event.respondWith(fetch(event.request).then((response) => {
    if (response.ok) {
      const copy = response.clone();
      event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy)));
    }
    return response;
  }).catch(() => caches.match(event.request)));
});
