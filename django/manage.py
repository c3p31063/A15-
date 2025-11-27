# django/manage.py
# -*- coding: utf-8 -*-
"""
Django の管理スクリプト（完全版）

- 開発用サーバーの起動:      python manage.py runserver
- マイグレーション作成:      python manage.py makemigrations
- マイグレーション適用:      python manage.py migrate
- 管理ユーザー作成:          python manage.py createsuperuser

DJANGO_SETTINGS_MODULE は 'config.settings' に固定。
"""

from __future__ import annotations

import os
import sys


def main() -> None:
    """管理コマンドのエントリポイント。"""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # noqa: BLE001
        raise ImportError(
            "Django がインポートできませんでした。環境に Django がインストールされているか、"
            "仮想環境が有効になっているかを確認してください。"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
