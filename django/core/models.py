# django/core/models.py
# -*- coding: utf-8 -*-
"""
core.models（完全版）

Django 側で利用するドメインモデル定義。

- CheckJob
    - 画像チェック / テキストチェックの実行履歴
    - FastAPI から返ってきたレスポンス全体を JSON として保持
    - リスクスコア / リスクレベル を保存して Django 側の一覧画面などで利用

- LoginHistory
    - ユーザーのログイン履歴
    - 管理者ダッシュボードから誰がいつログインしたかを確認できる

要求と対応方針（テキスト仕様からの反映）:
- 「管理者ログインの場は db内のユーザー名、それに付随した全ユーザーの今までのログイン記録、
   チェック内容（画像でチェックしたかテキストでチェックしたか）、をみれるようにする」
  → LoginHistory でユーザーごとのログイン履歴を保存、
     CheckJob で kind ("image" / "text") を保存し、両者を user で紐付ける。
"""

from __future__ import annotations

from typing import Any, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class TimeStampedModel(models.Model):
    """
    created_at / updated_at を自動管理する抽象モデル。
    """

    created_at = models.DateTimeField("作成日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        abstract = True


class CheckJob(TimeStampedModel):
    """
    画像チェック / テキストチェックの実行ログ。

    - kind: "image" / "text" / "compat" などチェック種別
    - job_id: FastAPI 側で生成したジョブID（レスポンス payload に入れておくと紐付け可能）
    - raw_payload: FastAPI から返されたレスポンス JSON 全体
    """

    class Kind(models.TextChoices):
        IMAGE = "image", "画像チェック"
        TEXT = "text", "テキストチェック"
        COMPAT = "compat", "互換性チェック"

    class Status(models.TextChoices):
        PENDING = "pending", "キュー待ち"
        RUNNING = "running", "実行中"
        DONE = "done", "完了"
        FAILED = "failed", "失敗"

    class RiskLevel(models.TextChoices):
        LOW = "低", "低"
        MID = "中", "中"
        HIGH = "高", "高"

    # ビュー / テンプレート互換用のクラス属性エイリアス
    KIND_IMAGE = Kind.IMAGE
    KIND_TEXT = Kind.TEXT
    KIND_COMPAT = Kind.COMPAT

    STATUS_PENDING = Status.PENDING
    STATUS_RUNNING = Status.RUNNING
    STATUS_DONE = Status.DONE
    STATUS_FAILED = Status.FAILED

    RISK_LOW = RiskLevel.LOW
    RISK_MID = RiskLevel.MID
    RISK_HIGH = RiskLevel.HIGH

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="ユーザー",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="チェックを実行したユーザー（匿名実行の場合は空）。",
    )

    job_id = models.CharField(
        "ジョブID",
        max_length=64,
        unique=True,
        help_text="FastAPI 側で発行したジョブID等を保存しておくためのフィールド。",
    )

    kind = models.CharField(
        "チェック種別",
        max_length=16,
        choices=Kind.choices,
        default=Kind.IMAGE,
    )

    status = models.CharField(
        "ステータス",
        max_length=16,
        choices=Status.choices,
        default=Status.DONE,
    )

    # 入力情報
    input_filename = models.CharField(
        "入力ファイル名",
        max_length=255,
        blank=True,
        help_text="アップロードされた元ファイル名（画像チェック時のみ）。",
    )
    input_mime = models.CharField(
        "MIMEタイプ",
        max_length=100,
        blank=True,
    )
    input_prompt = models.TextField(
        "プロンプト / 補足説明",
        blank=True,
        help_text="画像生成AIのプロンプトやテキストの補足説明など任意情報。",
    )

    client_ip = models.GenericIPAddressField(
        "クライアントIP",
        null=True,
        blank=True,
    )
    user_agent = models.TextField(
        "ユーザーエージェント",
        blank=True,
    )

    # リスク評価
    risk_score = models.FloatField(
        "リスクスコア",
        null=True,
        blank=True,
        help_text="0〜100 の著作権リスクスコア。",
    )
    risk_level = models.CharField(
        "リスクレベル",
        max_length=4,
        choices=RiskLevel.choices,
        blank=True,
        help_text="低 / 中 / 高。",
    )

    # ソフト削除フラグ（将来的に履歴削除機能を実装するため）
    is_deleted = models.BooleanField(
        "削除フラグ",
        default=False,
    )

    # FastAPI レスポンスをそのまま保持する JSON フィールド
    raw_payload = models.JSONField(
        "レスポンスペイロード",
        default=dict,
        blank=True,
        help_text="FastAPI 側の /check/image /check/text から返された JSON 全体。",
    )

    class Meta:
        verbose_name = "チェックジョブ"
        verbose_name_plural = "チェックジョブ一覧"
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover - 表示用
        user_str = self.user.username if isinstance(self.user, User) else "anonymous"
        return f"{self.job_id} ({self.kind}) by {user_str}"

    @property
    def short_filename(self) -> str:
        """
        ファイル名を短く表示するユーティリティ（テンプレート用）。
        """
        if not self.input_filename:
            return ""
        # ディレクトリを含んでいた場合に basename のみ返す
        return self.input_filename.split("/")[-1].split("\\")[-1]


class LoginHistory(TimeStampedModel):
    """
    ログイン履歴。

    - 一般ユーザーのログインも、管理者ログインも共通でここに記録する想定。
    - 管理者ダッシュボードで「誰がいつどのIPからログインしたか」を確認するために利用。
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="ユーザー",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="ログインしたユーザー（存在しない / 削除済みの場合は None）。",
    )

    username = models.CharField(
        "ユーザー名スナップショット",
        max_length=150,
        blank=True,
        help_text="ログイン時点のユーザー名（後から変更されてもここには当時の値が残る）。",
    )

    email = models.EmailField(
        "メールアドレススナップショット",
        max_length=254,
        blank=True,
    )

    ip_address = models.GenericIPAddressField(
        "IPアドレス",
        null=True,
        blank=True,
    )

    user_agent = models.TextField(
        "ユーザーエージェント",
        blank=True,
    )

    is_admin_login = models.BooleanField(
        "管理者ログインか",
        default=False,
        help_text="管理者専用ログイン画面からのログインであれば True。",
    )

    class Meta:
        verbose_name = "ログイン履歴"
        verbose_name_plural = "ログイン履歴一覧"
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover - 表示用
        name = self.username or (self.user.username if isinstance(self.user, User) else "unknown")
        return f"{name} @ {self.created_at:%Y-%m-%d %H:%M:%S}"

    @classmethod
    def record_login(
        cls,
        *,
        user: Optional[User],
        ip_address: Optional[str] = None,
        user_agent: str = "",
        is_admin_login: bool = False,
    ) -> "LoginHistory":
        """
        ビューから呼び出してログイン履歴を1件保存するヘルパ。

        例:
            LoginHistory.record_login(
                user=request.user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                is_admin_login=is_admin,
            )
        """
        username = ""
        email = ""
        if user is not None:
            username = getattr(user, "username", "") or ""
            email = getattr(user, "email", "") or ""

        return cls.objects.create(
            user=user,
            username=username,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent or "",
            is_admin_login=is_admin_login,
        )
