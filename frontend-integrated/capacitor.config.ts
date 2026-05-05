import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.manikandan.jobhunter',
  appName: 'Job Hunter',
  // Points to the Next.js static export output folder
  webDir: 'out',
  server: {
    // During dev: point to your live Next.js dev server so you get hot reload on device
    // Comment this out for production APK builds
    // url: 'http://192.168.1.x:3000',
    // androidScheme: 'http',
    // cleartext: true,

    // Production: use bundled files (comment the above, uncomment below)
    androidScheme: 'https',
  },
  plugins: {
    LocalNotifications: {
      smallIcon: 'ic_stat_icon_config_sample',
      iconColor: '#2563eb',
    },
  },
  android: {
    allowMixedContent: true,       // needed for http API calls during dev
    captureInput: true,
    webContentsDebuggingEnabled: true,   // set false for Play Store release
  },
};

export default config;
