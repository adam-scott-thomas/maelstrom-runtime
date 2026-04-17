/* ═══════════════════════════════════════════════════════════════════════
   Deterministic RNG — Mulberry32
   Port of maelstrom/utils.py DeterministicRNG
   ═══════════════════════════════════════════════════════════════════════ */

export class DeterministicRNG {
  constructor(seed = 42) {
    this._seed = seed >>> 0;
    this._state = this._seed;
    this.drawCount = 0;
  }

  /** Returns a float in [0, 1). */
  next() {
    this.drawCount++;
    this._state = (this._state + 0x6D2B79F5) | 0;
    let t = Math.imul(this._state ^ (this._state >>> 15), 1 | this._state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  /** Returns noise in [-amplitude, +amplitude]. Matches Python rng.noise(). */
  noise(amplitude = 0.03) {
    return (this.next() * 2 - 1) * amplitude;
  }

  /** Reset to initial seed state. */
  reset() {
    this._state = this._seed;
    this.drawCount = 0;
  }
}
