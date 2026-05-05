# Android App Deployment Guide

This guide explains how to deploy the JobHunter web application as an Android app using various methods.

## Method 1: Progressive Web App (PWA) - Recommended

### Benefits
- Single codebase for web and app
- Installable from home screen
- Offline functionality with Service Workers
- Push notifications support
- Near-native performance

### Steps

#### 1. Create PWA Manifest
Create `public/manifest.json`:
```json
{
  "name": "JobHunter - Find Your Perfect Job",
  "short_name": "JobHunter",
  "description": "Smart job aggregation platform with AI-powered matching",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#0066cc",
  "orientation": "portrait-primary",
  "icons": [
    {
      "src": "/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/icon-maskable-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "maskable"
    }
  ],
  "screenshots": [
    {
      "src": "/screenshot-mobile.png",
      "sizes": "540x720",
      "type": "image/png",
      "form_factor": "narrow"
    },
    {
      "src": "/screenshot-desktop.png",
      "sizes": "1280x720",
      "type": "image/png",
      "form_factor": "wide"
    }
  ],
  "categories": ["productivity"]
}
```

#### 2. Link Manifest in Layout
Update `app/layout.tsx`:
```tsx
<head>
  <link rel="manifest" href="/manifest.json" />
  <meta name="theme-color" content="#0066cc" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="default" />
  <meta name="apple-mobile-web-app-title" content="JobHunter" />
</head>
```

#### 3. Add Service Worker
Create `public/sw.js`:
```javascript
const CACHE_NAME = 'jobhunter-v1';
const urlsToCache = [
  '/',
  '/jobs',
  '/saved',
  '/profile',
  '/styles.css'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(urlsToCache);
    })
  );
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request).then(response => {
        const clonedResponse = response.clone();
        caches.open(CACHE_NAME).then(cache => {
          cache.put(event.request, clonedResponse);
        });
        return response;
      });
    }).catch(() => {
      // Return offline page or cached response
    })
  );
});
```

#### 4. Install Service Worker
Add to `app/layout.tsx`:
```tsx
<script>
  {`
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(err => 
        console.error('Service Worker registration failed:', err)
      );
    }
  `}
</script>
```

#### 5. Build & Deploy
```bash
pnpm build
# Deploy to Vercel or any hosting platform
vercel deploy
```

#### 6. Installation on Android
1. Open the web app in Chrome
2. Tap menu (⋮) → "Install app" or "Add to Home screen"
3. Confirm installation
4. App appears on home screen and app drawer

---

## Method 2: Electron App (Desktop + Android via Tauri)

### Benefits
- Desktop application (Windows, macOS, Linux)
- Single codebase
- Can be wrapped for Android with Tauri

### Steps

#### 1. Install Tauri
```bash
npm create tauri-app@latest
# Select: Web (then select Next.js project)
```

#### 2. Configure Tauri
Edit `src-tauri/tauri.conf.json`:
```json
{
  "build": {
    "frontendDist": "../out",
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build"
  },
  "app": {
    "windows": [{
      "fullscreen": false,
      "resizable": true,
      "title": "JobHunter"
    }]
  }
}
```

#### 3. Build for Desktop
```bash
npm run tauri build
```

#### 4. Build for Android
```bash
npm run tauri android build
```

---

## Method 3: Capacitor (Recommended for Hybrid Apps)

### Benefits
- Near-native performance
- Access to device APIs (camera, geolocation, etc.)
- Publish to Google Play Store
- Works on Android, iOS, Web

### Steps

#### 1. Install Capacitor
```bash
npm install @capacitor/core @capacitor/cli
npx cap init
```

#### 2. Add Android Platform
```bash
npm install @capacitor/android
npx cap add android
```

#### 3. Create Android Project
```bash
npx cap open android
```

#### 4. Configure `capacitor.config.json`
```json
{
  "appId": "com.jobhunter.app",
  "appName": "JobHunter",
  "webDir": "out",
  "server": {
    "androidScheme": "https",
    "cleartext": false
  },
  "plugins": {
    "Device": {},
    "Geolocation": {},
    "LocalNotifications": {}
  }
}
```

#### 5. Build & Sync
```bash
npm run build
npx cap sync
npx cap open android
```

#### 6. Build in Android Studio
- Open Android Studio
- Select Build → Build Bundle(s) / APK(s) → Build APK(s)
- Wait for completion
- APK is ready for testing on devices

---

## Method 4: Cordova App

### Benefits
- Mature framework
- Large plugin ecosystem
- Multiple platform support

### Steps

#### 1. Create Cordova Project
```bash
npm install -g cordova
cordova create JobHunter com.jobhunter.app JobHunter
cd JobHunter
cordova platform add android
```

#### 2. Add Web Content
```bash
# Copy built Next.js output to www folder
cp -r ../out/* ./www/
```

#### 3. Add Plugins
```bash
cordova plugin add cordova-plugin-geolocation
cordova plugin add cordova-plugin-contacts
cordova plugin add cordova-plugin-camera
```

#### 4. Build APK
```bash
cordova build android
```

---

## Method 5: React Native (Complete Rewrite)

### Benefits
- True native performance
- Access to all device APIs
- Best user experience
- Larger community

### Consideration
- Requires rewriting UI components
- Separate codebase for mobile
- More development time

---

## Publishing to Google Play Store

### Requirements
- Google Play Developer Account ($25 one-time fee)
- Signed APK/AAB file
- App icon (512x512px)
- Screenshots (4-8)
- Description and privacy policy
- Content rating questionnaire

### Steps

#### 1. Create Keystore (Sign APK)
```bash
keytool -genkey -v -keystore my-release-key.keystore \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias my-key-alias
```

#### 2. Sign APK/AAB
For Capacitor:
```bash
# In Android Studio:
# Build → Generate Signed Bundle / APK
# Select Release build type
# Choose your keystore
```

#### 3. Upload to Play Store
1. Go to Google Play Console
2. Create new app
3. Fill app details (name, category, pricing)
4. Upload APK/AAB
5. Add store listing:
   - Title: "JobHunter"
   - Short description: One line pitch
   - Full description: Detailed features
   - Screenshots: 4-8 per orientation
   - App icon & feature graphic
6. Add privacy policy
7. Set content rating
8. Review and publish

---

## Testing on Android Device

### Using Android Emulator
```bash
# List available emulators
emulator -list-avds

# Start emulator
emulator -avd <emulator_name>

# Deploy app
# For Capacitor:
npx cap run android
```

### Using Physical Device
1. Enable USB Debugging: Settings → Developer Options → USB Debugging
2. Connect via USB
3. Run:
```bash
# For Capacitor:
npx cap run android --device <device_id>
```

### Testing Checklist
- [ ] App launches without errors
- [ ] Navigation works (tap between tabs)
- [ ] Jobs load from API
- [ ] Save/unsave jobs works
- [ ] Search functionality works
- [ ] Filters work correctly
- [ ] Offline mode works
- [ ] Images load properly
- [ ] Touch targets are responsive
- [ ] Text is readable
- [ ] Performance is smooth
- [ ] Battery usage is reasonable
- [ ] App can be uninstalled cleanly

---

## Performance Optimization for Android

### APK Size Reduction
```bash
# Use code splitting
npm install --save-dev @next/bundle-analyzer
```

### Battery Optimization
- Minimize network calls
- Use efficient animations
- Implement aggressive caching
- Avoid background processes

### Memory Optimization
- Lazy load images
- Implement virtual scrolling for large lists
- Clean up event listeners
- Use efficient data structures

---

## Recommended Approach: Progressive Web App (PWA)

We recommend starting with **PWA** because:
1. ✅ Single codebase (web + app)
2. ✅ Instant installation (no app store review)
3. ✅ Immediate updates
4. ✅ Offline support
5. ✅ Low barrier to entry
6. ✅ Easy to maintain
7. ✅ Works everywhere

Then, if needed, upgrade to **Capacitor** for deeper device API access.

---

## Troubleshooting

### App Won't Install
- Check manifest.json is linked in layout
- Ensure served over HTTPS (required for PWA)
- Clear browser cache and try again

### Performance Issues
- Check Network tab in DevTools
- Look for large assets
- Enable gzip compression
- Use CDN for static files

### Offline Not Working
- Verify Service Worker is registered
- Check Service Worker scope
- Verify cache names match

### Touch Issues
- Ensure touch-target class is applied
- Test with actual Android device (emulator can be finicky)
- Check viewport meta tags

---

## Resources

- [PWA Guide](https://web.dev/progressive-web-apps/)
- [Capacitor Docs](https://capacitorjs.com/)
- [Tauri Docs](https://tauri.app/)
- [Google Play Console](https://play.google.com/console)
- [React Native](https://reactnative.dev/)
