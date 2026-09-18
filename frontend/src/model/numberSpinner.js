// Clamps a NumberSpinner value into [min, max], rounding to the nearest
// integer first so a fractional or out-of-range input (typed directly into
// the number field, not just +/- clicks) always lands on a valid step.
export function clampSpinnerValue(value, min, max) {
  return Math.min(max, Math.max(min, Math.round(value)))
}
