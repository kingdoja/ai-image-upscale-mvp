from pathlib import Path
from io import BytesIO
from collections import Counter
import csv
import json
from io import StringIO
from typing import Iterable, List, Optional, Tuple
import zipfile

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import get_settings
from ..inference.base import ModelConfigurationError
from ..inference.diffusion import DiffusionUpscaleAdapter
from ..inference.optional_models import DisabledOptionalModelAdapter, ExternalUpscaleAdapter, OptionalModelAdapter
from ..inference.realesrgan import RealESRGANAdapter
from ..inference.stub import StubUpscaleAdapter
from ..models import Feedback, Job, Result, new_id
from ..quality import evaluate_image
from ..schemas import ALLOWED_ISSUES, FeedbackCreate
from ..semantic_controller import (
    CANDIDATE_DISPLAY_ORDER,
    DEFAULT_SELECTED_CANDIDATES,
    build_data_governance_summary,
    build_semantic_context,
    create_upscale_plan,
    understand_image,
)
from ..storage import create_thumbnail, result_path, save_upload, thumbnail_path


VALID_SCALES = {2, 4}
VALID_MODES = {"faithful", "realistic", "both"}
VALID_SCENES = {"product", "marketing", "ecommerce", "other"}
VALID_SELECTED_CANDIDATES = {"faithful", "swinir", "hat"}


def _validate_job_options(scale: int, mode: str, scene: str) -> None:
    if scale not in VALID_SCALES:
        raise HTTPException(status_code=422, detail="scale must be 2 or 4")
    if mode not in VALID_MODES:
        raise HTTPException(status_code=422, detail="mode must be faithful, realistic, or both")
    if scene not in VALID_SCENES:
        raise HTTPException(status_code=422, detail="scene must be product, marketing, ecommerce, or other")


def normalize_selected_candidates(selected_candidates: Optional[List[str]]) -> List[str]:
    if selected_candidates is None:
        return []
    candidates = selected_candidates or []
    normalized = [candidate.strip().lower() for candidate in candidates if candidate and candidate.strip()]
    if not normalized:
        return []
    invalid = sorted(set(normalized) - VALID_SELECTED_CANDIDATES)
    if invalid:
        raise HTTPException(status_code=422, detail=f"candidates contains unsupported values: {', '.join(invalid)}")
    unique = list(dict.fromkeys(normalized))
    return sorted(unique, key=lambda candidate_type: CANDIDATE_DISPLAY_ORDER.index(candidate_type))


def _path_exists(path_value: str) -> bool:
    return bool(path_value) and Path(path_value).exists()


def build_model_statuses() -> dict:
    settings = get_settings()
    models = []
    if settings.faithful_backend == "realesrgan":
        executable_ready = _path_exists(settings.realesrgan_executable)
        model_dir_ready = _path_exists(settings.realesrgan_model_path)
        model_file_ready = bool(settings.realesrgan_model_path) and (
            Path(settings.realesrgan_model_path) / f"{settings.realesrgan_model}.param"
        ).exists()
        ready = executable_ready and model_dir_ready and model_file_ready
        models.append(
            {
                "id": "faithful",
                "label": "Real-ESRGAN",
                "backend": settings.faithful_backend,
                "status": "ready" if ready else "missing_config",
                "configured": ready,
                "detail": "Real-ESRGAN x4plus is ready" if ready else "Real-ESRGAN executable or model files are missing",
            }
        )
    else:
        models.append(
            {
                "id": "faithful",
                "label": "Real-ESRGAN",
                "backend": settings.faithful_backend,
                "status": "demo",
                "configured": True,
                "detail": "Using local demo stub; set UPSCALE_FAITHFUL_BACKEND=realesrgan for the real model",
            }
        )

    for model_id, label, backend, command, model_path, repo_path in [
        (
            "swinir",
            "SwinIR",
            settings.swinir_backend,
            settings.swinir_command,
            settings.swinir_model_path,
            settings.swinir_repo_path,
        ),
        (
            "hat",
            "HAT",
            settings.hat_backend,
            settings.hat_command,
            settings.hat_model_path,
            settings.hat_repo_path,
        ),
    ]:
        if backend == "disabled":
            status = "disabled"
            configured = False
            detail = f"{label} backend is disabled"
        else:
            configured = bool(command) and _path_exists(model_path) and _path_exists(repo_path)
            status = "ready" if configured else "missing_config"
            detail = f"{label} external backend is ready" if configured else f"{label} command, weights, or repo path are missing"
        models.append(
            {
                "id": model_id,
                "label": label,
                "backend": backend,
                "status": status,
                "configured": configured,
                "detail": detail,
            }
        )
    return {"models": models}


def create_job(
    db: Session,
    *,
    image: UploadFile,
    scale: int,
    mode: str,
    scene: str = "product",
    selected_candidates: Optional[List[str]] = None,
    uploader_id: str = "local-user",
) -> Job:
    _validate_job_options(scale, mode, scene)
    normalized_candidates = normalize_selected_candidates(selected_candidates)
    job_id = new_id("up")
    stored = save_upload(image, job_id)
    warnings = []
    if scene in {"marketing", "ecommerce"}:
        warnings.append("text_or_logo_review_recommended")
    job = Job(
        id=job_id,
        uploader_id=uploader_id,
        original_file_path=str(stored.path),
        original_hash=stored.sha256,
        scale=scale,
        mode=mode,
        scene=scene,
        status="queued",
    )
    job.warnings = warnings
    job.selected_candidates = normalized_candidates
    db.add(job)
    db.commit()
    db.refresh(job)
    enqueue_job(job.id)
    return job


def create_batch_jobs(
    db: Session,
    *,
    images: List[UploadFile],
    scale: int,
    mode: str,
    scene: str = "product",
    selected_candidates: Optional[List[str]] = None,
    uploader_id: str = "local-user",
) -> Tuple[str, List[Job]]:
    if not images:
        raise HTTPException(status_code=422, detail="at least one image is required")
    batch_id = new_id("batch")
    jobs = [
        create_job(
            db,
            image=image,
            scale=scale,
            mode=mode,
            scene=scene,
            selected_candidates=selected_candidates,
            uploader_id=uploader_id,
        )
        for image in images
    ]
    _write_batch_manifest(batch_id, [job.id for job in jobs])
    return batch_id, jobs


def _batch_manifest_path(batch_id: str) -> Path:
    return get_settings().storage_root / "batches" / f"{batch_id}.json"


def _write_batch_manifest(batch_id: str, job_ids: List[str]) -> None:
    path = _batch_manifest_path(batch_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"batch_id": batch_id, "job_ids": job_ids}, ensure_ascii=False), encoding="utf-8")


def get_batch_job_ids(batch_id: str) -> List[str]:
    path = _batch_manifest_path(batch_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Batch not found")
    payload = json.loads(path.read_text(encoding="utf-8"))
    job_ids = payload.get("job_ids", [])
    if not isinstance(job_ids, list):
        raise HTTPException(status_code=500, detail="Batch manifest is invalid")
    return [str(job_id) for job_id in job_ids]


def build_batch_results_zip(db: Session, batch_id: str) -> BytesIO:
    buffer = BytesIO()
    job_ids = get_batch_job_ids(batch_id)
    added = 0
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for job_id in job_ids:
            job = get_job(db, job_id)
            if job.status != "completed":
                continue
            for result in job.results:
                path = Path(result.file_path)
                if not path.exists():
                    continue
                archive.write(path, arcname=f"{job.id}-{result.result_type}{path.suffix}")
                added += 1
    if added == 0:
        raise HTTPException(status_code=404, detail="No completed results are available for this batch")
    buffer.seek(0)
    return buffer


def _job_risk_level(job: Job) -> str:
    risk_order = {"low": 0, "medium": 1, "high": 2}
    if job.results:
        return max((result.risk_level for result in job.results), key=lambda value: risk_order.get(value, 0))
    if job.warnings:
        return "medium"
    return "low"


def _latest_feedback(job: Job) -> Optional[Feedback]:
    if not job.feedback:
        return None
    return max(job.feedback, key=lambda feedback: feedback.created_at)


def _semantic_manifest_path(job_id: str) -> Path:
    return get_settings().storage_root / "manifests" / f"{job_id}.json"


def _write_semantic_manifest(job_id: str, payload: dict) -> None:
    path = _semantic_manifest_path(job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_semantic_manifest(job_id: str) -> Optional[dict]:
    path = _semantic_manifest_path(job_id)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _routing_execution_payload(job: Job, routing, executed_candidate_types: Optional[List[str]] = None) -> dict:
    executed = executed_candidate_types if executed_candidate_types is not None else [result.result_type for result in job.results]
    enabled_candidate_types = _enabled_candidate_types()
    if job.status in {"completed", "failed"}:
        skipped = [
            candidate_type
            for candidate_type in routing.candidate_types
            if candidate_type not in executed
        ]
    else:
        skipped = []
    skip_reasons = {
        candidate_type: "backend_disabled_or_not_configured"
        if candidate_type not in enabled_candidate_types
        else "candidate_not_generated"
        for candidate_type in skipped
    }
    return routing.copy(
        update={
            "executed_candidate_types": executed,
            "skipped_candidate_types": skipped,
            "skip_reasons": skip_reasons,
        }
    ).dict()


def _build_semantic_payload(job: Job, executed_candidate_types: Optional[List[str]] = None) -> dict:
    understanding, plan, routing = build_semantic_context(
        Path(job.original_file_path),
        scene=job.scene,
        requested_mode=job.mode,
        selected_candidates=job.selected_candidates or None,
    )
    return {
        "job_id": job.id,
        "understanding": understanding.dict(),
        "upscale_plan": plan.dict(),
        "routing_decision": _routing_execution_payload(job, routing, executed_candidate_types),
        "data_governance": build_data_governance_summary().dict(),
    }


def _semantic_payload_for_job(job: Job) -> dict:
    return _read_semantic_manifest(job.id) or _build_semantic_payload(job)


def _format_protected_regions_for_report(plan: dict) -> str:
    formatted = []
    for region in plan.get("protected_region_details", []):
        bbox = region.get("bbox")
        region_type = region.get("type", "unknown")
        if bbox:
            formatted.append(f"{region_type}:{','.join(str(value) for value in bbox)}")
        else:
            formatted.append(f"{region_type}:unlocalized")
    return ";".join(formatted)


def build_batch_evaluation_report(db: Session, batch_id: str) -> dict:
    job_ids = get_batch_job_ids(batch_id)
    jobs = [get_job(db, job_id) for job_id in job_ids]
    rows = []
    ratings = []
    usable_count = 0
    issue_counts: Counter[str] = Counter()
    high_risk_jobs = []

    for job in jobs:
        feedback = _latest_feedback(job)
        risk_level = _job_risk_level(job)
        issues = feedback.issues if feedback else []
        semantic_payload = _semantic_payload_for_job(job)
        understanding = semantic_payload["understanding"]
        plan = semantic_payload["upscale_plan"]
        routing = semantic_payload["routing_decision"]
        issue_counts.update(issues)
        if feedback:
            ratings.append(feedback.rating)
            if feedback.usable:
                usable_count += 1
        if risk_level == "high":
            high_risk_jobs.append(job.id)
        rows.append(
            {
                "job_id": job.id,
                "status": job.status,
                "scale": job.scale,
                "mode": job.mode,
                "scene": job.scene,
                "risk_level": risk_level,
                "rating": feedback.rating if feedback else "",
                "usable": feedback.usable if feedback else "",
                "issues": ";".join(issues),
                "semantic_risks": ";".join(understanding["detected_risks"]),
                "protected_regions": _format_protected_regions_for_report(plan),
                "routing_reasons": ";".join(routing["reasons"]),
                "comment": feedback.comment if feedback else "",
            }
        )

    average_rating = round(sum(ratings) / len(ratings), 1) if ratings else None
    return {
        "batch_id": batch_id,
        "sample_count": len(jobs),
        "completed_count": sum(1 for job in jobs if job.status == "completed"),
        "failed_count": sum(1 for job in jobs if job.status == "failed"),
        "feedback_count": len(ratings),
        "average_rating": average_rating,
        "usable_count": usable_count,
        "high_risk_jobs": high_risk_jobs,
        "issue_counts": dict(issue_counts.most_common()),
        "rows": rows,
    }


def render_evaluation_report_markdown(report: dict) -> str:
    average_rating = report["average_rating"] if report["average_rating"] is not None else "暂无评分"
    issue_lines = [
        f"- {issue}: {count}"
        for issue, count in report["issue_counts"].items()
    ] or ["- 暂无问题标签"]
    high_risk_lines = [f"- {job_id}" for job_id in report["high_risk_jobs"]] or ["- 暂无高风险样本"]
    row_lines = [
        (
            f"| {row['job_id']} | {row['status']} | {row['mode']} | {row['scene']} | "
            f"{row['risk_level']} | {row['rating'] or '-'} | {row['usable'] if row['usable'] != '' else '-'} | "
            f"{row['issues'] or '-'} | {row['semantic_risks'] or '-'} | {row['protected_regions'] or '-'} |"
        )
        for row in report["rows"]
    ]
    return "\n".join(
        [
            f"# 高清放大评测报告 - {report['batch_id']}",
            "",
            "## 汇总",
            "",
            f"- 样本数: {report['sample_count']}",
            f"- 完成数: {report['completed_count']}",
            f"- 失败数: {report['failed_count']}",
            f"- 已评分数: {report['feedback_count']}",
            f"- 平均评分: {average_rating}",
            f"- 可用数: {report['usable_count']}",
            "",
            "## 高风险样本",
            "",
            *high_risk_lines,
            "",
            "## 典型问题标签",
            "",
            *issue_lines,
            "",
            "## 样本明细",
            "",
            "| Job ID | 状态 | 模式 | 场景 | 风险 | 评分 | 可用 | 问题标签 | 语义风险 | 保护区域 |",
            "|---|---|---|---|---|---:|---|---|---|---|",
            *row_lines,
            "",
            "> 本报告仅供本地评测和训练数据复盘使用，含 Logo/文字/型号/仪表盘区域的样本需人工复核。",
            "",
        ]
    )


def render_evaluation_report_csv(report: dict) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "job_id",
            "status",
            "scale",
            "mode",
            "scene",
            "risk_level",
            "rating",
            "usable",
            "issues",
            "semantic_risks",
            "protected_regions",
            "routing_reasons",
            "comment",
        ]
    )
    for row in report["rows"]:
        writer.writerow(
            [
                row["job_id"],
                row["status"],
                row["scale"],
                row["mode"],
                row["scene"],
                row["risk_level"],
                row["rating"],
                row["usable"],
                row["issues"],
                row["semantic_risks"],
                row["protected_regions"],
                row["routing_reasons"],
                row["comment"],
            ]
        )
    return output.getvalue()


PROBLEM_ISSUE_LABELS = {
    "logo_error": "Logo/文字错误",
    "structure_changed": "产品结构变形",
    "fake_texture": "材质异常",
    "color_shift": "颜色偏移",
    "text_blur": "文字模糊",
    "oversharpen": "过锐化",
    "too_slow": "处理较慢",
    "other": "其他问题",
}


def _selected_or_first_result(job: Job, feedback: Optional[Feedback]) -> Optional[Result]:
    if feedback:
        for result in job.results:
            if result.id == feedback.selected_result_id:
                return result
    return job.results[0] if job.results else None


def _risk_sample_reason(job: Job, risk_level: str, feedback: Optional[Feedback]) -> str:
    reasons = []
    if job.status == "failed":
        reasons.append("任务失败")
    if risk_level != "low":
        reasons.append(f"{risk_level}风险")
    if feedback and not feedback.usable:
        reasons.append("评审不可用")
    if feedback:
        reasons.extend(PROBLEM_ISSUE_LABELS[issue] for issue in feedback.issues if issue in PROBLEM_ISSUE_LABELS)
    return "；".join(dict.fromkeys(reasons))


def _suggest_risk_action(job: Job, feedback: Optional[Feedback]) -> str:
    issues = set(feedback.issues if feedback else [])
    if job.status == "failed":
        return "重新处理或检查推理服务配置"
    if "logo_error" in issues or "text_blur" in issues:
        return "人工回贴 Logo/文字并进入负样本复盘"
    if "structure_changed" in issues:
        return "进入结构一致性负样本集"
    if "fake_texture" in issues:
        return "进入材质异常负样本集"
    if "color_shift" in issues:
        return "进入颜色一致性负样本集"
    if feedback and not feedback.usable:
        return "人工复核后决定重跑或纳入负样本"
    return "人工复核"


def build_batch_risk_samples(db: Session, batch_id: str) -> dict:
    job_ids = get_batch_job_ids(batch_id)
    rows = []
    for job_id in job_ids:
        job = get_job(db, job_id)
        feedback = _latest_feedback(job)
        risk_level = _job_risk_level(job)
        problem_issues = [issue for issue in (feedback.issues if feedback else []) if issue != "good"]
        is_risk_sample = (
            job.status == "failed"
            or risk_level != "low"
            or bool(problem_issues)
            or bool(feedback and not feedback.usable)
        )
        if not is_risk_sample:
            continue
        selected_result = _selected_or_first_result(job, feedback)
        rows.append(
            {
                "job_id": job.id,
                "original_path": job.original_file_path,
                "result_path": selected_result.file_path if selected_result else "",
                "scale": job.scale,
                "mode": job.mode,
                "scene": job.scene,
                "status": job.status,
                "risk_level": risk_level,
                "rating": feedback.rating if feedback else "",
                "usable": feedback.usable if feedback else "",
                "issues": ";".join(feedback.issues if feedback else []),
                "risk_reason": _risk_sample_reason(job, risk_level, feedback),
                "suggested_action": _suggest_risk_action(job, feedback),
                "comment": feedback.comment if feedback else ";".join(job.warnings),
            }
        )
    return {"batch_id": batch_id, "sample_count": len(rows), "rows": rows}


def render_risk_samples_csv(report: dict) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["仅供本地训练/评估使用，不上传第三方公共服务"])
    writer.writerow(
        [
            "job_id",
            "original_path",
            "result_path",
            "scale",
            "mode",
            "scene",
            "status",
            "risk_level",
            "rating",
            "usable",
            "issues",
            "suggested_action",
            "risk_reason",
            "comment",
        ]
    )
    for row in report["rows"]:
        writer.writerow(
            [
                row["job_id"],
                row["original_path"],
                row["result_path"],
                row["scale"],
                row["mode"],
                row["scene"],
                row["status"],
                row["risk_level"],
                row["rating"],
                row["usable"],
                row["issues"],
                row["suggested_action"],
                row["risk_reason"],
                row["comment"],
            ]
        )
    return output.getvalue()


def render_risk_samples_markdown(report: dict) -> str:
    row_lines = [
        (
            f"| {row['job_id']} | {row['status']} | {row['risk_level']} | {row['issues'] or '-'} | "
            f"{row['risk_reason'] or '-'} | {row['suggested_action']} |"
        )
        for row in report["rows"]
    ] or ["| - | - | - | - | 暂无失败或高风险样本 | - |"]
    return "\n".join(
        [
            f"# 失败/高风险样本清单 - {report['batch_id']}",
            "",
            f"- 风险样本数: {report['sample_count']}",
            "- 仅供本地训练/评估使用，不上传第三方公共服务。",
            "- 重点复核：Logo/文字错误、产品结构变形、材质异常、颜色偏移。",
            "",
            "| Job ID | 状态 | 风险 | 问题标签 | 风险原因 | 建议动作 |",
            "|---|---|---|---|---|---|",
            *row_lines,
            "",
        ]
    )


def enqueue_job(job_id: str) -> None:
    settings = get_settings()
    if not settings.enqueue_jobs:
        return
    try:
        from redis import Redis
        from rq import Queue
    except ImportError as exc:
        raise RuntimeError("Redis/RQ dependencies are not installed") from exc
    queue = Queue("upscale", connection=Redis.from_url(settings.redis_url))
    queue.enqueue("app.workers.upscale_worker.process_job_by_id", job_id)


def get_job(db: Session, job_id: str) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def get_result(db: Session, result_id: str) -> Result:
    result = db.get(Result, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result


def downloadable_result_path(result: Result) -> Path:
    path = Path(result.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")
    return path


def first_downloadable_result_for_job(job: Job) -> Result:
    ordered_results = _ordered_results(job.results)
    if not ordered_results:
        raise HTTPException(status_code=404, detail="No completed results are available for this job")
    return ordered_results[0]


def list_recent_jobs(db: Session, limit: int = 20) -> List[Job]:
    return (
        db.query(Job)
        .order_by(Job.created_at.desc())
        .limit(limit)
        .all()
    )


def _public_path(path: str) -> str:
    p = Path(path)
    parts = p.parts
    if "storage" in parts:
        idx = parts.index("storage")
        return "/" + "/".join(parts[idx:])
    return path


def serialize_job(job: Job) -> dict:
    ordered_results = _ordered_results(job.results)
    semantic_payload = _semantic_payload_for_job(job)
    return {
        "job_id": job.id,
        "status": job.status,
        "scale": job.scale,
        "mode": job.mode,
        "selected_candidates": job.selected_candidates,
        "original_url": _public_path(job.original_file_path),
        "warnings": job.warnings,
        "results": [
            {
                "id": result.id,
                "type": result.result_type,
                "url": _public_path(result.file_path),
                "thumbnail_url": _public_path(result.thumbnail_path),
                "model_name": result.model_name,
                "model_version": result.model_version,
                "quality_score": result.quality_score,
                "risk_level": result.risk_level,
            }
            for result in ordered_results
        ],
        "understanding": semantic_payload["understanding"],
        "upscale_plan": semantic_payload["upscale_plan"],
        "routing_decision": semantic_payload["routing_decision"],
        "data_governance": semantic_payload["data_governance"],
    }


def serialize_job_summary(job: Job) -> dict:
    risk_order = {"low": 0, "medium": 1, "high": 2}
    risk_level = "low"
    if job.results:
        risk_level = max((result.risk_level for result in job.results), key=lambda value: risk_order.get(value, 0))
    elif job.warnings:
        risk_level = "medium"
    ordered_results = _ordered_results(job.results)
    thumbnail_url = _public_path(ordered_results[0].thumbnail_path) if ordered_results else None
    result_url = _public_path(ordered_results[0].file_path) if ordered_results else None
    return {
        "job_id": job.id,
        "status": job.status,
        "scale": job.scale,
        "mode": job.mode,
        "scene": job.scene,
        "warnings": job.warnings,
        "result_count": len(job.results),
        "thumbnail_url": thumbnail_url,
        "result_url": result_url,
        "risk_level": risk_level,
        "created_at": job.created_at,
    }


def _enabled_candidate_types() -> set:
    settings = get_settings()
    enabled = {"faithful"}
    if settings.realistic_backend != "disabled":
        enabled.add("realistic")
    if settings.swinir_backend != "disabled":
        enabled.add("swinir")
    if settings.hat_backend != "disabled":
        enabled.add("hat")
    return enabled


def _adapters_for_candidates(candidate_types: Iterable[str]) -> Iterable[Tuple[str, object]]:
    settings = get_settings()
    yielded = set()
    for candidate_type in candidate_types:
        if candidate_type in yielded:
            continue
        yielded.add(candidate_type)
        if candidate_type == "faithful":
            if settings.faithful_backend == "realesrgan":
                yield "faithful", RealESRGANAdapter(
                    executable_path=Path(settings.realesrgan_executable) if settings.realesrgan_executable else None,
                    model_path=Path(settings.realesrgan_model_path) if settings.realesrgan_model_path else None,
                    model=settings.realesrgan_model,
                    timeout_seconds=settings.realesrgan_timeout_seconds,
                )
            else:
                yield "faithful", StubUpscaleAdapter(sharpen=True)
        elif candidate_type == "realistic":
            if settings.realistic_backend == "stub":
                yield "realistic", StubUpscaleAdapter(sharpen=True)
            elif settings.realistic_backend != "disabled":
                yield "realistic", DiffusionUpscaleAdapter()
        elif candidate_type == "swinir":
            if settings.swinir_backend == "external":
                yield "swinir", ExternalUpscaleAdapter(
                    model_name="swinir",
                    model_version="external",
                    command=settings.swinir_command,
                    model_path=Path(settings.swinir_model_path) if settings.swinir_model_path else None,
                    extra_args=["--repo-path", settings.swinir_repo_path] if settings.swinir_repo_path else [],
                    timeout_seconds=settings.swinir_timeout_seconds,
                )
            else:
                yield "swinir", DisabledOptionalModelAdapter("swinir")
        elif candidate_type == "hat":
            if settings.hat_backend == "external":
                yield "hat", ExternalUpscaleAdapter(
                    model_name="hat",
                    model_version="external",
                    command=settings.hat_command,
                    model_path=Path(settings.hat_model_path) if settings.hat_model_path else None,
                    extra_args=["--repo-path", settings.hat_repo_path] if settings.hat_repo_path else [],
                    timeout_seconds=settings.hat_timeout_seconds,
                )
            else:
                yield "hat", DisabledOptionalModelAdapter("hat")


def _ordered_results(results: Iterable[Result]) -> List[Result]:
    return sorted(
        results,
        key=lambda result: CANDIDATE_DISPLAY_ORDER.index(result.result_type)
        if result.result_type in CANDIDATE_DISPLAY_ORDER
        else len(CANDIDATE_DISPLAY_ORDER),
    )


def process_job(db: Session, job_id: str) -> Job:
    job = get_job(db, job_id)
    job.status = "running"
    db.commit()

    generated_result_types: List[str] = []
    understanding = None
    plan = None
    try:
        created_results = 0
        input_path = Path(job.original_file_path)
        understanding = understand_image(input_path, scene=job.scene)
        plan = create_upscale_plan(understanding, requested_mode=job.mode, selected_candidates=job.selected_candidates or None)
        job.warnings = sorted(set(job.warnings + plan.warnings))
        for result_type, adapter in _adapters_for_candidates(plan.candidate_types):
            result_id = new_id("res")
            output_path = result_path(result_id)
            thumb_path = thumbnail_path(result_id)
            try:
                output = adapter.upscale(input_path, output_path, job.scale)
                create_thumbnail(output.output_path, thumb_path)
                quality = evaluate_image(
                    input_path,
                    output.output_path,
                    contains_text=job.scene in {"marketing", "ecommerce"},
                    contains_logo=job.scene in {"marketing", "ecommerce"},
                )
                result = Result(
                    id=result_id,
                    job_id=job.id,
                    result_type=result_type,
                    file_path=str(output.output_path),
                    thumbnail_path=str(thumb_path),
                    model_name=output.model_name,
                    model_version=output.model_version,
                    quality_score=quality.quality_score,
                    risk_level=quality.risk_level,
                )
                job.warnings = sorted(set(job.warnings + output.warnings + quality.warnings))
                db.add(result)
                created_results += 1
                generated_result_types.append(result_type)
            except ModelConfigurationError as exc:
                job.warnings = sorted(set(job.warnings + [str(exc)]))
        if created_results == 0:
            raise RuntimeError("No result images were generated")
        job.status = "completed"
    except Exception as exc:
        job.status = "failed"
        job.warnings = sorted(set(job.warnings + [f"worker_failed: {exc}"]))
    if understanding is not None and plan is not None:
        semantic_payload = _build_semantic_payload(job, executed_candidate_types=generated_result_types)
        _write_semantic_manifest(job.id, semantic_payload)
    db.commit()
    db.refresh(job)
    return job


def create_feedback(db: Session, job_id: str, payload: FeedbackCreate) -> Feedback:
    job = get_job(db, job_id)
    result = db.get(Result, payload.selected_result_id)
    if not result or result.job_id != job.id:
        raise HTTPException(status_code=404, detail="Selected result not found for this job")
    invalid = sorted(set(payload.issues) - ALLOWED_ISSUES)
    if invalid:
        raise HTTPException(status_code=422, detail=f"Invalid issue tags: {', '.join(invalid)}")
    feedback = Feedback(
        job_id=job.id,
        selected_result_id=result.id,
        rating=payload.rating,
        usable=payload.usable,
        comment=payload.comment,
    )
    feedback.issues = payload.issues
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback
