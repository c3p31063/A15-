# django/config/urls.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    # ★ Django 標準管理サイトは使わない（URL競合させない）
    # path("admin/", admin.site.urls),

    # ★ A15 本体の UI はすべて core.urls に集約
    #   "/" から始まる全てのルートを core.urls に任せる
    path("", include("core.urls")),
]

# ★ 開発環境用 static / media 配信
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
