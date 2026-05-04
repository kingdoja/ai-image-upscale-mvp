import * as assert from "node:assert/strict";
import { test } from "node:test";
import { getLocalRegionEvalEntrypoint } from "./evaluation";

test("getLocalRegionEvalEntrypoint points reviewers to the primary local detector report", () => {
  const entrypoint = getLocalRegionEvalEntrypoint();

  assert.equal(entrypoint.command, ".\\scripts\\run_region_detector_eval.ps1");
  assert.equal(entrypoint.primaryReport.path, "reports/region-detector-eval-tesseract-logo-baseline.md");
  assert.equal(entrypoint.primaryReport.href, "/reports/region-detector-eval-tesseract-logo-baseline.md");
  assert.equal(entrypoint.secondaryReports[0].path, "reports/region-detector-eval-tesseract.md");
  assert.equal(entrypoint.secondaryReports[0].href, "/reports/region-detector-eval-tesseract.md");
  assert.match(entrypoint.clipboardText, /\.\\scripts\\run_region_detector_eval\.ps1/);
  assert.match(entrypoint.clipboardText, /reports\/region-detector-eval-tesseract-logo-baseline\.md/);
  assert.deepEqual(entrypoint.baselineMetrics, [
    { key: "bbox_match_rate_logo", value: "1.0" },
    { key: "bbox_match_rate_text", value: "1.0" },
    { key: "false_positive_logo", value: "0" }
  ]);
});
