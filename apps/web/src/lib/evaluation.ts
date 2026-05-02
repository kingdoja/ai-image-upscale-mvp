export type EvaluationScoreKey = "clarity" | "structure" | "logoText" | "material" | "color" | "usability";

export type EvaluationScores = Record<EvaluationScoreKey, number>;

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
