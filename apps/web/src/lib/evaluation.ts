export type EvaluationScoreKey = "clarity" | "structure" | "logoText" | "material" | "color" | "usability";

export type EvaluationScores = Record<EvaluationScoreKey, number>;

export type LocalRegionEvalReport = {
  label: string;
  path: string;
  href: string;
  description: string;
};

export type LocalRegionEvalMetric = {
  key: string;
  value: string;
};

export type LocalRegionEvalEntrypoint = {
  command: string;
  primaryReport: LocalRegionEvalReport;
  secondaryReports: LocalRegionEvalReport[];
  baselineMetrics: LocalRegionEvalMetric[];
  clipboardText: string;
};

const COMMENT_KEYS: Record<EvaluationScoreKey, string> = {
  clarity: "clarity",
  structure: "structure",
  logoText: "logo_text",
  material: "material",
  color: "color",
  usability: "usability"
};

export function calculateEvaluationRating(scores: EvaluationScores) {
  const values = Object.values(scores);
  const average = values.reduce((sum, value) => sum + value, 0) / values.length;
  return Math.max(1, Math.min(5, Math.round(average)));
}

export function buildEvaluationFeedbackComment(scores: EvaluationScores, notes: string) {
  const scoreLines = (Object.keys(COMMENT_KEYS) as EvaluationScoreKey[]).map(
    (key) => `${COMMENT_KEYS[key]}=${scores[key]}`
  );
  const normalizedNotes = notes.trim() || "无";
  return ["[evaluation]", ...scoreLines, `notes=${normalizedNotes}`].join("\n");
}
export function getLocalRegionEvalEntrypoint(): LocalRegionEvalEntrypoint {
  return {
    command: ".\\scripts\\run_region_detector_eval.ps1",
    primaryReport: {
      label: "Tesseract + Logo baseline",
      path: "reports/region-detector-eval-tesseract-logo-baseline.md",
      href: "/reports/region-detector-eval-tesseract-logo-baseline.md",
      description: "Current best local detector baseline for OCR text plus local logo/badge fusion."
    },
    secondaryReports: [
      {
        label: "Tesseract only",
        path: "reports/region-detector-eval-tesseract.md",
        href: "/reports/region-detector-eval-tesseract.md",
        description: "OCR-only comparison report used to separate text localization from logo fusion gains."
      },
      {
        label: "CSV baseline",
        path: "reports/region-detector-eval-tesseract-logo-baseline.csv",
        href: "/reports/region-detector-eval-tesseract-logo-baseline.csv",
        description: "Machine-readable rows for missed regions, false positives, detector sources, and bbox IoU."
      }
    ],
    baselineMetrics: [
      { key: "bbox_match_rate_logo", value: "1.0" },
      { key: "bbox_match_rate_text", value: "1.0" },
      { key: "false_positive_logo", value: "0" }
    ],
    clipboardText:
      ".\\scripts\\run_region_detector_eval.ps1\n" +
      "Open this first: reports/region-detector-eval-tesseract-logo-baseline.md\n" +
      "Secondary report: reports/region-detector-eval-tesseract.md"
  };
}
