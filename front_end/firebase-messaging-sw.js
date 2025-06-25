// This service worker is now completely independent of the Firebase SDK.
// It handles the 'push' event, which is the native browser event for push notifications.

self.addEventListener('push', function(event) {
  console.log('[Service Worker] Push Received.');

  // The data from your backend's FCM payload is in event.data
  const pushData = event.data.json();
  console.log('[Service Worker] Push data: ', pushData);

  // The 'notification' object is what your backend sends.
  const title = pushData.notification.title;
  const options = {
    body: pushData.notification.body,
    icon: '/icon.png', // Make sure you have an icon.png in your public folder
    data: pushData.data // This passes data like room_id to the click handler
  };

  // The waitUntil() method ensures the browser doesn't terminate the
  // service worker before the notification is shown.
  event.waitUntil(self.registration.showNotification(title, options));
});

// Optional: Handle notification clicks
self.addEventListener('notificationclick', function(event) {
  console.log('[Service Worker] Notification click Received.');

  event.notification.close();

  // This example focuses the browser tab if it's already open, or opens a new one.
  event.waitUntil(
    clients.openWindow('/') // You can add the room_id here later: `clients.openWindow('/chat/' + event.notification.data.room_id)`
  );
});

self.addEventListener('install', () => console.log('Service Worker: install event'));
self.addEventListener('activate', () => console.log('Service Worker: activate event'));