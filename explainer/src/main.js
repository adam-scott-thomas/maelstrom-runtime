/* ═══════════════════════════════════════════════════════════════════════
   MAELSTROM EXPLAINER — Main entry (engine-driven)
   ═══════════════════════════════════════════════════════════════════════ */
import { SimulationEngine } from './engine/SimulationEngine.js';
import { initControls } from './controls.js';
import { initStormVisual } from './visuals/storm.js';
import { initLoopVisual } from './visuals/loop.js';
import { initRegimeVisual } from './visuals/regimes.js';
import { initStressVisual } from './visuals/stress.js';
import { initBypassVisual } from './visuals/bypass.js';
import { initRegretVisual } from './visuals/regret.js';
import { initDeterminismVisual } from './visuals/determinism.js';
import { initScroll } from './scroll.js';

document.addEventListener('DOMContentLoaded', () => {
  const engine = new SimulationEngine();

  // Initialize all visuals with engine reference
  initStormVisual(engine);
  initLoopVisual(engine);
  initRegimeVisual(engine);
  initStressVisual(engine);
  initBypassVisual(engine);
  initRegretVisual(engine);
  initDeterminismVisual(engine);

  // Controls (stressor sliders + cycle scrubber)
  initControls(engine);

  // Scroll behavior
  initScroll(engine);

  // Boot the engine
  engine.init();

  // Close inspector panel
  const closeBtn = document.getElementById('inspector-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      document.getElementById('inspector')?.classList.remove('open');
    });
  }
});
