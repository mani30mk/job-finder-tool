# Job Hunter — Complete Deployment Guide

Three goals, one document:
1. **Mobile preview** — see it on your phone right now, no deployment needed
2. **Web app** — deploy to Vercel so it's always accessible at a URL
3. **Android APK** — install as a real app via PWA or Capacitor

---

## Part 1 — Mobile Preview (5 minutes, do this first)

This lets you see the app on your phone immediately using your local WiFi.

### Step 1 — Find your PC's local IP

**Windows:**
```
ipconfig
```
Look for `IPv4 Address` under your WiFi adapter. Example: `192.168.1.105`

**Linux/Mac:**
```
ip addr show   # or: ifconfig
```

### Step 2 — Start the backend

```bash
cd job-hunter
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` is critical — without it, the API is only accessible from your PC.

### Step 3 — Start the frontend

```bash
cd frontend-integrated
pnpm install
pnpm dev -- --host 0.0.0.0
```

The `--host 0.0.0.0` flag makes Next.js accessible from your phone.

### Step 4 — Open on your phone

Make sure your phone and PC are on the **same WiFi network**, then open:

```
http://192.168.1.105:3000        ← replace with your actual IP
```

> **Tip:** To simulate what it looks like as a full-screen app, in Chrome on Android:
> tap ⋮ → **Add to Home screen** → Open from home screen.
> This hides the browser chrome and gives you the app feel immediately.

### Step 5 — Configure the API URL

On your phone, open the app → go to **Profile** → set API URL to:
```
http://192.168.1.105:8000
```
Tap **Test** — should show ✅ Connected.

---

## Part 2 — Chrome DevTools Mobile Preview (on your PC)

To preview without a phone while developing:

1. Open `http://localhost:3000` in Chrome
2. Press `F12` → click the **Toggle device toolbar** icon (📱) or press `Ctrl+Shift+M`
3. Select a device from the dropdown — use **Pixel 7** or **Galaxy S21**
4. Reload the page

This simulates touch events, viewport, and pixel density accurately.

---

## Part 3 — Web Deployment (Vercel)

### Prerequisites
- Push your `frontend-integrated` folder to a GitHub repo
- Sign up at [vercel.com](https://vercel.com) (free)

### Backend first — expose it publicly

Your FastAPI backend needs a public URL for the deployed web app. Two options:

**Option A — Cloudflare Tunnel (free, permanent URL, recommended)**
```bash
# Install cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/
cloudflared tunnel --url http://localhost:8000
```
This gives you a URL like `https://random-words.trycloudflare.com` — use this as your API URL.

**Option B — Railway.app (deploy FastAPI to cloud)**
1. Push `job-hunter/` to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Set start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
4. Set env var: `DB_PATH=/app/jobs.db`
5. Railway gives you a `https://your-app.railway.app` URL

### Deploy frontend to Vercel

1. Push `frontend-integrated` to GitHub
2. Go to [vercel.com/new](https://vercel.com/new) → Import repo
3. Set environment variable:
   ```
   NEXT_PUBLIC_API_URL = https://your-backend-url.com
   ```
4. Click Deploy — Vercel handles everything else

Your web app will be live at: `https://your-app-name.vercel.app`

### DNS (optional — your own domain)
In Vercel dashboard → Domains → Add `jobs.yourdomain.com`

---

## Part 4 — Android App

Two paths: **PWA** (5 minutes, no Play Store) or **Capacitor** (full APK, Play Store ready).

---

### Path A — PWA Install (Easiest — do this first)

The PWA files are already set up (`manifest.json`, `sw.js`, updated `layout.tsx`).

**Steps:**
1. Deploy to Vercel (Part 3 above) — PWA requires HTTPS
2. On your Android phone, open the URL in **Chrome**
3. Chrome will show a banner: **"Add Job Hunter to Home screen"**
   - If no banner: tap ⋮ → **Install app** or **Add to home screen**
4. Tap Install → the app appears in your app drawer

**What you get:**
- ✅ Full-screen (no browser bar)
- ✅ Home screen icon
- ✅ App drawer entry
- ✅ Offline support (saved jobs visible without internet)
- ✅ Instant updates (no reinstall needed)
- ❌ Not in Play Store (can't share with others)

---

### Path B — Capacitor APK (Full Android App)

Use this if you want a real `.apk` / `.aab` for Play Store.

#### Prerequisites

Install these first (takes ~30 min):

| Tool | Download |
|---|---|
| Node.js 18+ | [nodejs.org](https://nodejs.org) |
| Java JDK 17 | [adoptium.net](https://adoptium.net) |
| Android Studio | [developer.android.com/studio](https://developer.android.com/studio) |
| Android SDK (via Android Studio) | Install inside Android Studio |

After Android Studio install, open it → SDK Manager → install:
- Android SDK Platform 34
- Android SDK Build-Tools 34
- Android Emulator (for testing without a phone)

Set environment variables (Windows — add to System Environment Variables):
```
ANDROID_HOME = C:\Users\YourName\AppData\Local\Android\Sdk
JAVA_HOME = C:\Program Files\Eclipse Adoptium\jdk-17.x.x.x-hotspot
```
Add to PATH:
```
%ANDROID_HOME%\tools
%ANDROID_HOME%\platform-tools
```

#### Step 1 — Install Capacitor

```bash
cd frontend-integrated
pnpm add @capacitor/core @capacitor/cli @capacitor/android @capacitor/local-notifications
```

#### Step 2 — Build a static export

Uncomment `output: 'export'` in `next.config.mjs`:
```js
const nextConfig = {
  typescript: { ignoreBuildErrors: true },
  images: { unoptimized: true },
  output: 'export',    // ← uncomment this line
};
```

Set your backend URL in `.env.local`:
```
NEXT_PUBLIC_API_URL=https://your-backend-url.com
```

Build:
```bash
pnpm build
# This creates an 'out/' folder with static HTML/JS/CSS
```

#### Step 3 — Initialize Capacitor

```bash
npx cap init "Job Hunter" "com.manikandan.jobhunter" --web-dir out
npx cap add android
```

#### Step 4 — Sync and open Android Studio

```bash
npx cap sync android
npx cap open android
```

Android Studio opens with your project.

#### Step 5 — Build APK in Android Studio

1. Wait for Gradle sync to finish (first time is slow — ~5 min)
2. Menu → **Build → Build Bundle(s)/APK(s) → Build APK(s)**
3. Wait for build → click **locate** in the notification
4. APK is at: `android/app/build/outputs/apk/debug/app-debug.apk`

#### Step 6 — Install on your phone

**Via USB:**
```bash
# Enable USB Debugging on phone: Settings → Developer Options → USB Debugging
adb install android/app/build/outputs/apk/debug/app-debug.apk
```

**Via file transfer:**
1. Copy `app-debug.apk` to your phone
2. Open the file → Android will prompt to install
3. You may need to allow "Install from unknown sources" in Settings

---

### Path C — Dev Mode on Physical Device (fastest for testing)

This lets you test the Capacitor shell with your live dev server — no rebuild needed on code changes.

1. Uncomment the `server.url` line in `capacitor.config.ts`:
   ```ts
   server: {
     url: 'http://192.168.1.105:3000',   // your PC IP
     androidScheme: 'http',
     cleartext: true,
   }
   ```
2. Start your dev server: `pnpm dev -- --host 0.0.0.0`
3. Run on device: `npx cap run android`

Changes to your frontend code appear on the phone instantly (hot reload works through the USB connection).

---

## Part 5 — Play Store (Optional)

### Requirements
- Google Play Developer account: [play.google.com/console](https://play.google.com/console) ($25 one-time)
- Signed release APK/AAB

### Generate signed release build

1. In Android Studio: **Build → Generate Signed Bundle/APK**
2. Choose **APK** (or AAB for Play Store)
3. Create a new keystore — **save the keystore file and passwords somewhere safe, you can never recover them**
4. Select **Release** build variant → Finish

### Upload to Play Store

1. Play Console → Create app
2. Fill: Title "Job Hunter", Category "Productivity"
3. Upload APK/AAB
4. Add 2-8 screenshots (can screenshot from your phone)
5. Write a short description
6. Add a privacy policy (required — even for personal apps)
7. Submit for review (~3–7 days for first app)

---

## Workflow Summary

```
Daily development:
  pnpm dev + uvicorn → test at localhost:3000

Mobile preview (no deployment):
  Add --host 0.0.0.0 to both servers → open IP:3000 on phone

Web app:
  pnpm build → push to GitHub → Vercel auto-deploys

Android APK (development):
  npx cap sync → npx cap run android (with server.url set)

Android APK (production):
  uncomment output:'export' → pnpm build → npx cap sync → Build APK in Android Studio

PWA install (quickest path to phone):
  Deploy to Vercel → open in Chrome on Android → Add to Home Screen
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Phone can't reach backend | Check both are on same WiFi. Check Windows Firewall isn't blocking port 8000. |
| "Add to Home Screen" not showing | Must be served over HTTPS (use Vercel). Clear Chrome cache. |
| Gradle sync fails | File → Invalidate Caches → Restart. Make sure JAVA_HOME is set correctly. |
| `adb: command not found` | Add `%ANDROID_HOME%\platform-tools` to PATH and restart terminal. |
| App shows mock data | Check `NEXT_PUBLIC_API_URL` in `.env.local`. Must not be empty. |
| CORS error in browser | Backend already has CORS `*`. If using Cloudflare Tunnel, check the tunnel is running. |
| White screen on Android | Check `webDir` in `capacitor.config.ts` matches where `next build` outputs (`out/`). |
