# SaFe-T - Secure Banking Platform

A modern, secure banking platform built with Django REST Framework and React + Ionic.

## 🚀 Features

### Core Banking
- ✅ **User Authentication** - Phone-based OTP authentication
- ✅ **Account Management** - Multiple account types (Savings, Checking)
- ✅ **Transactions** - Transfers, deposits, withdrawals
- ✅ **Payment Methods** - QR payments, bill payments
- ✅ **Transaction History** - Real-time balance updates

### Security
- ✅ **Multi-Provider OTP** - Twilio Verify, WhatsApp, Dev mode
- ✅ **PIN Protection** - Secure PIN-based authentication
- ✅ **Role-Based Access Control** - Customer and Staff roles
- ✅ **Fraud Detection** - ML-powered fraud scoring
- ✅ **Audit Logging** - Complete audit trail

### Mobile & Web
- ✅ **Progressive Web App** - Works on all devices
- ✅ **Native Android App** - Built with Capacitor
- ✅ **Responsive UI** - Mobile-first design
- ✅ **Real-time Updates** - Smart polling with background sync
- ✅ **Offline Support** - Works without internet

### Admin Features
- ✅ **Staff Dashboard** - Transaction monitoring
- ✅ **User Management** - KYC approval workflow
- ✅ **Transaction Approval** - Multi-level approval
- ✅ **Reporting** - Analytics and insights

---

## 📁 Project Structure

```
SaFe-T/
├── backend/              # Django REST API
│   ├── apps/
│   │   ├── accounts/     # Account management
│   │   ├── ledger/       # Double-entry ledger
│   │   ├── payments/     # Payment processing
│   │   ├── security/     # Authentication & OTP
│   │   └── users/        # User management
│   ├── config/           # Django settings
│   ├── docs/             # Backend documentation
│   └── requirements/     # Python dependencies
│
├── frontend/             # React + Ionic PWA
│   ├── src/
│   │   ├── app/          # App shell & routing
│   │   ├── core/         # Core utilities
│   │   ├── domains/      # Feature modules
│   │   └── shared/       # Shared components
│   ├── android/          # Android native app
│   ├── docs/             # Frontend documentation
│   └── public/           # Static assets
│
└── docs/                 # Project documentation
```

---

## 🛠️ Tech Stack

### Backend
- **Framework:** Django 6.0 + Django REST Framework 3.17
- **Database:** MySQL 8.0
- **Authentication:** JWT (Simple JWT)
- **OTP Providers:** Twilio Verify, WhatsApp (Tneenwh)
- **ML:** scikit-learn (fraud detection)
- **Security:** Argon2 password hashing

### Frontend
- **Framework:** React 18 + TypeScript
- **Mobile:** Ionic React + Capacitor
- **State Management:** React Query (TanStack Query)
- **Routing:** React Router v6
- **Styling:** Tailwind CSS + Ionic Components
- **Build Tool:** Vite

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- MySQL 8.0+
- Git

### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate      # Linux/Mac

# Install dependencies
pip install -r requirements/base.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load demo data (optional)
python manage.py seed_demo_data

# Start server
python manage.py runserver 0.0.0.0:8000
```

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your API URL

# Start dev server
npm run dev

# Build for production
npm run build

# Build Android app
npm run build:mobile
npx cap sync android
npx cap open android
```

---

## 🔐 Environment Variables

### Backend (.env)

```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=safet_db
DB_USER=safet_user
DB_PASSWORD=your-password
DB_HOST=127.0.0.1
DB_PORT=3306

# OTP Provider (dev | whatsapp | twilio_verify)
OTP_PROVIDER=twilio_verify
ENABLE_DEV_OTP=True

# Twilio Verify (for SMS OTP)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_VERIFY_SERVICE_SID=VAxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# WhatsApp OTP (optional)
TNEENWH_BASE_URL=https://api.tneenwh.com
TNEENWH_EMAIL=your-email@example.com
TNEENWH_PASSWORD=your-password
TNEENWH_SESSION_ID=your-session-uuid
TNEENWH_CHANNEL_SECRET=your-channel-secret

# JWT
ACCESS_TOKEN_LIFETIME_MINUTES=60
REFRESH_TOKEN_LIFETIME_DAYS=30

# Ledger
LEDGER_FEE_POOL_ACCOUNT_NUMBER=
LEDGER_CASH_ACCOUNT_NUMBER=9999000000000002

# ML Fraud Detection
ML_ENABLED=True
```

### Frontend (.env)

```bash
VITE_API_BASE_URL=http://localhost:8000/api
VITE_APP_NAME=SaFe-T
VITE_APP_VERSION=1.0.0
```

---

## 📱 OTP Providers

### 1. Twilio Verify (Recommended for Production)
- **Pros:** Managed service, reliable, trial-compatible
- **Cons:** Costs $0.05 per SMS
- **Setup:** See [TWILIO-QUICK-START.md](backend/docs/TWILIO-QUICK-START.md)

```bash
OTP_PROVIDER=twilio_verify
TWILIO_ACCOUNT_SID=ACxxxx
TWILIO_AUTH_TOKEN=xxxx
TWILIO_VERIFY_SERVICE_SID=VAxxxx
```

### 2. WhatsApp (Tneenwh)
- **Pros:** Free, uses WhatsApp
- **Cons:** Requires Tneenwh account
- **Setup:** Configure Tneenwh credentials

```bash
OTP_PROVIDER=whatsapp
TNEENWH_EMAIL=your-email
TNEENWH_PASSWORD=your-password
```

### 3. Dev Mode (Development Only)
- **Pros:** No external service needed, OTP printed to terminal
- **Cons:** Not for production
- **Setup:** No credentials needed

```bash
OTP_PROVIDER=dev
ENABLE_DEV_OTP=True
DEBUG=True
```

---

## 🧪 Testing

### Backend Tests
```bash
cd backend
python manage.py test
```

### Frontend Tests
```bash
cd frontend
npm run test
```

### E2E Tests
```bash
cd frontend
npm run test:e2e
```

---

## 📦 Deployment

### Backend (Production)

```bash
# Install production dependencies
pip install -r requirements/prod.txt

# Collect static files
python manage.py collectstatic --noinput

# Run with Gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### Frontend (Production)

```bash
# Build for web
npm run build

# Build for Android
npm run build:mobile
npx cap sync android
npx cap build android --release
```

---

## 📚 Documentation

### Backend
- [Twilio Verify Setup](backend/docs/TWILIO-QUICK-START.md)
- [Twilio Implementation](backend/docs/twilio-verify-implementation.md)
- [Performance Improvements](backend/docs/twilio-verify-improvements.md)

### Frontend
- [Batch 1 Results](frontend/docs/batch1-results.md)
- [Batch 2 Implementation](frontend/docs/batch2-implementation-complete.md)
- [App Icon Setup](frontend/docs/app-icon-setup-complete.md)
- [Validation Checklist](frontend/docs/batch1-validation-checklist.md)

---

## 🔒 Security Features

### Authentication
- Phone-based OTP authentication
- PIN protection for transactions
- JWT token-based sessions
- Refresh token rotation

### Authorization
- Role-based access control (RBAC)
- Permission-based guards
- Route-level protection
- API endpoint protection

### Data Protection
- Argon2 password hashing
- OTP hash storage (never plaintext)
- Encrypted sensitive data
- Audit logging

### Fraud Prevention
- ML-powered fraud scoring
- Transaction velocity checks
- IP tracking
- Device fingerprinting

---

## 🎨 Features Highlights

### Real-time Updates
- Smart polling with exponential backoff
- Background sync when app returns to foreground
- Query invalidation on data changes
- Optimistic UI updates

### Mobile Optimizations
- Lazy route loading
- Code splitting by platform
- Bundle size optimization
- Native splash screens and icons

### User Experience
- Pull-to-refresh on mobile
- Loading states
- Error handling
- Offline support

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is proprietary and confidential.

---

## 👥 Team

**LinkersDev** - Development Team

---

## 📞 Support

For support, email support@safet.com or open an issue.

---

## 🎯 Roadmap

### Phase 1 (Current)
- ✅ Core banking features
- ✅ OTP authentication
- ✅ Mobile app
- ✅ Real-time updates

### Phase 2 (Planned)
- ⏳ Biometric authentication
- ⏳ Card management
- ⏳ Loan processing
- ⏳ Investment accounts

### Phase 3 (Future)
- ⏳ Multi-currency support
- ⏳ International transfers
- ⏳ Merchant payments
- ⏳ Analytics dashboard

---

## 🙏 Acknowledgments

- Django REST Framework team
- React and Ionic teams
- Twilio for OTP services
- All open-source contributors

---

**Built with ❤️ by LinkersDev**
