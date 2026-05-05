import type { ResultRead } from "./api";

export type SelectableCandidate = "faithful" | "swinir" | "hat";

export const DEFAULT_CANDIDATES: SelectableCandidate[] = ["faithful"];
export const CANDIDATE_ORDER: SelectableCandidate[] = ["faithful", "swinir", "hat"];

export const CANDIDATE_OPTIONS: Array<{ value: SelectableCandidate; label: string }> = [
  { value: "faithful", label: "Real-ESRGAN" },
  { value: "swinir", label: "SwinIR" },
  { value: "hat", label: "HAT" }
];

export function orderedCandidates(candidates: SelectableCandidate[]): SelectableCandidate[] {
  const selected = new Set(candidates);
  return CANDIDATE_ORDER.filter((candidate) => selected.has(candidate));
}

export function visibleOrderedResults(results: ResultRead[]): ResultRead[] {
  return results
    .filter((result) => result.type !== "material_guard" && result.type !== "sharpened")
    .sort((left, right) => {
      return candidateOrderIndex(left.type) - candidateOrderIndex(right.type);
    });
}

export function visibleOrderedCandidateTypes(types: ResultRead["type"][]): ResultRead["type"][] {
  return types
    .filter((type) => type !== "material_guard" && type !== "sharpened")
    .sort((left, right) => candidateOrderIndex(left) - candidateOrderIndex(right));
}

function candidateOrderIndex(type: ResultRead["type"]): number {
  const index = CANDIDATE_ORDER.indexOf(type as SelectableCandidate);
  return index === -1 ? CANDIDATE_ORDER.length : index;
}
