# django/core/apps.py
# -*- coding: utf-8 -*-
"""
core.apps（完全版）

Django に 'core' アプリを認識させるための AppConfig 定義。

settings.INSTALLED_APPS には文字列 "core" を入れておけば、
自動的にこの CoreConfig が使われる（Django 3.2+）。
"""

from __future__ import annotations

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "著作権チェックコア"
