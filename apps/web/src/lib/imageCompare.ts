export function afterImageClipPath(position: number) {
  const clamped = Math.max(0, Math.min(100, position));
  return `inset(0 ${100 - clamped}% 0 0)`;
}
