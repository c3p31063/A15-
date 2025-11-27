# django/core/urls.py
# -*- coding: utf-8 -*-
"""
core.urls（完全版）

Django 側の URL ルーティング。

- すべて core.views の関数ビューに紐づける
- app_name を "core" にして、テンプレートから
    {% url 'core:login' %}
    {% url 'core:dashboard' %}
    {% url 'core:image_check' %}
  のように参照できるようにする

想定パス:
    /login/            -> ログイン
    /logout/           -> ログアウト
    /signup/           -> 新規ユーザー登録
    /                  -> ダッシュボード
    /image-check/      -> 画像チェック画面
    /text-check/       -> テキストチェック画面
    /my-logs/          -> 自分のチェック履歴一覧
    /jobs/<job_id>/    -> ジョブ詳細
    /admin/dashboard/  -> 管理者向けダッシュボード
"""

from __future__ import annotations

from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    # 認証系
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup_view, name="signup"),
    path("admin/login/", views.admin_login_view, name="admin_login"),

    # ダッシュボード / 履歴
    path("", views.dashboard_view, name="dashboard"),
    path("my-logs/", views.my_logs_view, name="my_logs"),
    path("jobs/<str:job_id>/", views.job_detail_view, name="job_detail"),

    # チェック画面
    path("image-check/", views.image_check_view, name="image_check"),
    path("text-check/", views.text_check_view, name="text_check"),

    # 管理者向け
    path("admin/dashboard/", views.admin_dashboard_view, name="admin_dashboard"),
]
