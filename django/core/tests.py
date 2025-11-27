# django/core/tests.py
# -*- coding: utf-8 -*-
"""
core.tests（完全版）

Django 側の最低限の疎通テスト。

ポイント:
- ログイン画面 / サインアップ画面 / ダッシュボードなどのURLが 200 / 302 を返すか確認
- ログインしていないとダッシュボードにアクセスできないことを確認
- CheckJob の一覧画面（my_logs）が動作することを確認

pytest でも manage.py test でも動作するように Django 標準の TestCase を利用。
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class AuthViewsTest(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.username = "testuser"
        self.password = "testpassword123"
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email="test@example.com",
        )

    def test_login_page_get(self) -> None:
        url = reverse("core:login")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ログイン", status_code=200)

    def test_signup_page_get(self) -> None:
        url = reverse("core:signup")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_requires_login(self) -> None:
        url = reverse("core:dashboard")
        resp = self.client.get(url)
        # ログインしていない場合はリダイレクト (302) が期待値
        self.assertIn(resp.status_code, (302, 301))

    def test_login_success_and_redirect_to_dashboard(self) -> None:
        url = reverse("core:login")
        resp = self.client.post(
            url,
            {"username": self.username, "password": self.password},
            follow=True,
        )
        # ログインに成功していれば dashboard に到達するはず
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["user"].is_authenticated)


class CheckViewsTest(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.username = "checkuser"
        self.password = "checkpassword123"
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            email="check@example.com",
        )

    def _login(self) -> None:
        self.client.login(username=self.username, password=self.password)

    def test_my_logs_requires_login(self) -> None:
        url = reverse("core:my_logs")
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (302, 301))

    def test_my_logs_after_login(self) -> None:
        self._login()
        url = reverse("core:my_logs")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_image_check_get(self) -> None:
        self._login()
        url = reverse("core:image_check")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_text_check_get(self) -> None:
        self._login()
        url = reverse("core:text_check")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
