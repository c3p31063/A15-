# django/config/__init__.py
# -*- coding: utf-8 -*-
"""
config パッケージ初期化モジュール（完全版）

このファイルは Django プロジェクト設定モジュールの名前空間。

- settings.py / urls.py / asgi.py / wsgi.py をまとめる役割だけで、
  特別な処理は行っていない。
- 'DJANGO_SETTINGS_MODULE' として 'config.settings' を指定することで、
  プロジェクト全体の設定を参照できる。

例:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
"""

__all__ = [
    "settings",
    "urls",
    "asgi",
    "wsgi",
]
