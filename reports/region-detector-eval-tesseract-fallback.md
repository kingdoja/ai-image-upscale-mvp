# Region Detector Evaluation

- dataset: `datasets\region-eval`
- backend: `tesseract`

## Summary

- sample_count: 4
- evaluated_count: 4
- missing_image_count: 0
- review_required_count: 4
- expected_text: 4
- detected_text: 0
- missed_text: 4
- false_positive_text: 0
- expected_logo: 4
- detected_logo: 1
- missed_logo: 3
- false_positive_logo: 0

## Warnings

- Tesseract is not available: 'tesseract' is not recognized as an internal or external command,
operable program or batch file.

## Samples

| sample | scene | status | expected | detected | missed | false positive | sources | boxes |
|---|---|---|---|---|---|---|---|---|
| samples/cc0-product-label.jpg | marketing | evaluated | text;logo | logo | text |  | logo:vision_detector | logo:103,80,569,330 |
| samples/cc0-new-label.jpg | marketing | evaluated | text;logo |  | text;logo |  |  |  |
| samples/commons-main-label.jpg | ecommerce | evaluated | text;logo |  | text;logo |  |  |  |
| samples/commons-produk-packaging.jpg | ecommerce | evaluated | text;logo |  | text;logo |  |  |  |

> This report is for local evaluation only. Images should not be uploaded to third-party services without approval.
