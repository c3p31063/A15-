# django/core/services/__init__.py
# -*- coding: utf-8 -*-
"""
core.services パッケージ初期化（完全版）

- Firestore 連携など、「外部サービスとのやりとり」をまとめる名前空間。
- 現状は firestore_repo だけだが、将来的に:
    - fastapi_proxy.py
    - audit_logger.py
    - mailer.py
  などを追加してもここにぶら下げられる。

views.py からは:

    from .services import firestore_repo

のようにインポートして利用する。
"""

from __future__ import annotations

# 必要ならここでサブモジュールを re-export してもよいが、
# 現状は views から `from .services import firestore_repo` と
# 直接モジュールをインポートしているので、明示的な import は不要。
#
# 例:
# from . import firestore_repo  # noqa: F401

__all__ = [
    "firestore_repo",
]
