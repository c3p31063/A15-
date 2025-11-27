# django/core/views.py
# -*- coding: utf-8 -*-
"""
core.views（完全版）

役割:
- Django 側の画面遷移・フォーム受付・FastAPI 呼び出し・CheckJob 保存をまとめる。
- HTML テンプレート:
    - core/login.html
    - core/signup.html
    - core/dashboard.html
    - core/image_check.html
    - core/text_check.html
    - core/my_logs.html
    - core/job_detail.html
    - core/admin_dashboard.html
  などと連携する想定。

ポイント:
- 認証まわりは Django 標準の User / AuthenticationForm / UserCreationForm を利用
- 画像・テキストチェックは FastAPI へ httpx でリクエストを送り、
  戻ってきた JSON を CheckJob に保存
- Firestore 連携（core.services.firestore_repo）があれば job_detail で追加情報を取得するが、
  無くてもエラーにならないように try/except でガードする
"""

from __future__ import annotations

from uuid import uuid4
from typing import Any, Dict, Optional

import json
import httpx
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import CheckJob


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------


def _get_fastapi_base_url() -> str:
    """
    FastAPI 側のベースURLを取得するヘルパー。

    優先順位:
        1. settings.FASTAPI_BASE_URL
        2. settings.FASTAPI_URL
        3. デフォルト "http://127.0.0.1:8001"
    """
    return (
        getattr(settings, "FASTAPI_BASE_URL", None)
        or getattr(settings, "FASTAPI_URL", None)
        or "http://127.0.0.1:8001"
    ).rstrip("/")


def _build_job_id_from_payload(payload: Dict[str, Any]) -> str:
    """
    FastAPI 側のレスポンスから job_id を抽出するヘルパー。

    - payload["job_id"]
    - payload["id"]
    - payload["meta"]["job_id"]
    の順で探し、見つからなければ uuid4() を振る。
    """
    job_id = (
        payload.get("job_id")
        or payload.get("id")
        or (payload.get("meta") or {}).get("job_id")
    )
    if not job_id:
        job_id = uuid4().hex
    return str(job_id)


def _get_client_ip(request: HttpRequest) -> Optional[str]:
    """
    X-Forwarded-For を考慮したクライアントIP取得。
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        # "client, proxy1, proxy2" のような形式を想定
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _is_staff(user) -> bool:
    return bool(user and (user.is_staff or user.is_superuser))


# ---------------------------------------------------------------------------
# 認証系
# ---------------------------------------------------------------------------


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    """
    ログイン画面。

    - GET: ログインフォーム表示
    - POST: 認証 → 成功したら dashboard へリダイレクト
    """
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "ログインしました。")
            return redirect("core:dashboard")
        else:
            messages.error(request, "ユーザー名またはパスワードが正しくありません。")

    return render(request, "core/login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def signup_view(request: HttpRequest) -> HttpResponse:
    """
    新規ユーザー登録画面。
    """
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    form = UserCreationForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            # 自動ログインしてダッシュボードへ
            login(request, user)
            messages.success(request, "ユーザー登録が完了しました。")
            return redirect("core:dashboard")
        else:
            messages.error(request, "入力内容にエラーがあります。")

    return render(request, "core/signup.html", {"form": form})


@login_required
def logout_view(request: HttpRequest) -> HttpResponse:
    """
    ログアウト処理。
    """
    logout(request)
    messages.info(request, "ログアウトしました。")
    return redirect("core:login")


# ---------------------------------------------------------------------------
# ダッシュボード / ログ一覧
# ---------------------------------------------------------------------------


@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    一般ユーザー向けダッシュボード。

    - 自分の最新ジョブ一覧（10件）
    - 種別ごとの件数
    - 平均リスクスコアなどを簡易表示
    """
    qs = CheckJob.objects.filter(user=request.user, is_deleted=False)

    total_count = qs.count()
    image_count = qs.filter(kind=CheckJob.Kind.IMAGE).count()
    text_count = qs.filter(kind=CheckJob.Kind.TEXT).count()
    compat_count = qs.filter(kind=CheckJob.Kind.COMPAT).count()

    # 平均スコア
    avg_score = 0.0
    if total_count > 0:
        from django.db.models import Avg

        avg_score = qs.aggregate(avg=Avg("risk_score"))["avg"] or 0.0

    recent_jobs = qs.order_by("-created_at")[:10]

    context = {
        "total_count": total_count,
        "image_count": image_count,
        "text_count": text_count,
        "compat_count": compat_count,
        "avg_score": float(avg_score),
        "recent_jobs": recent_jobs,
    }
    return render(request, "core/dashboard.html", context)


@login_required
def my_logs_view(request: HttpRequest) -> HttpResponse:
    """
    自分のチェック履歴一覧画面。
    """
    jobs = (
        CheckJob.objects.filter(user=request.user, is_deleted=False)
        .order_by("-created_at")
    )
    return render(request, "core/my_logs.html", {"jobs": jobs})


@login_required
def job_detail_view(request: HttpRequest, job_id: str) -> HttpResponse:
    """
    単一ジョブの詳細画面。

    - SQL 側の CheckJob
    - （あれば）Firestore 側の詳細
    をまとめてテンプレートに渡す。
    """
    if _is_staff(request.user):
        job = get_object_or_404(CheckJob, job_id=job_id)
    else:
        job = get_object_or_404(CheckJob, job_id=job_id, user=request.user)

    firestore_detail: Optional[Dict[str, Any]] = None

    # Firestore 連携はあれば使う、無ければ無視
    try:
        from .services import firestore_repo  # type: ignore[import-not-found]

        if hasattr(firestore_repo, "get_job_detail"):
            firestore_detail = firestore_repo.get_job_detail(job.job_id)  # type: ignore[assignment]
    except Exception:
        firestore_detail = None

    context = {
        "job": job,
        "payload": job.raw_payload or {},
        "firestore_detail": firestore_detail,
    }
    return render(request, "core/job_detail.html", context)


# ---------------------------------------------------------------------------
# 画像チェック
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(["GET", "POST"])
def image_check_view(request: HttpRequest) -> HttpResponse:
    """
    画像チェック画面。

    - GET: フォーム表示
    - POST:
        1. アップロードされた画像ファイルと任意プロンプトを取得
        2. FastAPI /check/image エンドポイントを呼び出し
        3. 戻り値を CheckJob に保存
        4. 結果を同じテンプレートに表示
    """
    result_payload: Optional[Dict[str, Any]] = None
    created_job: Optional[CheckJob] = None

    if request.method == "POST":
        uploaded = request.FILES.get("image")
        prompt = request.POST.get("prompt") or ""

        if not uploaded:
            messages.error(request, "画像ファイルを選択してください。")
        else:
            try:
                base_url = _get_fastapi_base_url()
                url = f"{base_url}/check/image"

                # ファイルをバイト列にして送る
                file_bytes = uploaded.read()
                files = {
                    "file": (
                        uploaded.name,
                        file_bytes,
                        uploaded.content_type or "application/octet-stream",
                    )
                }
                data = {
                    "prompt": prompt,
                    # FastAPI 側で user_id を使うならここで渡す
                    "user_id": str(request.user.pk),
                }

                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(url, files=files, data=data)
                    resp.raise_for_status()
                    result_payload = resp.json()

                # CheckJob 保存
                job_id = _build_job_id_from_payload(result_payload)
                created_job = CheckJob.objects.create(
                    user=request.user,
                    job_id=job_id,
                    kind=CheckJob.Kind.IMAGE,
                    status=CheckJob.Status.DONE,
                    input_filename=uploaded.name,
                    input_mime=uploaded.content_type or "",
                    input_prompt=prompt,
                    client_ip=_get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    risk_score=float(result_payload.get("risk_score") or 0.0),
                    risk_level=str(result_payload.get("risk_level") or ""),
                    raw_payload=result_payload,
                )

                messages.success(request, "画像チェックが完了しました。")

            except httpx.HTTPError as exc:
                messages.error(request, f"FastAPI への画像チェックリクエストに失敗しました: {exc}")
            except Exception as exc:  # noqa: BLE001
                messages.error(request, f"画像チェック処理中にエラーが発生しました: {exc}")

    context = {
        "result": result_payload,
        "job": created_job,
    }
    return render(request, "core/image_check.html", context)


# ---------------------------------------------------------------------------
# テキストチェック
# ---------------------------------------------------------------------------


@login_required
@require_http_methods(["GET", "POST"])
def text_check_view(request: HttpRequest) -> HttpResponse:
    """
    テキストチェック画面。

    - GET: フォーム表示
    - POST:
        1. テキストを取得
        2. FastAPI /check/text エンドポイントを呼び出し（Form で送る点に注意）
        3. 戻り値を CheckJob に保存
        4. 結果を同じテンプレートに表示
    """
    result_payload: Optional[Dict[str, Any]] = None
    created_job: Optional[CheckJob] = None
    input_text: str = ""
    memo: str = ""
    error_msg: Optional[str] = None

    if request.method == "POST":
        input_text = request.POST.get("input_text") or ""
        memo = request.POST.get("memo") or ""

        if not input_text.strip():
            error_msg = "チェック対象のテキストを入力してください。"
            messages.error(request, error_msg)
        else:
            try:
                base_url = _get_fastapi_base_url()
                url = f"{base_url}/check/text"

                # ★ FastAPI 側の定義:
                #   async def check_text(text: str = Form(...), user_id: Optional[str] = Form(None))
                # なので JSON ではなく form-encoded で送る
                data = {
                    "text": input_text,
                    "user_id": str(request.user.pk),
                }

                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(url, data=data)
                    resp.raise_for_status()
                    result_payload = resp.json()

                # CheckJob 保存
                job_id = _build_job_id_from_payload(result_payload)
                created_job = CheckJob.objects.create(
                    user=request.user,
                    job_id=job_id,
                    kind=CheckJob.Kind.TEXT,
                    status=CheckJob.Status.DONE,
                    input_filename="",  # テキストなのでファイル名なし
                    input_mime="text/plain",
                    input_prompt=input_text,
                    client_ip=_get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    risk_score=float(result_payload.get("risk_score") or 0.0),
                    risk_level=str(result_payload.get("risk_level") or ""),
                    raw_payload=result_payload,
                )

                messages.success(request, "テキストチェックが完了しました。")

            except httpx.HTTPError as exc:
                error_msg = f"FastAPI へのテキストチェックリクエストに失敗しました: {exc}"
                messages.error(request, error_msg)
            except Exception as exc:  # noqa: BLE001
                error_msg = f"テキストチェック処理中にエラーが発生しました: {exc}"
                messages.error(request, error_msg)

    # 類似文章リスト & RAW JSON はテンプレで参照しやすいように分解して渡す
    similar_texts = None
    raw_payload_json: Optional[str] = None
    if result_payload:
        similar_texts = (
            result_payload.get("plagiarism_matches")
            or result_payload.get("similar_texts")
            or result_payload.get("plagiarism_results")
        )
        try:
            raw_payload_json = json.dumps(result_payload, ensure_ascii=False, indent=2)
        except Exception:
            raw_payload_json = None

    context = {
        "input_text": input_text,
        "memo": memo,
        "result": result_payload,
        "job": created_job,
        "error": error_msg,
        "similar_texts": similar_texts,
        "raw_payload_json": raw_payload_json,
    }
    return render(request, "core/text_check.html", context)


# ---------------------------------------------------------------------------
# 管理者向けダッシュボード
# ---------------------------------------------------------------------------


@user_passes_test(_is_staff)
def admin_dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    管理者・職員向けのダッシュボード。

    - 全ユーザーの最新ジョブ一覧（ページングしたければ将来拡張）
    - 種別ごとの件数
    - 平均スコア
    """
    qs = CheckJob.objects.filter(is_deleted=False)

    total_count = qs.count()
    image_count = qs.filter(kind=CheckJob.Kind.IMAGE).count()
    text_count = qs.filter(kind=CheckJob.Kind.TEXT).count()
    compat_count = qs.filter(kind=CheckJob.Kind.COMPAT).count()

    avg_score = 0.0
    if total_count > 0:
        from django.db.models import Avg

        avg_score = qs.aggregate(avg=Avg("risk_score"))["avg"] or 0.0

    recent_jobs = qs.select_related("user").order_by("-created_at")[:50]

    context = {
        "total_count": total_count,
        "image_count": image_count,
        "text_count": text_count,
        "compat_count": compat_count,
        "avg_score": float(avg_score),
        "recent_jobs": recent_jobs,
    }
    return render(request, "core/admin_dashboard.html", context)


@require_http_methods(["GET", "POST"])
def admin_login_view(request: HttpRequest) -> HttpResponse:
    """
    管理者・職員向けログイン画面。
    - staff / superuser だけを通す
    """
    # すでに staff でログイン済みならダッシュボードへ
    if request.user.is_authenticated and _is_staff(request.user):
        return redirect("core:admin_dashboard")

    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            user = form.get_user()
            if not _is_staff(user):
                messages.error(request, "このアカウントには管理者権限がありません。")
            else:
                login(request, user)
                messages.success(request, "管理者としてログインしました。")
                return redirect("core:admin_dashboard")
        else:
            messages.error(request, "ユーザー名またはパスワードが正しくありません。")

    return render(request, "core/admin_login.html", {"form": form})
