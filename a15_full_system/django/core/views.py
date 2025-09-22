import os, requests
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .forms import UploadForm
from .models import CheckJob, CheckResult, Evidence
from django.shortcuts import get_object_or_404
from .models import CheckJob

FASTAPI_URL = os.environ.get("FASTAPI_URL","http://fastapi:8001")

def upload_view(request):
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            kind = form.cleaned_data["kind"]
            prompt = form.cleaned_data.get("prompt") or ""
            job = CheckJob.objects.create(
                user=request.user if request.user.is_authenticated else None,
                kind=kind, prompt_text=prompt, status="running"
            )
            try:
                if kind == "image":
                    f = request.FILES["image"]
                    files = {"file": (f.name, f.read())}
                    data = {"prompt": prompt}
                    r = requests.post(f"{FASTAPI_URL}/check/image", files=files, data=data, timeout=60)
                else:
                    data = {"text": form.cleaned_data["text"], "prompt": prompt}
                    r = requests.post(f"{FASTAPI_URL}/check/text", data=data, timeout=60)
                r.raise_for_status()
                payload = r.json()
                risk = payload.get("risk", {})
                CheckResult.objects.create(
                    job=job,
                    risk_score_total=risk.get("total",0.0),
                    risk_level=risk.get("level","unknown"),
                    decision=("auto_block" if risk.get("level")=="auto_block" else ("manual_review" if risk.get("level")=="manual_review" else "auto_pass")),
                    threshold_version=risk.get("threshold_version","unknown")
                )
                for ev in payload.get("evidence",[]):
                    Evidence.objects.create(
                        job=job,
                        source=ev.get("source",""),
                        raw_json=ev.get("detail",{}),
                        score_numeric=ev.get("score",0.0),
                        label="",
                        url=ev.get("detail",{}).get("url","")
                    )
                job.status = "done"
                job.finished_at = timezone.now()
                job.save()
                messages.success(request, f"判定が完了しました: {risk.get('level')} (score={risk.get('total')})")
                return redirect("dashboard")
            except Exception as e:
                job.status = "rejected"
                job.save()
                messages.error(request, f"エラー: {e}")
    else:
        form = UploadForm()
    return render(request, "core/upload.html", {"form": form})

def dashboard_view(request):
    jobs = CheckJob.objects.select_related("result").order_by("-created_at")[:50]
    return render(request, "core/dashboard.html", {"jobs": jobs})
    
def job_detail_view(request, job_id: int):
    job = get_object_or_404(CheckJob.objects.select_related("result"), id=job_id)
    evidences = job.evidences.all().order_by("id")
    return render(request, "core/job_detail.html", {"job": job, "evidences": evidences})
