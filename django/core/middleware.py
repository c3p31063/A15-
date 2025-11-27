# django/core/middleware.py
# -*- coding: utf-8 -*-
"""
core.middleware（完全版）

ログイン必須ミドルウェア。

- ログインしていないユーザーが保護されたURLにアクセスした場合、
  LOGIN_URL へリダイレクトする。
- ログイン不要のパス（ログイン／ログアウト／サインアップ／パスワード関連）や
  static / media / admin などは除外する。

settings.MIDDLEWARE に追加する場合の例:

    MIDDLEWARE = [
        ...
        "core.middleware.LoginRequiredMiddleware",
    ]
"""

from __future__ import annotations

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch


# ログイン不要とする固定パス
EXEMPT_URLS = {
    "/accounts/login/",
    "/accounts/logout/",
    "/accounts/password_change/",
    "/accounts/password_change/done/",
    "/accounts/password_reset/",
    "/accounts/password_reset/done/",
    "/accounts/reset/",
    "/accounts/reset/done/",
    "/accounts/signup/",  # サインアップページ
    "/admin/login/",
    "/login/",
    "/signup/",
}

# 先頭がこれらで始まるパスは常に除外（static, media, adminなど）
EXEMPT_PREFIXES = (
    getattr(settings, "STATIC_URL", "/static/"),
    getattr(settings, "MEDIA_URL", "/media/"),
    "/admin/",
)


class LoginRequiredMiddleware:
    """
    認証必須ミドルウェア。

    - 認証済みユーザー: そのまま通す
    - 未認証ユーザー:
        - EXEMPT_URLS に含まれるパス
        - EXEMPT_PREFIXES で始まるパス
      のいずれにも該当しない場合は LOGIN_URL にリダイレクトする。
      リダイレクト時には ?next=<元のパス> を付与する。
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # settings.LOGIN_URL は '/login/' or 'core:login' どちらも想定
        self.login_url_setting = settings.LOGIN_URL

    def _resolve_login_url(self) -> str:
        """
        LOGIN_URL が名前（例: 'core:login'）の場合は reverse でパスに変換する。
        すでに '/login/' のようなパスならそのまま返す。
        """
        login_url = self.login_url_setting
        if isinstance(login_url, str) and not login_url.startswith("/"):
            try:
                login_url = reverse(login_url)
            except NoReverseMatch:
                # 解決できなければそのまま使う（設定ミスだがアプリ全体が死なないように）
                pass
        return login_url

    def __call__(self, request):
        path = request.path

        # 認証済み or 除外URL or 除外プレフィックスの場合はそのまま
        if (
            request.user.is_authenticated
            or path in EXEMPT_URLS
            or path.startswith(EXEMPT_PREFIXES)
        ):
            return self.get_response(request)

        login_url = self._resolve_login_url()
        return redirect(f"{login_url}?next={path}")
