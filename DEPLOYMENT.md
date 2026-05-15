# SaFe-T Production Deployment Guide

## 🚀 Production Setup Complete

**Backend API:** https://api.safe-t-app.site  
**Status:** ✅ Deployed

---

## 📋 Quick Deployment Steps

### 1️⃣ Configure Production Environment

#### Frontend Web App

```bash
cd frontend

# Create production environment file
cp .env.production.example .env.production

# Edit .env.production (already configured)
# VITE_API_BASE_URL=https://api.safe-t-app.site
# VITE_DEV_MOCK_MODE=false
```

#### Frontend Mobile App

The mobile app will automatically use the production API when built with `--mode production`.

---

### 2️⃣ Build for Production

#### Web App (PWA)

```bash
cd frontend

# Install dependencies (if not already)
npm install

# Build for production
npm run build:prod

# Preview production build locally (optional)
npm run preview
```

**Output:** `frontend/dist/` folder ready for deployment

#### Mobile App (Android)

```bash
cd frontend

# Build mobile app with production API
npm run build:mobile:prod

# Open Android Studio to build release APK
npm run cap:open:android

# Or build release APK from command line
npm run android:prod
```

**Output:** `frontend/android/app/build/outputs/apk/release/app-release.apk`

---

### 3️⃣ Deploy Web App

#### Option A: Static Hosting (Netlify, Vercel, etc.)

```bash
# Deploy dist folder to your hosting provider
# Example with Netlify CLI:
cd frontend
npm install -g netlify-cli
netlify deploy --prod --dir=dist
```

#### Option B: Manual Upload

1. Build the app: `npm run build:prod`
2. Upload `frontend/dist/` folder to your web server
3. Configure server for SPA routing (see below)

---

### 4️⃣ Server Configuration

#### Nginx (Recommended)

```nginx
server {
    listen 80;
    server_name safe-t-app.site www.safe-t-app.site;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name safe-t-app.site www.safe-t-app.site;
    
    # SSL certificates
    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/key.pem;
    
    root /var/www/safe-t-app/dist;
    index index.html;
    
    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # SPA routing - serve index.html for all routes
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
}
```

#### Apache

```apache
<VirtualHost *:80>
    ServerName safe-t-app.site
    Redirect permanent / https://safe-t-app.site/
</VirtualHost>

<VirtualHost *:443>
    ServerName safe-t-app.site
    DocumentRoot /var/www/safe-t-app/dist
    
    SSLEngine on
    SSLCertificateFile /path/to/ssl/cert.pem
    SSLCertificateKeyFile /path/to/ssl/key.pem
    
    <Directory /var/www/safe-t-app/dist>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted
        
        # SPA routing
        RewriteEngine On
        RewriteBase /
        RewriteRule ^index\.html$ - [L]
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule . /index.html [L]
    </Directory>
    
    # Cache static assets
    <FilesMatch "\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$">
        Header set Cache-Control "max-age=31536000, public, immutable"
    </FilesMatch>
</VirtualHost>
```

---

## 🔒 Security Checklist

### Backend (Already Deployed)
- ✅ HTTPS enabled (api.safe-t-app.site)
- ✅ CORS configured for production domain
- ✅ Environment variables secured
- ✅ Database credentials protected
- ✅ Debug mode disabled

### Frontend (To Configure)
- ⏳ HTTPS enabled for web app
- ⏳ Environment variables set to production
- ⏳ API URL pointing to production backend
- ⏳ Service worker configured (PWA)
- ⏳ Security headers configured

### Mobile App
- ✅ HTTPS scheme configured
- ✅ Network security config allows HTTPS
- ✅ Production API domain whitelisted
- ⏳ Release APK signed with keystore

---

## 📱 Mobile App Release

### Generate Signing Key (First Time Only)

```bash
cd frontend/android

# Generate keystore
keytool -genkey -v -keystore safet-release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias safet-key

# Follow prompts and remember the passwords!
```

### Configure Signing

Edit `frontend/android/app/build.gradle`:

```gradle
android {
    ...
    signingConfigs {
        release {
            storeFile file("safet-release-key.jks")
            storePassword "your-store-password"
            keyAlias "safet-key"
            keyPassword "your-key-password"
        }
    }
    
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled true
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
}
```

### Build Release APK

```bash
cd frontend

# Build production APK
npm run android:prod

# APK location:
# frontend/android/app/build/outputs/apk/release/app-release.apk
```

### Test Release APK

```bash
# Install on device
adb install frontend/android/app/build/outputs/apk/release/app-release.apk

# Test all features:
# - Login with OTP
# - View accounts
# - Make transfers
# - Check real-time updates
```

---

## 🧪 Testing Production Setup

### 1. Test Backend API

```bash
# Health check
curl https://api.safe-t-app.site/api/health/

# Login endpoint
curl -X POST https://api.safe-t-app.site/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+252633227391"}'
```

### 2. Test Web App

1. Open browser: https://safe-t-app.site (when deployed)
2. Open DevTools → Network tab
3. Login with phone number
4. Verify API calls go to `https://api.safe-t-app.site`
5. Check for HTTPS (green padlock)
6. Test all features

### 3. Test Mobile App

1. Install release APK on device
2. Open app
3. Login with phone number
4. Verify OTP received via Twilio
5. Test all features:
   - Account balance
   - Transfers
   - QR payments
   - Bill payments
   - Transaction history

---

## 🌐 CORS Configuration

### Backend Django Settings

Ensure your backend allows the production frontend domain:

```python
# config/settings/prod.py or base.py

CORS_ALLOWED_ORIGINS = [
    "https://safe-t-app.site",
    "https://www.safe-t-app.site",
]

# For mobile app (if needed)
CORS_ALLOW_ALL_ORIGINS = False  # Keep False for security

# Allowed hosts
ALLOWED_HOSTS = [
    "api.safe-t-app.site",
    "safe-t-app.site",
]
```

---

## 📊 Monitoring & Analytics

### Backend Monitoring

```bash
# Check backend logs
ssh your-server
tail -f /var/log/safet/backend.log

# Check Django errors
tail -f /var/log/safet/django-error.log

# Monitor API requests
tail -f /var/log/nginx/access.log | grep api.safe-t-app.site
```

### Frontend Monitoring

Add analytics to track usage:

```typescript
// src/core/analytics/analytics.ts
export const trackPageView = (page: string) => {
  // Google Analytics, Mixpanel, etc.
  console.log('Page view:', page)
}

export const trackEvent = (event: string, data?: any) => {
  console.log('Event:', event, data)
}
```

---

## 🚨 Troubleshooting

### Issue: API calls failing

**Check:**
1. Backend is running: `curl https://api.safe-t-app.site/api/health/`
2. CORS configured correctly
3. Frontend `.env.production` has correct API URL
4. Browser console for errors

**Fix:**
```bash
# Rebuild with correct API URL
cd frontend
rm -rf dist
npm run build:prod
```

### Issue: Mobile app can't connect

**Check:**
1. Network security config allows HTTPS
2. Capacitor config has correct domain
3. App built with production mode

**Fix:**
```bash
cd frontend
npm run build:mobile:prod
npx cap sync
```

### Issue: HTTPS not working

**Check:**
1. SSL certificate valid
2. Server configuration correct
3. Firewall allows port 443

**Fix:**
```bash
# Test SSL
openssl s_client -connect api.safe-t-app.site:443

# Renew certificate (Let's Encrypt)
sudo certbot renew
```

### Issue: OTP not received

**Check:**
1. Twilio credentials correct in backend `.env`
2. Phone number verified (trial account)
3. Twilio console for delivery status

**Fix:**
- Check backend logs for Twilio errors
- Verify Twilio account has credits
- Check phone number format (+252...)

---

## 📦 Deployment Checklist

### Pre-Deployment
- [ ] Backend deployed and tested
- [ ] Backend HTTPS working
- [ ] Backend CORS configured
- [ ] Twilio credentials configured
- [ ] Database backed up

### Frontend Web
- [ ] `.env.production` created with production API URL
- [ ] Build production bundle: `npm run build:prod`
- [ ] Test production build locally: `npm run preview`
- [ ] Upload `dist/` to web server
- [ ] Configure server for SPA routing
- [ ] Enable HTTPS
- [ ] Test web app in browser
- [ ] Verify API calls work
- [ ] Test all features (login, transfers, etc.)

### Frontend Mobile
- [ ] `.env.production` configured
- [ ] Capacitor config updated with production domain
- [ ] Build production APK: `npm run build:mobile:prod`
- [ ] Sign APK with release keystore
- [ ] Test APK on real device
- [ ] Verify API calls work
- [ ] Test all features
- [ ] Upload to Google Play Store (optional)

### Post-Deployment
- [ ] Monitor backend logs
- [ ] Monitor frontend errors
- [ ] Test user registration flow
- [ ] Test OTP delivery
- [ ] Test payments
- [ ] Set up monitoring/analytics
- [ ] Document any issues

---

## 🎯 Production URLs

| Service | URL | Status |
|---------|-----|--------|
| Backend API | https://api.safe-t-app.site | ✅ Deployed |
| Web App | https://safe-t-app.site | ⏳ To Deploy |
| Mobile App | Google Play Store | ⏳ To Upload |

---

## 📞 Support

**Issues?** Check:
1. Backend logs
2. Frontend console errors
3. Network tab in DevTools
4. Twilio console for OTP delivery

**Need Help?**
- Email: support@safe-t-app.site
- GitHub Issues: https://github.com/LinkersDev/Safe-T/issues

---

## 🎉 Success Criteria

Your deployment is successful when:

✅ Web app loads at https://safe-t-app.site  
✅ Mobile app connects to production API  
✅ Users can register with phone number  
✅ OTP received via Twilio SMS  
✅ Login works  
✅ Account balances display  
✅ Transfers work  
✅ Real-time updates work  
✅ No console errors  
✅ HTTPS working (green padlock)  

---

**Built with ❤️ by LinkersDev**
