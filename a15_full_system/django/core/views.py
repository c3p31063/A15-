import os
import json
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from .forms import UploadForm
from .models import CheckJob, CheckResult, Evidence, SimilarImage

# FastAPI のエンドポイント（docker-compose などで service 名 fastapi の 8001 を想定）
FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://fastapi:8001")


def upload_view(request):
    """
    アップロード（画像 or テキスト）を受け取り、FastAPI にチェックを依頼。
    返ってきた結果（リスク・エビデンス・類似画像など）を Django の DB に保存する。
    """
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            kind = form.cleaned_data["kind"]  # "image" or "text"
            prompt = form.cleaned_data.get("prompt") or ""

            # CheckJob を running で作成
            job = CheckJob.objects.create(
                user=request.user if request.user.is_authenticated else None,
                kind=kind,
                prompt_text=prompt,
                status="running",
            )

            try:
                # FastAPI に投げる
                if kind == "image":
                    f = request.FILES["image"]
                    files = {"file": (f.name, f.read())}
                    data = {"prompt": prompt}
                    r = requests.post(
                        f"{FASTAPI_URL}/check/image",
                        files=files,
                        data=data,
                        timeout=60,
                    )
                else:
                    # kind == "text"
                    data = {
                        "text": form.cleaned_data["text"],
                        "prompt": prompt,
                    }
                    r = requests.post(
                        f"{FASTAPI_URL}/check/text",
                        data=data,
                        timeout=60,
                    )

                # エラーなら例外
                r.raise_for_status()

                # レスポンス JSON
                payload = r.json()

                # リスク結果
                risk = payload.get("risk", {}) if isinstance(payload, dict) else {}
                total_score = float(risk.get("total", 0.0) or 0.0)
                level = risk.get("level", "unknown") or "unknown"
                threshold_version = risk.get("threshold_version", "unknown") or "unknown"

                # Django 側の判定ラベルへマッピング
                # （既存の3分類に合わせる）
                if level == "auto_block":
                    decision = "auto_block"
                elif level == "manual_review":
                    decision = "manual_review"
                else:
                    decision = "auto_pass"

                # CheckResult 保存
                CheckResult.objects.create(
                    job=job,
                    risk_score_total=total_score,
                    risk_level=level,
                    decision=decision,
                    threshold_version=threshold_version,
                )

                # Evidence 保存（URL があれば文献URL表示に活用される）
                # payload["evidence"] は例：
                # [{"source":"websearch","score":0.87,"detail":{"url":"https://...","title":"..."}}, ...]
                evidences = []
                try:
                    evidences = payload.get("evidence", [])
                    if evidences is None:
                        evidences = []
                except Exception:
                    evidences = []

                for ev in evidences:
                    # detail は dict 想定。文字列で返ってきたら辞書化を試みる
                    detail = ev.get("detail", {})
                    if isinstance(detail, str):
                        try:
                            detail = json.loads(detail)
                        except Exception:
                            detail = {"raw": ev.get("detail", "")}

                    Evidence.objects.create(
                        job=job,
                        source=ev.get("source", "") or "",
                        raw_json=detail,
                        score_numeric=float(ev.get("score", 0.0) or 0.0),
                        label="",  # ラベルは未使用なら空
                        url=(detail.get("url") if isinstance(detail, dict) else "") or "",
                    )

                # 類似画像の保存（FastAPI が "similar_images" を返す前提／なければスキップ）
                # 例:
                # payload["similar_images"] = [
                #   {"url":"https://...", "score":0.91, "thumbnail":"https://..."},
                #   ...
                # ]
                if kind == "image":
                    sim_list = payload.get("similar_images") if isinstance(payload, dict) else None
                    if isinstance(sim_list, list):
                        for idx, it in enumerate(sim_list, start=1):
                            match_url = it.get("url") or ""
                            match_score = float(it.get("score", 0.0) or 0.0)
                            thumbnail_url = it.get("thumbnail") or ""
                            SimilarImage.objects.create(
                                job=job,
                                rank=idx,
                                match_url=match_url,
                                match_score=match_score,
                                thumbnail_url=thumbnail_url,
                            )

                # ジョブ完了
                job.status = "done"
                job.finished_at = timezone.now()
                job.save()

                messages.success(
                    request,
                    f"判定が完了しました: {level} (score={total_score})",
                )
                return redirect("dashboard")

            except Exception as e:
                # 失敗時
                job.status = "rejected"
                job.save()
                messages.error(request, f"エラー: {e}")

    else:
        form = UploadForm()

    return render(request, "core/upload.html", {"form": form})


def dashboard_view(request):
    """
    直近 50 件のジョブ一覧（簡易ダッシュボード）
    """
    jobs = CheckJob.objects.select_related("result").order_by("-created_at")[:50]
    return render(request, "core/dashboard.html", {"jobs": jobs})


def job_detail_view(request, job_id: int):
    """
    ジョブ詳細。Evidence（文献URL 等）と SimilarImage（ピックした画像）を表示。
    """
    job = get_object_or_404(CheckJob.objects.select_related("result"), id=job_id)
    evidences = job.evidences.all().order_by("id")
    simimgs = job.similar_images.all().order_by("rank")
    return render(
        request,
        "core/job_detail.html",
        {
            "job": job,
            "evidences": evidences,
            "simimgs": simimgs,
        },
    )
