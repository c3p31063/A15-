# django/config/settings.py
# -*- coding: utf-8 -*-
"""
Django settings for a15_full_clip_hash_webapp（完全版）

- 日本語 / 日本時間向け設定
- SQLite をデフォルトDBとして利用
- core アプリとテンプレート (core/templates/core/*.html) を利用
- FastAPI との連携URLを環境変数から取得

環境変数（.env など）で優先的に読む値:

    DJANGO_SECRET_KEY
    DJANGO_DEBUG
    DJANGO_ALLOWED_HOSTS
    DJANGO_CSRF_TRUSTED_ORIGINS
    FASTAPI_BASE_URL / FASTAPI_URL

"""

from __future__ import annotations

import os
from pathlib import Path


# ---------------------------------------------------------------------------
# ベースパス
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 環境変数ヘルパ
# ---------------------------------------------------------------------------

def get_env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name)
    if value is None:
        return default or ""
    return value


def get_env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    v = v.strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return default


# ---------------------------------------------------------------------------
# 基本設定
# ---------------------------------------------------------------------------

SECRET_KEY = get_env("DJANGO_SECRET_KEY", "!!!CHANGE_ME_IN_PRODUCTION!!!")

DEBUG = get_env_bool("DJANGO_DEBUG", True)

# 例: "127.0.0.1,localhost"
_allowed_hosts_env = get_env("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(",") if h.strip()]

# CSRF Trusted Origins (例: "http://127.0.0.1:8000,http://localhost:8000")
_csrf_origins_env = get_env(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "http://127.0.0.1:8000,http://localhost:8000",
)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins_env.split(",") if o.strip()]


# ---------------------------------------------------------------------------
# アプリケーション
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # コアアプリ
    "core",
]

MIDDLEWARE = [
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
        # core/templates を直指定 + 各アプリの templates (APP_DIRS=True)
        "DIRS": [
            BASE_DIR / "core" / "templates",
        ],
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


# ---------------------------------------------------------------------------
# データベース
# ---------------------------------------------------------------------------

# 開発時は SQLite、必要に応じて本番では別DBに差し替える
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ---------------------------------------------------------------------------
# 認証 / パスワード
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTH_USER_MODEL = "auth.User"  # デフォルトのまま


# ログインURLなど
LOGIN_URL = "core:login"
LOGIN_REDIRECT_URL = "core:dashboard"
LOGOUT_REDIRECT_URL = "core:login"


# ---------------------------------------------------------------------------
# 国際化
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "ja"

TIME_ZONE = "Asia/Tokyo"

USE_I18N = True
USE_L10N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# 静的ファイル / メディア
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ---------------------------------------------------------------------------
# メッセージフレームワーク
# ---------------------------------------------------------------------------

from django.contrib.messages import constants as messages  # noqa: E402

MESSAGE_TAGS = {
    messages.DEBUG: "debug",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "danger",
}


# ---------------------------------------------------------------------------
# FastAPI 連携設定
# ---------------------------------------------------------------------------

# FastAPI 側のベースURL
FASTAPI_BASE_URL = (
    get_env("FASTAPI_BASE_URL")
    or get_env("FASTAPI_URL")
    or "http://127.0.0.1:8001"
)


# ---------------------------------------------------------------------------
# ロギング（必要最低限）
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "[{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "core": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}
