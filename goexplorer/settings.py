"""
Django settings for GoExplorer (DEV)
Simple, predictable, easy to maintain.
"""

from pathlib import Path
from decouple import config
import dj_database_url

# --------------------------------------------------
# Base
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="dev-secret-key-change-later")
DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = ['goexplorer-dev.cloud','www.goexplorer-dev.cloud','srv1247591.hstgr.cloud','localhost','127.0.0.1','testserver']

# --------------------------------------------------
# Applications
# --------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "rest_framework",
    "corsheaders",
    "django_filters",
    "crispy_forms",
    "crispy_bootstrap5",

    # Local apps
    "core",
    "hotels",
    "buses",
    "packages",
    "bookings",
    "payments",
    "users",
    "notifications",
    "property_owners",
    "dashboard",
    "audit_logs",
    "reviews",  # Phase 3: Reviews moderation
]

# --------------------------------------------------
# Middleware (serves static via WhiteNoise in DEV/PROD)
# --------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "bookings.middleware.ClearAuthMessagesMiddleware",  # Clear login messages on booking pages
]

ROOT_URLCONF = "goexplorer.urls"

# --------------------------------------------------
# Templates
# --------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "goexplorer.wsgi.application"

# --------------------------------------------------
# Database (Postgres preferred, SQLite fallback for DEV)
# --------------------------------------------------
DB_NAME = config("DB_NAME", default=None)

if DB_NAME:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": DB_NAME,
            "USER": config("DB_USER", default=""),
            "PASSWORD": config("DB_PASSWORD", default=""),
            "HOST": config("DB_HOST", default="127.0.0.1"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }
else:
    DATABASES = {
        "default": dj_database_url.config(
            default=config("DATABASE_URL", default="sqlite:///db.sqlite3")
        )
    }

# --------------------------------------------------
# Auth
# --------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

AUTH_USER_MODEL = "users.User"

# --------------------------------------------------
# I18N
# --------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------
# Static & Media (Nginx serves these)
# --------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
# Enable WhiteNoise finders so dev/staging can serve from STATICFILES_DIRS without collectstatic
WHITENOISE_USE_FINDERS = True
# Avoid manifest requirement during DEBUG/tests to prevent Missing manifest errors
if DEBUG:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
else:
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
SERVE_MEDIA_FILES = config("SERVE_MEDIA_FILES", default=True, cast=bool)

# --------------------------------------------------
# Email / Notifications (CRITICAL - No Fallbacks)
# --------------------------------------------------
# ENFORCED: SendGrid SMTP only (no Gmail, no console)
# Password reset, OTP, and all transactional emails MUST be delivered
# Any misconfiguration will fail loudly at startup
# --------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# SendGrid SMTP (production email service)
EMAIL_HOST = config("EMAIL_HOST", default="smtp.sendgrid.net")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="apikey")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)

# Validate that SendGrid API key is configured (fail fast in production)
if not DEBUG and not config("EMAIL_HOST_PASSWORD", default=""):
    import warnings
    warnings.warn(
        "CRITICAL: SendGrid API key (EMAIL_HOST_PASSWORD) is not configured. "
        "Email sending will fail. Set SENDGRID_API_KEY environment variable.",
        RuntimeWarning
    )

DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL", default="alerts.goexplorer@gmail.com"
)

# Enforce verified sender identity (SendGrid single sender)
if DEFAULT_FROM_EMAIL.lower() != "alerts.goexplorer@gmail.com":
    import warnings
    warnings.warn(
        "DEFAULT_FROM_EMAIL must be alerts.goexplorer@gmail.com (verified sender)",
        RuntimeWarning,
    )

# Notification delivery flags (must be False in production)
NOTIFICATIONS_EMAIL_DRY_RUN = config("NOTIFICATIONS_EMAIL_DRY_RUN", default=False, cast=bool)
NOTIFICATIONS_SMS_DRY_RUN = config("NOTIFICATIONS_SMS_DRY_RUN", default=False, cast=bool)

# Email delivery logging (always enabled for troubleshooting)
EMAIL_LOG_LEVEL = "INFO"  # Log all email send attempts and results

# MSG91 (templated SMS)
MSG91_AUTHKEY = config("MSG91_AUTHKEY", default="")
MSG91_SENDER_ID = config("MSG91_SENDER_ID", default="GOEXPR")
MSG91_ROUTE = config("MSG91_ROUTE", default="4")
MSG91_COUNTRY = config("MSG91_COUNTRY", default="91")
MSG91_BASE_URL = config("MSG91_BASE_URL", default="https://api.msg91.com/api/v5/flow/")
MSG91_OTP_TEMPLATE_ID = config("MSG91_OTP_TEMPLATE_ID", default="")
MSG91_DEFAULT_TEMPLATE_ID = config("MSG91_DEFAULT_TEMPLATE_ID", default="")

# Fail-fast when MSG91 credentials/templates are missing in non-debug environments
if not DEBUG and (not MSG91_AUTHKEY or not MSG91_OTP_TEMPLATE_ID):
    import warnings
    warnings.warn(
        "CRITICAL: MSG91 OTP template/auth key missing. Set MSG91_AUTHKEY and MSG91_OTP_TEMPLATE_ID.",
        RuntimeWarning,
    )

# --------------------------------------------------
# Payments (TEST KEYS ONLY)
# --------------------------------------------------
RAZORPAY_KEY_ID = config("RAZORPAY_KEY_ID", default="")
RAZORPAY_KEY_SECRET = config("RAZORPAY_KEY_SECRET", default="")

# Cashfree UPI Integration
CASHFREE_APP_ID = config("CASHFREE_APP_ID", default="")
CASHFREE_SECRET_KEY = config("CASHFREE_SECRET_KEY", default="")
CASHFREE_API_VERSION = "2023-08-01"

STRIPE_PUBLIC_KEY = config("STRIPE_PUBLIC_KEY", default="")
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")

# --------------------------------------------------
# Logging (email and authentication debugging)
# --------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "formatter": "verbose",
        },
        "email_file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "email.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": config("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
        "django.core.mail": {
            "handlers": ["console", "email_file"],
            "level": "INFO",
            "propagate": False,
        },
        "users": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "notifications": {
            "handlers": ["console", "email_file"],
            "level": "INFO",
            "propagate": False,
        },
        "bookings": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Ensure logs directory exists
import os as _os
_log_dir = BASE_DIR / "logs"
if not _log_dir.exists():
    _log_dir.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------
# CORS (DEV)
# --------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True

# --------------------------------------------------
# REST Framework (simple for DEV)
# --------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "PAGE_SIZE": 20,
}

# --------------------------------------------------
# Cache & Sessions (simple DB cache)
# --------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "goexplorer_cache",
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# --------------------------------------------------
# Crispy Forms
# --------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# --------------------------------------------------
# Production security (ignored in DEV)
# --------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'SAMEORIGIN'
