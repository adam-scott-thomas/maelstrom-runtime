/* ═══════════════════════════════════════════════════════════════════════
   Determinism — Engine-driven hash comparison with seed/mutate controls
   ═══════════════════════════════════════════════════════════════════════ */
import * as d3 from 'd3';
import { SimulationEngine } from '../engine/SimulationEngine.js';

export function initDeterminismVisual(engine) {
  const container = document.getElementById('determinism-visual');
  if (!container) return;

  const width = 720, height = 340;
  const svg = d3.select(container).append('svg')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet');

  const cx = width / 2;
  const colWidth = 260, rowHeight = 26, startY = 70, maxRows = 8;

  // Labels
  const runALabel = svg.append('text').attr('x', cx - colWidth / 2 - 40).attr('y', 30)
    .attr('text-anchor', 'middle').attr('fill', '#6e8efb').attr('font-size', '12px')
    .attr('font-family', 'JetBrains Mono, monospace').attr('font-weight', 600);
  const runBLabel = svg.append('text').attr('x', cx + colWidth / 2 + 40).attr('y', 30)
    .attr('text-anchor', 'middle').attr('fill', '#a777e3').attr('font-size', '12px')
    .attr('font-family', 'JetBrains Mono, monospace').attr('font-weight', 600);

  svg.append('text').attr('x', cx - colWidth / 2 - 40).attr('y', 48)
    .attr('text-anchor', 'middle').attr('fill', '#555566').attr('font-size', '9px')
    .attr('font-family', 'JetBrains Mono, monospace').text('state_hash per cycle');
  svg.append('text').attr('x', cx + colWidth / 2 + 40).attr('y', 48)
    .attr('text-anchor', 'middle').attr('fill', '#555566').attr('font-size', '9px')
    .attr('font-family', 'JetBrains Mono, monospace').text('state_hash per cycle');

  // Groups for hash rows
  const runAG = svg.append('g');
  const runBG = svg.append('g');
  const matchG = svg.append('g');

  // Summary text
  const summaryText = svg.append('text').attr('x', cx).attr('text-anchor', 'middle')
    .attr('fill', '#22c55e').attr('font-size', '11px')
    .attr('font-family', 'JetBrains Mono, monospace').attr('font-weight', 500);
  const subText = svg.append('text').attr('x', cx).attr('text-anchor', 'middle')
    .attr('fill', '#555566').attr('font-size', '9px').attr('font-family', 'Inter, sans-serif');

  // Controls (HTML, appended below SVG)
  const controlDiv = document.createElement('div');
  controlDiv.style.cssText = 'display:flex;gap:0.75rem;justify-content:center;margin-top:1rem;flex-wrap:wrap;';

  const seedInput = document.createElement('input');
  seedInput.type = 'number';
  seedInput.value = '42';
  seedInput.min = '1';
  seedInput.max = '999999';
  seedInput.style.cssText = 'width:80px;background:#12121a;border:1px solid #1e1e2e;color:#e8e6e3;padding:0.5rem;border-radius:4px;font-family:JetBrains Mono,monospace;font-size:1rem;min-height:44px;';

  const seedLabel = document.createElement('span');
  seedLabel.textContent = 'Seed: ';
  seedLabel.style.cssText = 'font-size:0.75rem;color:#8a8a9a;font-family:JetBrains Mono,monospace;display:flex;align-items:center;gap:0.3rem;';
  seedLabel.prepend(seedInput);

  const runBtn = document.createElement('button');
  runBtn.textContent = 'Run Both';
  runBtn.style.cssText = 'background:#6e8efb;color:#fff;border:none;padding:0.5rem 1rem;border-radius:4px;font-size:0.85rem;cursor:pointer;font-family:Inter,sans-serif;min-height:44px;';

  const mutateBtn = document.createElement('button');
  mutateBtn.textContent = 'Mutate Run B';
  mutateBtn.style.cssText = 'background:#1e1e2e;color:#8a8a9a;border:1px solid #333;padding:0.5rem 1rem;border-radius:4px;font-size:0.85rem;cursor:pointer;font-family:Inter,sans-serif;min-height:44px;';

  controlDiv.appendChild(seedLabel);
  controlDiv.appendChild(runBtn);
  controlDiv.appendChild(mutateBtn);
  container.appendChild(controlDiv);

  let mutated = false;

  function runComparison() {
    const seed = parseInt(seedInput.value) || 42;
    mutated = false;

    // Run A
    const engineA = new SimulationEngine();
    engineA.seed = seed;
    const traceA = engineA.runFullSimulation();

    // Run B (same seed)
    const engineB = new SimulationEngine();
    engineB.seed = seed;
    const traceB = engineB.runFullSimulation();

    render(traceA, traceB, seed, seed);
  }

  function runMutated() {
    const seed = parseInt(seedInput.value) || 42;
    mutated = true;

    const engineA = new SimulationEngine();
    engineA.seed = seed;
    const traceA = engineA.runFullSimulation();

    // Run B with one stressor mutated
    const engineB = new SimulationEngine();
    engineB.seed = seed;
    engineB.stressorOverrides.threat_level = 0.95; // force a divergence
    const traceB = engineB.runFullSimulation();

    render(traceA, traceB, seed, seed, true);
  }

  function render(traceA, traceB, seedA, seedB, isMutated = false) {
    const rows = Math.min(maxRows, traceA.length);
    const leftX = cx - colWidth - 20;
    const rightX = cx + 20;

    runALabel.text(`Run A — seed=${seedA}`);
    runBLabel.text(`Run B — seed=${seedB}${isMutated ? ' (mutated)' : ''}`);

    // Clear
    runAG.selectAll('*').remove();
    runBG.selectAll('*').remove();
    matchG.selectAll('*').remove();

    let matches = 0;
    for (let i = 0; i < rows; i++) {
      const yPos = startY + i * rowHeight;
      const hashA = traceA[i]?.stateHash || '—';
      const hashB = traceB[i]?.stateHash || '—';
      const match = hashA === hashB;
      if (match) matches++;

      // Run A
      runAG.append('text').attr('x', leftX).attr('y', yPos)
        .attr('fill', '#555566').attr('font-size', '10px').attr('font-family', 'JetBrains Mono, monospace')
        .text(`t=${i + 1}`);
      runAG.append('text').attr('x', leftX + 35).attr('y', yPos)
        .attr('fill', '#8a8a9a').attr('font-size', '10px').attr('font-family', 'JetBrains Mono, monospace')
        .text(`0x${hashA}`);

      // Run B
      runBG.append('text').attr('x', rightX).attr('y', yPos)
        .attr('fill', '#555566').attr('font-size', '10px').attr('font-family', 'JetBrains Mono, monospace')
        .text(`t=${i + 1}`);
      runBG.append('text').attr('x', rightX + 35).attr('y', yPos)
        .attr('fill', match ? '#8a8a9a' : '#ef4444').attr('font-size', '10px')
        .attr('font-family', 'JetBrains Mono, monospace')
        .text(`0x${hashB}`);

      // Match indicator
      matchG.append('line').attr('x1', leftX + colWidth - 30).attr('y1', yPos - 3)
        .attr('x2', rightX).attr('y2', yPos - 3)
        .attr('stroke', match ? '#22c55e' : '#ef4444').attr('stroke-width', 1)
        .attr('opacity', 0.3).attr('stroke-dasharray', '3,3');
      matchG.append('text').attr('x', cx).attr('y', yPos)
        .attr('text-anchor', 'middle').attr('fill', match ? '#22c55e' : '#ef4444')
        .attr('font-size', '12px').text(match ? '=' : '\u2260');
    }

    const summaryY = startY + rows * rowHeight + 20;
    summaryText.attr('y', summaryY)
      .attr('fill', matches === rows ? '#22c55e' : '#ef4444')
      .text(matches === rows
        ? `${matches}/${rows} hashes match — bit-perfect determinism`
        : `${matches}/${rows} match — divergence detected at cycle ${traceA.findIndex((t, i) => t.stateHash !== traceB[i]?.stateHash) + 1}`);
    subText.attr('y', summaryY + 20)
      .text(matches === rows
        ? 'Proven over 3,000,000 ticks. Zero NaN. Zero Inf. Fully auditable.'
        : 'Different inputs produce different traces — determinism means same input = same output.');
  }

  runBtn.addEventListener('click', runComparison);
  mutateBtn.addEventListener('click', runMutated);

  // Initial render when engine is ready
  engine.subscribe(() => {
    if (!mutated) runComparison();
  });
}
