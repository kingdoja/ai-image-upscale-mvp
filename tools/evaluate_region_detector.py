from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import json
from io import StringIO
from pathlib import Path
import subprocess
import sys
from typing import Dict, List, Sequence, Set


REGION_TYPES = ("text", "logo")


@dataclass(frozen=True)
class RegionEvalSample:
    file: str
    scene: str
    expected_regions: Set[str]
    expected_bboxes: Dict[str, List[int]]
    review_required: bool = False
    notes: str = ""


@dataclass(frozen=True)
class RegionEvalReport:
    dataset_dir: Path
    backend: str
    logo_detector_backend: str
    summary: Dict[str, object]
    rows: List[Dict[str, str]]
    warnings: List[str]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def configure_imports() -> None:
    api_root = project_root() / "apps" / "api"
    for path in (project_root(), api_root):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def _normalize_expected_regions(values: Sequence[str]) -> Set[str]:
    return {str(value) for value in values if str(value) in REGION_TYPES}


def _normalize_expected_bboxes(values: object) -> Dict[str, List[int]]:
    if not isinstance(values, dict):
        return {}
    normalized: Dict[str, List[int]] = {}
    for region_type, bbox in values.items():
        if region_type not in REGION_TYPES:
            continue
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        try:
            normalized[str(region_type)] = [int(value) for value in bbox]
        except (TypeError, ValueError):
            continue
    return normalized


def load_annotations(path: Path) -> List[RegionEvalSample]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("samples", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        raise ValueError("annotations.json must contain a samples list")
    samples = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        filename = str(row.get("file", "")).strip()
        if not filename:
            continue
        samples.append(
            RegionEvalSample(
                file=filename,
                scene=str(row.get("scene", "other")),
                expected_regions=_normalize_expected_regions(row.get("expected_regions", [])),
                expected_bboxes=_normalize_expected_bboxes(row.get("expected_bboxes", {})),
                review_required=bool(row.get("review_required", False)),
                notes=str(row.get("notes", "")),
            )
        )
    return samples


def _format_set(values: Set[str]) -> str:
    return ";".join(value for value in REGION_TYPES if value in values)


def _format_sources(regions: Sequence[object]) -> str:
    return ";".join(f"{region.type}:{region.source}" for region in regions)


def _format_boxes(regions: Sequence[object]) -> str:
    return ";".join(f"{region.type}:{','.join(str(value) for value in region.bbox)}" for region in regions)


def _format_expected_bboxes(expected_bboxes: Dict[str, List[int]]) -> str:
    return ";".join(
        f"{region_type}:{','.join(str(value) for value in expected_bboxes[region_type])}"
        for region_type in REGION_TYPES
        if region_type in expected_bboxes
    )


def _format_iou_map(values: Dict[str, float]) -> str:
    return ";".join(f"{region_type}:{values[region_type]:.2f}" for region_type in REGION_TYPES if region_type in values)


def _bbox_iou(first: List[int], second: List[int]) -> float:
    first_x1, first_y1, first_w, first_h = first
    second_x1, second_y1, second_w, second_h = second
    first_x2 = first_x1 + max(0, first_w)
    first_y2 = first_y1 + max(0, first_h)
    second_x2 = second_x1 + max(0, second_w)
    second_y2 = second_y1 + max(0, second_h)
    intersection_w = max(0, min(first_x2, second_x2) - max(first_x1, second_x1))
    intersection_h = max(0, min(first_y2, second_y2) - max(first_y1, second_y1))
    intersection = intersection_w * intersection_h
    first_area = max(0, first_w) * max(0, first_h)
    second_area = max(0, second_w) * max(0, second_h)
    union = first_area + second_area - intersection
    if union <= 0:
        return 0.0
    return intersection / union


def _bbox_eval(
    expected_bboxes: Dict[str, List[int]],
    regions: Sequence[object],
    *,
    iou_threshold: float,
) -> Dict[str, object]:
    detected_by_type = {region.type: region.bbox for region in regions if region.type in REGION_TYPES}
    ious: Dict[str, float] = {}
    matches: Set[str] = set()
    misses: Set[str] = set()
    for region_type, expected_bbox in expected_bboxes.items():
        detected_bbox = detected_by_type.get(region_type)
        if detected_bbox is None:
            ious[region_type] = 0.0
            misses.add(region_type)
            continue
        iou = _bbox_iou(expected_bbox, detected_bbox)
        ious[region_type] = iou
        if iou >= iou_threshold:
            matches.add(region_type)
        else:
            misses.add(region_type)
    return {"ious": ious, "matches": matches, "misses": misses}


def _empty_summary(sample_count: int, backend: str) -> Dict[str, object]:
    summary = {
        "sample_count": sample_count,
        "evaluated_count": 0,
        "missing_image_count": 0,
        "review_required_count": 0,
        "expected_bbox_count": 0,
        "matched_bbox_count": 0,
        "missed_bbox_count": 0,
    }
    for region_type in REGION_TYPES:
        summary[f"expected_{region_type}"] = 0
        summary[f"detected_{region_type}"] = 0
        summary[f"missed_{region_type}"] = 0
        summary[f"false_positive_{region_type}"] = 0
        summary[f"expected_bbox_{region_type}"] = 0
        summary[f"matched_bbox_{region_type}"] = 0
        summary[f"missed_bbox_{region_type}"] = 0
    return summary


def _rate(numerator: object, denominator: object) -> float:
    if not isinstance(numerator, int) or not isinstance(denominator, int) or denominator <= 0:
        return 0.0
    return round(numerator / denominator, 3)


def _add_bbox_rate_metrics(summary: Dict[str, object]) -> None:
    summary["bbox_match_rate"] = _rate(summary["matched_bbox_count"], summary["expected_bbox_count"])
    for region_type in REGION_TYPES:
        summary[f"bbox_match_rate_{region_type}"] = _rate(
            summary[f"matched_bbox_{region_type}"],
            summary[f"expected_bbox_{region_type}"],
        )


def _add_detection_rate_metrics(summary: Dict[str, object]) -> None:
    for region_type in REGION_TYPES:
        expected = summary[f"expected_{region_type}"]
        detected = summary[f"detected_{region_type}"]
        missed = summary[f"missed_{region_type}"]
        false_positive = summary[f"false_positive_{region_type}"]
        if not all(isinstance(value, int) for value in (expected, detected, missed, false_positive)):
            summary[f"precision_{region_type}"] = 0.0
            summary[f"recall_{region_type}"] = 0.0
            continue
        true_positive = max(0, detected - false_positive)
        summary[f"precision_{region_type}"] = _rate(true_positive, detected)
        summary[f"recall_{region_type}"] = _rate(expected - missed, expected)


def _command_with_version_arg(command: str) -> str:
    return f'{command} --version'


def check_tesseract_available(command: str = "tesseract") -> Dict[str, object]:
    try:
        completed = subprocess.run(
            _command_with_version_arg(command),
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"available": False, "message": f"Tesseract is not available: {exc}"}
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        return {"available": False, "message": f"Tesseract is not available: {detail or completed.returncode}"}
    first_line = (completed.stdout or completed.stderr or "").splitlines()
    version = first_line[0] if first_line else "tesseract"
    return {"available": True, "message": version}


def evaluate_dataset(
    annotations_path: Path,
    *,
    backend: str = "local",
    external_command: str = "",
    tesseract_command: str = "tesseract",
    logo_detector_backend: str = "local",
    logo_detector_command: str = "",
    bbox_iou_threshold: float = 0.3,
    timeout_seconds: int = 30,
) -> RegionEvalReport:
    configure_imports()
    from app.vision_regions import detect_protected_regions

    dataset_dir = annotations_path.parent
    samples = load_annotations(annotations_path)
    summary = _empty_summary(len(samples), backend)
    rows = []
    warnings = []
    if backend == "tesseract":
        availability = check_tesseract_available(tesseract_command)
        if not availability["available"]:
            warnings.append(str(availability["message"]))

    for sample in samples:
        image_path = dataset_dir / sample.file
        expected = set(sample.expected_regions)
        detected: Set[str] = set()
        regions = []
        status = "evaluated"

        if not image_path.exists():
            status = "missing_image"
            summary["missing_image_count"] += 1
        else:
            regions = detect_protected_regions(
                image_path,
                scene=sample.scene,
                backend=backend,
                external_command=external_command,
                tesseract_command=tesseract_command,
                logo_detector_backend=logo_detector_backend,
                logo_detector_command=logo_detector_command,
                timeout_seconds=timeout_seconds,
            )
            detected = {region.type for region in regions if region.type in REGION_TYPES}
            summary["evaluated_count"] += 1
            if sample.review_required:
                summary["review_required_count"] += 1

        missed = expected - detected
        false_positive = detected - expected
        for region_type in REGION_TYPES:
            if region_type in expected:
                summary[f"expected_{region_type}"] += 1
            if region_type in detected:
                summary[f"detected_{region_type}"] += 1
            if region_type in missed:
                summary[f"missed_{region_type}"] += 1
            if region_type in false_positive:
                summary[f"false_positive_{region_type}"] += 1

        bbox_eval = _bbox_eval(sample.expected_bboxes, regions, iou_threshold=bbox_iou_threshold)
        bbox_ious = bbox_eval["ious"]
        bbox_matches = bbox_eval["matches"]
        bbox_misses = bbox_eval["misses"]
        summary["expected_bbox_count"] += len(sample.expected_bboxes)
        summary["matched_bbox_count"] += len(bbox_matches)
        summary["missed_bbox_count"] += len(bbox_misses)
        for region_type in REGION_TYPES:
            if region_type in sample.expected_bboxes:
                summary[f"expected_bbox_{region_type}"] += 1
            if region_type in bbox_matches:
                summary[f"matched_bbox_{region_type}"] += 1
            if region_type in bbox_misses:
                summary[f"missed_bbox_{region_type}"] += 1

        rows.append(
            {
                "sample": sample.file,
                "scene": sample.scene,
                "status": status,
                "expected_regions": _format_set(expected),
                "detected_regions": _format_set(detected),
                "missed_regions": _format_set(missed),
                "false_positive_regions": _format_set(false_positive),
                "detector_sources": _format_sources(regions),
                "protected_regions": _format_boxes(regions),
                "expected_bboxes": _format_expected_bboxes(sample.expected_bboxes),
                "bbox_ious": _format_iou_map(bbox_ious),
                "bbox_matches": _format_set(bbox_matches),
                "bbox_misses": _format_set(bbox_misses),
                "review_required": str(sample.review_required),
                "notes": sample.notes,
            }
        )

    _add_detection_rate_metrics(summary)
    _add_bbox_rate_metrics(summary)

    return RegionEvalReport(
        dataset_dir=dataset_dir,
        backend=backend,
        logo_detector_backend=logo_detector_backend,
        summary=summary,
        rows=rows,
        warnings=warnings,
    )


def render_markdown(report: RegionEvalReport) -> str:
    lines = [
        "# Region Detector Evaluation",
        "",
        f"- dataset: `{report.dataset_dir}`",
        f"- backend: `{report.backend}`",
        f"- logo_detector_backend: `{report.logo_detector_backend}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in report.summary.items():
        lines.append(f"- {key}: {value}")
    if report.warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in report.warnings:
            lines.append(f"- {warning}")
    lines.extend(
        [
            "",
            "## Samples",
            "",
            "| sample | scene | status | expected | detected | missed | false positive | sources | boxes | expected boxes | bbox IoU | bbox match | bbox miss |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for row in report.rows:
        lines.append(
            "| {sample} | {scene} | {status} | {expected_regions} | {detected_regions} | "
            "{missed_regions} | {false_positive_regions} | {detector_sources} | {protected_regions} | "
            "{expected_bboxes} | {bbox_ious} | {bbox_matches} | {bbox_misses} |".format(**row)
        )
    lines.extend(
        [
            "",
            "> This report is for local evaluation only. Images should not be uploaded to third-party services without approval.",
            "",
        ]
    )
    return "\n".join(lines)


def render_csv(report: RegionEvalReport) -> str:
    output = StringIO()
    fieldnames = [
        "sample",
        "scene",
        "status",
        "expected_regions",
        "detected_regions",
        "missed_regions",
        "false_positive_regions",
        "detector_sources",
        "protected_regions",
        "expected_bboxes",
        "bbox_ious",
        "bbox_matches",
        "bbox_misses",
        "review_required",
        "notes",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in report.rows:
        writer.writerow({field: row[field] for field in fieldnames})
    return output.getvalue()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate protected-region detector output against local annotations.")
    parser.add_argument("--annotations", type=Path, default=Path("datasets/region-eval/annotations.json"))
    parser.add_argument("--backend", choices=("local", "external", "tesseract"), default="local")
    parser.add_argument("--external-command", default="")
    parser.add_argument("--tesseract-command", default="tesseract")
    parser.add_argument("--logo-detector-backend", choices=("local", "external"), default="local")
    parser.add_argument("--logo-detector-command", default="")
    parser.add_argument("--bbox-iou-threshold", type=float, default=0.3)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--markdown-output", type=Path, default=Path("reports/region-detector-eval.md"))
    parser.add_argument("--csv-output", type=Path, default=Path("reports/region-detector-eval.csv"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = evaluate_dataset(
        args.annotations,
        backend=args.backend,
        external_command=args.external_command,
        tesseract_command=args.tesseract_command,
        logo_detector_backend=args.logo_detector_backend,
        logo_detector_command=args.logo_detector_command,
        bbox_iou_threshold=args.bbox_iou_threshold,
        timeout_seconds=args.timeout_seconds,
    )
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.csv_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    args.csv_output.write_text(render_csv(report), encoding="utf-8")
    print(f"Region detector evaluation written to {args.markdown_output} and {args.csv_output}")


if __name__ == "__main__":
    main()
