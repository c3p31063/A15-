# django/config/wsgi.py
# -*- coding: utf-8 -*-
"""
WSGI config for a15_full_clip_hash_webapp（完全版）

- 伝統的な WSGI サーバー (gunicorn / mod_wsgi など) 用のエントリポイント
- DJANGO_SETTINGS_MODULE を 'config.settings' に固定
- get_wsgi_application() で application を公開

開発時に runserver するときも内部的にはこれが使われる。
"""

from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application

# 設定モジュールを指定（manage.py / asgi.py と合わせる）
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# WSGI アプリケーション本体
application = get_wsgi_application()
