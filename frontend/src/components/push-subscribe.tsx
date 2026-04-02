"use client";

import { useEffect, useRef } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const arr = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
  return arr;
}

export function PushSubscribe() {
  const { isAuthenticated } = useAuth();
  const subscribedRef = useRef(false);

  useEffect(() => {
    if (!isAuthenticated || subscribedRef.current) return;
    if (typeof window === "undefined" || !("serviceWorker" in navigator) || !("PushManager" in window)) return;

    let cancelled = false;

    async function subscribe() {
      try {
        let vapidResp;
        try {
          vapidResp = await api.getVapidKey();
        } catch {
          // Push not configured on backend — silently skip
          return;
        }
        const { vapid_public_key } = vapidResp;
        if (cancelled) return;

        const registration = await navigator.serviceWorker.ready;

        // Check if already subscribed in browser
        let subscription = await registration.pushManager.getSubscription();

        if (!subscription) {
          // Request permission and create new subscription
          const permission = await Notification.requestPermission();
          if (permission !== "granted" || cancelled) return;

          subscription = await registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(vapid_public_key) as unknown as BufferSource,
          });
        }

        const json = subscription.toJSON();
        if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) return;

        await api.pushSubscribe({
          endpoint: json.endpoint,
          p256dh: json.keys.p256dh,
          auth: json.keys.auth,
        });

        subscribedRef.current = true;
      } catch (err) {
        console.error("Push subscription failed:", err);
      }
    }

    subscribe();
    return () => { cancelled = true; };
  }, [isAuthenticated]);

  return null;
}
