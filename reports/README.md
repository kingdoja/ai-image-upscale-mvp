# Region Detector Reports

This folder stores local evaluation outputs for the protected-region detector.

Start here:

- `region-detector-eval-tesseract-logo-baseline.md`
- `region-detector-eval-tesseract.md`

The logo-baseline report is the one to open first because it shows the current
best local evaluation path for the project:

- OCR text regions from Tesseract
- local logo/badge baseline fusion
- bbox localization quality

Run the one-click local evaluation entrypoint:

```powershell
.\scripts\run_region_detector_eval.ps1
```

If Tesseract lives somewhere else:

```powershell
.\scripts\run_region_detector_eval.ps1 -TesseractCommand "D:\Tools\Tesseract-OCR\tesseract.exe"
```

Current report interpretation:

- `bbox_match_rate_logo` should stay at `1.0` on the checked-in baseline set
- `bbox_match_rate_text` should stay at `1.0` on the checked-in baseline set
- `false_positive_logo` should stay at `0`

These reports are for local evaluation only. Do not upload approved local
samples to third-party services without explicit approval.
