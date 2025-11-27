# django/core/admin.py
# -*- coding: utf-8 -*-
"""
core.admin（完全版）

- CheckJob / LoginHistory を Django 管理サイトから閲覧・検索できるように登録する。
- リスクスコアや種別ごとにフィルタリングできるように設定。
"""

from __future__ import annotations

from django.contrib import admin

from .models import CheckJob, LoginHistory


@admin.register(CheckJob)
class CheckJobAdmin(admin.ModelAdmin):
    list_display = (
        "job_id",
        "user",
        "kind",
        "status",
        "risk_score",
        "risk_level",
        "input_filename",
        "created_at",
    )
    list_filter = (
        "kind",
        "status",
        "risk_level",
        "created_at",
    )
    search_fields = (
        "job_id",
        "user__username",
        "user__email",
        "input_filename",
        "input_prompt",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "user",
        "job_id",
    )
    ordering = ("-created_at",)

    fieldsets = (
        (
            "基本情報",
            {
                "fields": (
                    "user",
                    "job_id",
                    "kind",
                    "status",
                    "is_deleted",
                )
            },
        ),
        (
            "入力情報",
            {
                "fields": (
                    "input_filename",
                    "input_mime",
                    "input_prompt",
                    "client_ip",
                    "user_agent",
                )
            },
        ),
        (
            "リスク評価",
            {
                "fields": (
                    "risk_score",
                    "risk_level",
                )
            },
        ),
        (
            "メタデータ",
            {
                "classes": ("collapse",),
                "fields": (
                    "raw_payload",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "username",
        "email",
        "ip_address",
    )
    list_filter = (
        "created_at",
    )
    search_fields = (
        "username",
        "email",
        "user__username",
        "user__email",
        "ip_address",
    )
    ordering = ("-created_at",)
