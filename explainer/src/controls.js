/* ═══════════════════════════════════════════════════════════════════════
   Controls — Stressor slider panel + cycle scrubber
   ═══════════════════════════════════════════════════════════════════════ */

import { PRIMARY_STRESSORS, SECONDARY_STRESSORS, DEMO_CYCLES } from './engine/constants.js';

export function initControls(engine) {
  buildStressorPanel(engine);
  buildCycleScrubber(engine);
}

// ── Stressor Panel ──────────────────────────────────────────────────
function buildStressorPanel(engine) {
  const container = document.getElementById('stressor-panel');
  if (!container) return;

  // Primary sliders
  const primaryDiv = document.createElement('div');
  primaryDiv.className = 'stressor-sliders';

  for (const s of PRIMARY_STRESSORS) {
    primaryDiv.appendChild(makeSlider(s, engine));
  }
  container.appendChild(primaryDiv);

  // Expandable secondary
  const toggle = document.createElement('button');
  toggle.className = 'stressor-expand-btn';
  toggle.textContent = 'More stressors';
  toggle.addEventListener('click', () => {
    const sec = container.querySelector('.stressor-secondary');
    if (sec) {
      sec.classList.toggle('expanded');
      toggle.textContent = sec.classList.contains('expanded') ? 'Fewer stressors' : 'More stressors';
    }
  });
  container.appendChild(toggle);

  const secondaryDiv = document.createElement('div');
  secondaryDiv.className = 'stressor-sliders stressor-secondary';
  for (const s of SECONDARY_STRESSORS) {
    secondaryDiv.appendChild(makeSlider(s, engine));
  }
  container.appendChild(secondaryDiv);

  // Subscribe to engine to update slider values
  engine.subscribe(state => {
    if (!state) return;
    for (const s of [...PRIMARY_STRESSORS, ...SECONDARY_STRESSORS]) {
      const slider = container.querySelector(`[data-stressor="${s.id}"]`);
      const label = container.querySelector(`[data-stressor-val="${s.id}"]`);
      if (slider && label) {
        const val = state.stressorVector[s.id] || 0;
        // Don't update slider position if user is dragging
        if (document.activeElement !== slider) {
          slider.value = Math.round(val * 100);
        }
        label.textContent = val.toFixed(2);
      }
    }
  });
}

function makeSlider(stressor, engine) {
  const wrap = document.createElement('div');
  wrap.className = 'stressor-slider-row';

  const label = document.createElement('label');
  label.innerHTML = `<span class="stressor-dot" style="background:${stressor.color}"></span>${stressor.label}: <span data-stressor-val="${stressor.id}" class="stressor-val">0.00</span>`;

  const input = document.createElement('input');
  input.type = 'range';
  input.min = '0';
  input.max = '100';
  input.value = '0';
  input.dataset.stressor = stressor.id;
  input.style.setProperty('--slider-color', stressor.color);

  input.addEventListener('input', () => {
    engine.setStressor(stressor.id, parseInt(input.value) / 100);
  });

  wrap.appendChild(label);
  wrap.appendChild(input);
  return wrap;
}

// ── Cycle Scrubber ──────────────────────────────────────────────────
function buildCycleScrubber(engine) {
  const container = document.getElementById('cycle-scrubber');
  if (!container) return;

  const label = document.createElement('span');
  label.className = 'cycle-label';
  label.textContent = 'Cycle: t = 1';

  const input = document.createElement('input');
  input.type = 'range';
  input.min = '1';
  input.max = String(DEMO_CYCLES);
  input.value = '1';
  input.className = 'cycle-input';

  const regimeIndicator = document.createElement('span');
  regimeIndicator.className = 'cycle-regime';

  input.addEventListener('input', () => {
    engine.setCycle(parseInt(input.value));
  });

  container.appendChild(label);
  container.appendChild(input);
  container.appendChild(regimeIndicator);

  engine.subscribe(state => {
    if (!state) return;
    label.textContent = `Cycle: t = ${state.cycle}`;
    if (document.activeElement !== input) {
      input.value = state.cycle;
    }
    regimeIndicator.textContent = state.activeRegime;
    regimeIndicator.style.color = getRegimeColor(state.activeRegime);
  });
}

function getRegimeColor(id) {
  const colors = {
    survival: '#ef4444', legal: '#f59e0b', moral: '#a855f7',
    economic: '#22c55e', epistemic: '#3b82f6', peacetime: '#6b7280',
  };
  return colors[id] || '#8a8a9a';
}
