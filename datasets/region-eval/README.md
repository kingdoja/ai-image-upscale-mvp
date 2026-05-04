# Region Detector Evaluation Dataset

This directory is for local protected-region detector evaluation.

Put approved local sample images under `samples/` and describe them in
`annotations.json`. Do not add private customer or production images unless
they are approved for local evaluation storage.

The current checked-in sample set uses a small number of public images from
PublicDomainPictures and Wikimedia Commons for smoke evaluation. Keep
`source_url` in `annotations.json` when adding or replacing public samples.
It also includes generated synthetic fixtures for text-only and negative
coverage. Regenerate those local fixtures with:

```powershell
.\.venv\Scripts\python.exe tools\generate_region_eval_synthetic_samples.py
```

Run:

```powershell
python tools/evaluate_region_detector.py `
  --annotations datasets/region-eval/annotations.json `
  --backend local `
  --markdown-output reports/region-detector-eval.md `
  --csv-output reports/region-detector-eval.csv
```

Supported `expected_regions` values:

- `text`
- `logo`

Supported scenes:

- `product`
- `marketing`
- `ecommerce`
- `other`

Optional bbox annotations:

```json
{
  "expected_bboxes": {
    "text": [100, 80, 1045, 1370],
    "logo": [103, 80, 1045, 530]
  }
}
```

Bounding boxes use `[x, y, width, height]`. The evaluator reports per-type IoU
and counts a bbox match when IoU is at least `0.3` by default. Override with
`--bbox-iou-threshold` when reviewing stricter localization.

The summary includes overall and per-type localization rates:

- `bbox_match_rate`
- `bbox_match_rate_text`
- `bbox_match_rate_logo`

Use these together with `matched_bbox_*` and `missed_bbox_*` counts to separate
"detected the right risk type" from "localized the protected region well enough
to be useful."

The detector summary also includes type-level precision/recall:

- `precision_text`
- `recall_text`
- `precision_logo`
- `recall_logo`

Use these before tuning a detector: raising recall while precision drops means
the detector is creating more manual review work, while raising bbox match rate
means the protection region is becoming more actionable.

Tesseract check:

```powershell
.\scripts\check_tesseract.ps1
```

If Tesseract is installed outside `PATH`, pass an executable path:

```powershell
.\scripts\check_tesseract.ps1 -Executable "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Current local OCR path used by this workspace:

```powershell
.\scripts\check_tesseract.ps1 -Executable "D:\Tools\Tesseract-OCR\tesseract.exe"
```

Run the OCR-backed evaluation:

```powershell
.\.venv\Scripts\python.exe tools\evaluate_region_detector.py `
  --annotations datasets\region-eval\annotations.json `
  --backend tesseract `
  --tesseract-command "D:\Tools\Tesseract-OCR\tesseract.exe" `
  --markdown-output reports\region-detector-eval-tesseract.md `
  --csv-output reports\region-detector-eval-tesseract.csv
```

Run the one-click local eval entrypoint:

```powershell
.\scripts\run_region_detector_eval.ps1
```

Use this first when you want the current baseline in one command. It writes the
Tesseract-only report and the Tesseract+Logo baseline report, then points you to
the baseline report to read first.

Run OCR plus the local Logo baseline adapter:

```powershell
.\.venv\Scripts\python.exe tools\evaluate_region_detector.py `
  --annotations datasets\region-eval\annotations.json `
  --backend tesseract `
  --tesseract-command "D:\Tools\Tesseract-OCR\tesseract.exe" `
  --logo-detector-backend external `
  --logo-detector-command ".\.venv\Scripts\python.exe tools\logo_detector_baseline.py" `
  --markdown-output reports\region-detector-eval-tesseract-logo-baseline.md `
  --csv-output reports\region-detector-eval-tesseract-logo-baseline.csv
```

`tools/logo_detector_baseline.py` is a local smoke-test adapter, not a real
brand/logo identity model. Use its report as a baseline before replacing it
with a stronger local Logo detector.
