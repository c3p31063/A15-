# django/config/asgi.py
# -*- coding: utf-8 -*-
"""
ASGI config for a15_full_clip_hash_webapp（完全版）

- ASGI サーバー(daphne / uvicorn / hypercorn 等) から利用されるエントリポイント
- DJANGO_SETTINGS_MODULE を 'config.settings' に固定
- get_asgi_application() で application を公開

例: uvicorn で立ち上げる場合

    uvicorn config.asgi:application --host 127.0.0.1 --port 8000

"""

from __future__ import annotations

import os

from django.core.asgi import get_asgi_application

# 設定モジュールを指定（manage.py と合わせる）
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# ASGI アプリケーション本体
application = get_asgi_application()
