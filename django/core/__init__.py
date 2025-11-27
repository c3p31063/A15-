# django/core/__init__.py
# -*- coding: utf-8 -*-
"""
core パッケージ初期化（完全版）

Django にアプリ設定 CoreConfig を自動認識させるためのエントリ。

- settings.INSTALLED_APPS に "core" と書くだけで、
  CoreConfig（core.apps.CoreConfig）が使われるようにする。
"""

default_app_config = "core.apps.CoreConfig"
