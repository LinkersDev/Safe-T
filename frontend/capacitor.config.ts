import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.safet.banking',
  appName: 'SafeT',
  webDir: 'dist',
  server: {
    androidScheme: 'http',
    cleartext: true, // Allow HTTP in development only
    // SECURITY: Restrict navigation to known domains
    allowNavigation: [
      'localhost',
      '127.0.0.1',
      '192.168.13.105',
      '*.safet.com',
      'api.safet.com'
    ]
  },
  android: {
    buildOptions: {
      releaseType: 'APK'
    }
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      backgroundColor: '#0A2540',
      androidScaleType: 'CENTER_CROP',
      showSpinner: false
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#0A2540'
    },
    Keyboard: {
      resize: 'body', // NOTE: Test with fixed headers, modals, bottom nav
      style: 'DARK',
      resizeOnFullScreen: true
    }
  }
};

export default config;
