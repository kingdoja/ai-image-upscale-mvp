import * as assert from "node:assert/strict";
import { test } from "node:test";
import { afterImageClipPath } from "./imageCompare";

test("afterImageClipPath keeps the result on the left and original on the right", () => {
  assert.equal(afterImageClipPath(0), "inset(0 100% 0 0)");
  assert.equal(afterImageClipPath(50), "inset(0 50% 0 0)");
  assert.equal(afterImageClipPath(100), "inset(0 0% 0 0)");
});

test("afterImageClipPath clamps slider positions", () => {
  assert.equal(afterImageClipPath(-10), "inset(0 100% 0 0)");
  assert.equal(afterImageClipPath(120), "inset(0 0% 0 0)");
});
