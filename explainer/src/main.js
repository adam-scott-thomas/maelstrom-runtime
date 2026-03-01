/* ═══════════════════════════════════════════════════════════════════════
   MAELSTROM EXPLAINER — Main entry
   ═══════════════════════════════════════════════════════════════════════ */
import { initStormVisual } from './visuals/storm.js';
import { initLoopVisual } from './visuals/loop.js';
import { initRegimeVisual } from './visuals/regimes.js';
import { initStressVisual } from './visuals/stress.js';
import { initBypassVisual } from './visuals/bypass.js';
import { initRegretVisual } from './visuals/regret.js';
import { initDeterminismVisual } from './visuals/determinism.js';
import { initScroll } from './scroll.js';

// ── Boot ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initStormVisual();
  initLoopVisual();
  initRegimeVisual();
  initStressVisual();
  initBypassVisual();
  initRegretVisual();
  initDeterminismVisual();
  initScroll();
});
