# -*- coding: utf-8 -*-
"""
Firestore リポジトリ（完全版）
- コレクションは FIRESTORE_COLLECTION_PREFIX を先頭につける
- jobs / evidences / simimgs / vectors / audits
- 監査ログ: write_audit, load_audit_for_user (除外アクション対応)
- 結果読み出し: load_result(job_id) -> (evidences, simimgs)
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone as py_tz

from django.conf import settings
from google.cloud import firestore
from google.api_core.exceptions import FailedPrecondition

# --- 内部ヘルパ ---
def _db() -> firestore.Client:
    # GOOGLE_APPLICATION_CREDENTIALS は環境変数で設定済み想定
    return firestore.Client()

def _prefix() -> str:
    return getattr(settings, "FIRESTORE_COLLECTION_PREFIX", "a15")

def _col(name: str) -> firestore.CollectionReference:
    return _db().collection(f"{_prefix()}_{name}")

def _jobs_col(): return _col("jobs")
def _evidences_col(): return _col("evidences")
def _simimgs_col(): return _col("simimgs")
def _vectors_col(): return _col("vectors")
def _audits_col(): return _col("audits")

# --- ジョブ ---
def save_job_meta(job_id: str, user_id: int, data: Dict[str, Any]) -> None:
    base = {"job_id": job_id, "user_id": int(user_id), "updated_at": datetime.now(tz=py_tz.utc)}
    if "created_at" not in data:
        data["created_at"] = datetime.now(tz=py_tz.utc)
    _jobs_col().document(job_id).set({**base, **data}, merge=True)

def load_job(job_id: str) -> Dict[str, Any]:
    doc = _jobs_col().document(job_id).get()
    if not doc.exists:
        return {}
    d = doc.to_dict() or {}
    d["id"] = doc.id
    return d

# --- 類似画像/証拠/ベクタ・ハッシュ ---
def save_similar_images(job_id: str, sim: List[Dict[str, Any]]) -> None:
    # 既存削除
    db = _db()
    batch = db.batch()
    qs = _simimgs_col().where("job_id", "==", job_id).stream()
    for d in qs:
        batch.delete(d.reference)
    batch.commit()

    # 新規書き込み
    batch = db.batch()
    for i, it in enumerate(sim):
        doc_id = f"{job_id}__{i:04d}"
        row = {
            "job_id": job_id,
            "rank": it.get("rank", i + 1),
            "match_url": it.get("match_url") or it.get("url") or "",
            "thumbnail_url": it.get("thumbnail_url") or it.get("thumbnail") or "",
            "match_score": float(it.get("match_score", it.get("score", 0.0)) or 0.0),
        }
        batch.set(_simimgs_col().document(doc_id), row, merge=True)
    batch.commit()

def save_evidences(job_id: str, evs: List[Dict[str, Any]]) -> None:
    db = _db()
    batch = db.batch()
    qs = _evidences_col().where("job_id", "==", job_id).stream()
    for d in qs:
        batch.delete(d.reference)
    batch.commit()

    batch = db.batch()
    for i, it in enumerate(evs):
        doc_id = f"{job_id}__{i:04d}"
        row = {
            "job_id": job_id,
            "source": it.get("source", ""),
            "url": it.get("url", ""),
            "score_numeric": it.get("score_numeric"),
        }
        batch.set(_evidences_col().document(doc_id), row, merge=True)
    batch.commit()

def save_vectors_and_hashes(job_id: str, clip_vector: Optional[List[float]], hashes: Optional[Dict[str, Any]]) -> None:
    _vectors_col().document(job_id).set({
        "job_id": job_id,
        "clip_vector": clip_vector,
        "hashes": hashes,
        "updated_at": datetime.now(tz=py_tz.utc),
    }, merge=True)

def load_result(job_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """戻り値: (evidences, simimgs)"""
    evs: List[Dict[str, Any]] = []
    sims: List[Dict[str, Any]] = []

    # evidences
    try:
        q = _evidences_col().where("job_id", "==", job_id) \
            .order_by("url") \
            .limit(200)
        ev_docs = list(q.stream())
    except FailedPrecondition:
        ev_docs = list(_evidences_col().where("job_id", "==", job_id).limit(200).stream())
    for d in ev_docs:
        row = d.to_dict() or {}
        row["id"] = d.id
        evs.append(row)

    # simimgs
    try:
        q = _simimgs_col().where("job_id", "==", job_id) \
            .order_by("rank") \
            .limit(200)
        sm_docs = list(q.stream())
    except FailedPrecondition:
        sm_docs = list(_simimgs_col().where("job_id", "==", job_id).limit(200).stream())
        sm_docs.sort(key=lambda x: (x.to_dict() or {}).get("rank", 999999))
    for d in sm_docs:
        row = d.to_dict() or {}
        row["id"] = d.id
        sims.append(row)

    return evs, sims

# --- 監査ログ ---
def write_audit(user_id: int, action: str, job_id: Optional[str], ip: Optional[str], ua: Optional[str]) -> None:
    _audits_col().add({
        "user_id": int(user_id),
        "action": action,
        "job_id": job_id,
        "ip": ip or "",
        "ua": ua or "",
        "ts": datetime.now(tz=py_tz.utc),
    })

def load_audit_for_user(
    user_id: int,
    limit: int = 200,
    exclude_actions: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    col = _audits_col()
    try:
        q = col.where("user_id", "==", int(user_id)) \
               .order_by("ts", direction=firestore.Query.DESCENDING) \
               .limit(limit)
        docs = list(q.stream())
    except FailedPrecondition:
        docs = list(col.where("user_id", "==", int(user_id)).limit(limit).stream())
        def _ts(d):
            v = (d.to_dict() or {}).get("ts")
            return v or datetime.min.replace(tzinfo=py_tz.utc)
        docs.sort(key=_ts, reverse=True)

    out: List[Dict[str, Any]] = []
    for d in docs:
        row = d.to_dict() or {}
        row["id"] = d.id
        out.append(row)

    if exclude_actions:
        ex = set(exclude_actions)
        out = [r for r in out if r.get("action") not in ex]

    return out


def load_audits(
    *,
    start_ts: Optional[datetime] = None,
    end_ts: Optional[datetime] = None,
    user_ids: Optional[List[int]] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    管理者向け: 監査ログを取得して、簡易フィルタを行うユーティリティ。
    - start_ts/end_ts は timezone-aware datetime を想定
    - user_ids が指定されればそのユーザーに限定
    - limit は取得上限（Firestore 側で降順取得してから Python 側で絞る）
    """
    col = _audits_col()
    try:
        q = col.order_by("ts", direction=firestore.Query.DESCENDING).limit(limit)
        docs = list(q.stream())
    except FailedPrecondition:
        docs = list(col.limit(limit).stream())

    out: List[Dict[str, Any]] = []
    for d in docs:
        row = d.to_dict() or {}
        row["id"] = d.id
        out.append(row)

    # Python側でフィルタリング
    if user_ids is not None:
        s = set(int(u) for u in user_ids)
        out = [r for r in out if int(r.get("user_id", -1)) in s]

    if start_ts is not None:
        out = [r for r in out if (r.get("ts") is not None and r.get("ts") >= start_ts)]
    if end_ts is not None:
        out = [r for r in out if (r.get("ts") is not None and r.get("ts") <= end_ts)]

    return out
