// sw.js - minimal service worker, does not intercept API calls
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", () => self.clients.claim());
// No fetch handler - let all requests pass through normally
