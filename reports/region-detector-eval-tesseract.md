# Region Detector Evaluation

- dataset: `datasets\region-eval`
- backend: `tesseract`
- logo_detector_backend: `local`

## Summary

- sample_count: 8
- evaluated_count: 8
- missing_image_count: 0
- review_required_count: 7
- expected_bbox_count: 12
- matched_bbox_count: 9
- missed_bbox_count: 3
- expected_text: 7
- detected_text: 7
- missed_text: 0
- false_positive_text: 0
- expected_bbox_text: 7
- matched_bbox_text: 6
- missed_bbox_text: 1
- expected_logo: 5
- detected_logo: 3
- missed_logo: 2
- false_positive_logo: 0
- expected_bbox_logo: 5
- matched_bbox_logo: 3
- missed_bbox_logo: 2
- precision_text: 1.0
- recall_text: 1.0
- precision_logo: 1.0
- recall_logo: 0.6
- bbox_match_rate: 0.75
- bbox_match_rate_text: 0.857
- bbox_match_rate_logo: 0.6

## Samples

| sample | scene | status | expected | detected | missed | false positive | sources | boxes | expected boxes | bbox IoU | bbox match | bbox miss |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| samples/cc0-product-label.jpg | marketing | evaluated | text;logo | text;logo |  |  | text:tesseract_ocr;logo:vision_detector | text:102,77,704,456;logo:103,80,569,330 | text:100,80,1045,1370;logo:103,80,1045,530 | text:0.22;logo:0.34 | logo | text |
| samples/cc0-new-label.jpg | marketing | evaluated | text;logo | text;logo |  |  | text:badge_text_fallback;logo:graphic_mark_detector | text:408,91,1100,1099;logo:408,91,1100,1099 | text:512,385,850,510;logo:408,91,1100,1099 | text:0.36;logo:1.00 | text;logo |  |
| samples/commons-main-label.jpg | ecommerce | evaluated | text;logo | text | logo |  | text:tesseract_ocr | text:184,168,1228,754 | text:184,168,1228,754;logo:610,330,410,420 | text:1.00;logo:0.00 | text | logo |
| samples/commons-produk-packaging.jpg | ecommerce | evaluated | text;logo | text | logo |  | text:tesseract_ocr | text:0,1,760,425 | text:0,135,800,398;logo:420,285,150,75 | text:0.53;logo:0.00 | text | logo |
| samples/synthetic-text-only-poster.png | marketing | evaluated | text | text |  |  | text:tesseract_ocr | text:88,99,430,270 | text:80,80,670,315 | text:0.55 | text |  |
| samples/synthetic-packaging-text-only.png | ecommerce | evaluated | text | text |  |  | text:tesseract_ocr | text:304,216,329,132 | text:300,205,330,145 | text:0.89 | text |  |
| samples/synthetic-plain-product-negative.png | product | evaluated |  |  |  |  |  |  |  |  |  |  |
| samples/synthetic-packaging-logo-text.png | ecommerce | evaluated | text;logo | text;logo |  |  | text:tesseract_ocr;logo:vision_detector | text:110,88,400,275;logo:110,92,115,58 | text:280,155,190,225;logo:110,92,114,104 | text:0.35;logo:0.55 | text;logo |  |

> This report is for local evaluation only. Images should not be uploaded to third-party services without approval.
