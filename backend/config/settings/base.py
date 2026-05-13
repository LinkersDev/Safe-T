"""
Base settings shared across all environments.
"""
from pathlib import Path
from datetime import timedelta
import environ

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/

env = environ.Env(
    DEBUG=(bool, False),
    ENABLE_DEV_OTP=(bool, False),
    ACCESS_TOKEN_LIFETIME_MINUTES=(int, 60),
    REFRESH_TOKEN_LIFETIME_DAYS=(int, 30),
    LEDGER_FEE_POOL_ACCOUNT_NUMBER=(str, ""),
    # Default matches demo seed; override in production via env.
    LEDGER_CASH_ACCOUNT_NUMBER=(str, "9999000000000002"),
    # OTP provider (dev | whatsapp)
    OTP_PROVIDER=(str, "dev"),
    # TNEENWH WhatsApp API credentials
    TNEENWH_BASE_URL=(str, "https://api.tneenwh.com"),
    TNEENWH_API_KEY=(str, ""),
    TNEENWH_SESSION_ID=(str, ""),
    TNEENWH_CHANNEL_SECRET=(str, ""),
    TNEENWH_EMAIL=(str, ""),
    TNEENWH_PASSWORD=(str, ""),
    TNEENWH_HTTP_USER_AGENT=(str, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
)
environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ENABLE_DEV_OTP = env("ENABLE_DEV_OTP")
OTP_PROVIDER = env("OTP_PROVIDER")
TNEENWH_BASE_URL = env("TNEENWH_BASE_URL").rstrip("/")
TNEENWH_API_KEY = env("TNEENWH_API_KEY")
TNEENWH_SESSION_ID = env("TNEENWH_SESSION_ID")
TNEENWH_CHANNEL_SECRET = env("TNEENWH_CHANNEL_SECRET")
TNEENWH_EMAIL = env("TNEENWH_EMAIL")
TNEENWH_PASSWORD = env("TNEENWH_PASSWORD")
TNEENWH_HTTP_USER_AGENT = env("TNEENWH_HTTP_USER_AGENT")
ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1", "192.168.13.105"]

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
]

LOCAL_APPS = [
    "apps.users",
    "apps.security",
    "apps.kyc",
    "apps.accounts",
    "apps.ledger",
    "apps.payments",
    "apps.support",
    "apps.risk",
    "apps.reporting",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database — MySQL only, strict mode enforced
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="127.0.0.1"),
        "PORT": env("DB_PORT", default="3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO'",
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Media files (user-uploaded content — KYC documents, etc.)
# ---------------------------------------------------------------------------
MEDIA_URL  = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Custom user model
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "users.User"

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Use argon2 as the default password hasher
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static
# ---------------------------------------------------------------------------
STATIC_URL = "static/"

# ---------------------------------------------------------------------------
# Cache — LocMemCache in dev; override to Redis in prod
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    # Throttle rates — keys match scope names in throttle classes
    # Format: 'N/Xs' where X is seconds (custom), or standard 's/m/h/d'
    "DEFAULT_THROTTLE_RATES": {
        "otp_send": "3/600s",    # 3 per 10 minutes per IP
        "login": "5/300s",       # 5 per 5 minutes per IP
        "transfer": "10/60s",    # 10 per minute per user  (Phase 5)
        "qr_pay": "10/60s",      # 10 per minute per user  (Phase 5)
    },
}

# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------
# Account number that receives all transaction fees.
# Leave empty to disable fee collection (e.g. development / staging).
LEDGER_FEE_POOL_ACCOUNT_NUMBER = env("LEDGER_FEE_POOL_ACCOUNT_NUMBER")

# Account number representing the branch cash/vault counterparty for teller
# deposits and withdrawals. Must exist as an Account in the database.
LEDGER_CASH_ACCOUNT_NUMBER = env("LEDGER_CASH_ACCOUNT_NUMBER")

# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# CORS — allow the Vite dev server and any local port during development
# ---------------------------------------------------------------------------
SKIP_OTP_IN_DEV = env.bool("SKIP_OTP_IN_DEV", default=False)

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.13.105:3000",
    "capacitor://localhost",
    "ionic://localhost",
    "http://localhost",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-device-id",
    "x-device-name",
]

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env("ACCESS_TOKEN_LIFETIME_MINUTES")),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("REFRESH_TOKEN_LIFETIME_DAYS")),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}
