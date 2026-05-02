import * as assert from "node:assert/strict";
import { test } from "node:test";
import { buildEvaluationFeedbackComment, calculateEvaluationRating, type EvaluationScores } from "./evaluation";

test("calculateEvaluationRating rounds the six review dimensions into one feedback rating", () => {
  const scores: EvaluationScores = {
    clarity: 5,
    structure: 4,
    logoText: 3,
    material: 4,
    color: 4,
    usability: 5
  };

  assert.equal(calculateEvaluationRating(scores), 4);
});

test("buildEvaluationFeedbackComment keeps a parseable evaluation block and reviewer notes", () => {
  const comment = buildEvaluationFeedbackComment(
    {
      clarity: 5,
      structure: 4,
      logoText: 3,
      material: 4,
      color: 4,
      usability: 5
    },
    "Logo 需要人工复核。"
  );

  assert.match(comment, /\[evaluation\]/);
  assert.match(comment, /clarity=5/);
  assert.match(comment, /logo_text=3/);
  assert.match(comment, /notes=Logo 需要人工复核。/);
});
