// CACHE_VERSION is bumped on each build via the build script.
// Changing CACHE_NAME triggers activate → deletes old caches → forces fresh content.
const CACHE_VERSION = "1775806382035";
const CACHE_NAME = `letagentpay-${CACHE_VERSION}`;

const PRECACHE_URLS = ["/auth/signin"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Only cache http(s) — chrome-extension:// etc. are unsupported by Cache API
  if (url.protocol !== "https:" && url.protocol !== "http:") return;

  // Skip API calls, SSE, and Next.js assets — always go to network
  if (
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/_next/") ||
    url.pathname.includes("/events")
  ) {
    return;
  }

  // Network-first for HTML pages
  if (request.headers.get("accept")?.includes("text/html")) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => caches.match(request)),
    );
    return;
  }

  // Cache-first for static assets
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      });
    }),
  );
});

// Web Push notifications
self.addEventListener("push", (event) => {
  if (!event.data) return;

  let data;
  try {
    data = event.data.json();
  } catch {
    data = { title: "LetAgentPay", body: event.data.text() };
  }

  const options = {
    body: data.body || "",
    icon: "/icons/icon-192.png",
    badge: "/icons/icon-192.png",
    tag: data.data?.request_id || data.tag || "default",
    data: {
      url: data.url || "/dashboard",
      request_id: data.data?.request_id,
      agent_id: data.data?.agent_id,
    },
  };

  // Add action buttons for pending purchase requests
  if (data.data?.request_id) {
    options.actions = [
      { action: "approve", title: "Approve" },
      { action: "reject", title: "Reject" },
    ];
    options.requireInteraction = true;
  }

  event.waitUntil(
    self.registration.showNotification(data.title || "LetAgentPay", options),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const { action } = event;
  const requestId = event.notification.data?.request_id;

  // Handle approve/reject actions directly from notification
  if (requestId && (action === "approve" || action === "reject")) {
    event.waitUntil(
      fetch(`/api/v1/requests/${requestId}/${action}`, {
        method: "POST",
        credentials: "include",
      }).then(() => {
        // Notify open windows to refresh
        self.clients
          .matchAll({ type: "window" })
          .then((clients) =>
            clients.forEach((c) => c.postMessage({ type: "request_updated" })),
          );
      }),
    );
    return;
  }

  const url = event.notification.data?.url || "/dashboard";

  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clients) => {
        const existing = clients.find((c) => c.url.includes(url));
        if (existing) return existing.focus();
        return self.clients.openWindow(url);
      }),
  );
});
