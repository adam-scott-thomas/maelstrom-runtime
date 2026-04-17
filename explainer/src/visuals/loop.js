/* ═══════════════════════════════════════════════════════════════════════
   Five-phase loop — Engine-driven with step/play controls
   ═══════════════════════════════════════════════════════════════════════ */
import * as d3 from 'd3';
import { PHASES, PHASE_COLORS, SCORE_DIMS } from '../engine/constants.js';
import { showTooltip, hideTooltip } from '../tooltip.js';

const PHASE_META = [
  { id: 'evaluate', label: 'Evaluate',  icon: 'E' },
  { id: 'generate', label: 'Generate',  icon: 'G' },
  { id: 'select',   label: 'Select',    icon: 'S' },
  { id: 'execute',  label: 'Execute',   icon: 'X' },
  { id: 'reflect',  label: 'Reflect',   icon: 'R' },
];

export function initLoopVisual(engine) {
  const container = document.getElementById('loop-visual');
  if (!container) return;

  const size = 420, cx = size / 2, cy = size / 2, radius = 140;

  const svg = d3.select(container).append('svg')
    .attr('viewBox', `0 0 ${size} ${size}`)
    .attr('preserveAspectRatio', 'xMidYMid meet').style('max-width', '100%');

  const nodeAngles = PHASE_META.map((_, i) => (i / PHASE_META.length) * Math.PI * 2 - Math.PI / 2);
  const nodePos = nodeAngles.map(a => ({ x: cx + Math.cos(a) * radius, y: cy + Math.sin(a) * radius }));

  // Edges
  PHASE_META.forEach((_, i) => {
    const ni = (i + 1) % PHASE_META.length;
    svg.append('line')
      .attr('x1', nodePos[i].x).attr('y1', nodePos[i].y)
      .attr('x2', nodePos[ni].x).attr('y2', nodePos[ni].y)
      .attr('stroke', '#1e1e2e').attr('stroke-width', 2);
  });

  // Nodes
  const nodes = svg.selectAll('.phase-node').data(PHASE_META).enter()
    .append('g').attr('class', 'phase-node').style('cursor', 'pointer')
    .attr('transform', (d, i) => `translate(${nodePos[i].x},${nodePos[i].y})`);

  const nodeCircles = nodes.append('circle').attr('r', 28)
    .attr('fill', '#12121a').attr('stroke', d => PHASE_COLORS[d.id]).attr('stroke-width', 2);

  nodes.append('text').text(d => d.icon).attr('text-anchor', 'middle').attr('dy', '0.35em')
    .attr('fill', d => PHASE_COLORS[d.id]).attr('font-size', '16px')
    .attr('font-family', 'JetBrains Mono, monospace').attr('font-weight', 600);

  nodes.append('text').text(d => d.label).attr('text-anchor', 'middle').attr('dy', '48px')
    .attr('fill', '#8a8a9a').attr('font-size', '11px').attr('font-family', 'Inter, sans-serif').attr('font-weight', 500);

  // Click node → show proposals in inspector
  nodes.on('click', (event, d) => {
    const state = engine.getState();
    if (!state || !state.proposals) return;
    const proposals = state.proposals[d.id] || [];
    const selected = state.selectedProposals[d.id];
    showProposalInspector(d, proposals, selected, state.activeRegime);
  });

  // Hover node → tooltip with selected proposal
  nodes.on('mouseover', (event, d) => {
    const state = engine.getState();
    if (!state) return;
    const sel = state.selectedProposals[d.id];
    const inPath = state.executionPath.includes(d.id);
    let html = `<strong style="color:${PHASE_COLORS[d.id]}">${d.label}</strong>`;
    if (!inPath) html += `<br><span style="color:#ef4444">SKIPPED (bypass)</span>`;
    else if (sel) html += `<br>${sel.description}<br><span class="tt-value">${sel.regimeScore?.toFixed(3) ?? '—'}</span>`;
    html += `<br><span class="tt-label">Click for proposals</span>`;
    showTooltip(html, event);
  }).on('mouseout', hideTooltip);

  // Pulse
  const pulse = svg.append('circle').attr('r', 6).attr('fill', '#6e8efb').attr('opacity', 0.9)
    .style('filter', 'drop-shadow(0 0 6px rgba(110,142,251,0.6))');

  // Center
  svg.append('text').attr('x', cx).attr('y', cy - 6).attr('text-anchor', 'middle')
    .attr('fill', '#555566').attr('font-size', '10px').attr('font-family', 'Inter, sans-serif')
    .attr('letter-spacing', '0.1em').text('CYCLE');
  const centerLabel = svg.append('text').attr('x', cx).attr('y', cy + 10).attr('text-anchor', 'middle')
    .attr('fill', '#6e8efb').attr('font-size', '10px').attr('font-family', 'JetBrains Mono, monospace').attr('opacity', 0.5);

  // State
  let execPath = [...PHASES];
  let canonicalPenalty = 0.5;
  let progress = 0;

  engine.subscribe(state => {
    if (!state) return;
    execPath = state.executionPath;
    canonicalPenalty = Math.max(0.1, state.canonicalPenalty || 0.5);
    centerLabel.text(`t = ${state.cycle}`);

    // Dim skipped nodes
    nodeCircles.attr('opacity', (d) => execPath.includes(d.id) ? 1 : 0.2)
      .attr('stroke-dasharray', (d) => execPath.includes(d.id) ? 'none' : '4,4');
  });

  function animate() {
    // Speed inversely proportional to canonical penalty
    const speed = 0.003 / Math.max(0.3, canonicalPenalty);
    progress = (progress + speed) % 1;

    // Follow execution path
    const pathLen = execPath.length;
    const segIdx = Math.floor(progress * pathLen);
    const segProgress = (progress * pathLen) - segIdx;
    const currPhaseIdx = PHASES.indexOf(execPath[segIdx % pathLen]);
    const nextPhaseIdx = PHASES.indexOf(execPath[(segIdx + 1) % pathLen]);

    if (currPhaseIdx >= 0 && nextPhaseIdx >= 0) {
      const p1 = nodePos[currPhaseIdx], p2 = nodePos[nextPhaseIdx];
      pulse.attr('cx', p1.x + (p2.x - p1.x) * segProgress)
        .attr('cy', p1.y + (p2.y - p1.y) * segProgress);
    }

    // Highlight active phase card
    const activePhase = execPath[segIdx % pathLen];
    document.querySelectorAll('.phase-card').forEach(card => {
      card.classList.toggle('active', card.dataset.phase === activePhase);
    });

    nodeCircles.attr('stroke-width', (d) => d.id === activePhase ? 3 : 2)
      .attr('r', (d) => d.id === activePhase ? 32 : 28);

    requestAnimationFrame(animate);
  }
  animate();
}

function showProposalInspector(phase, proposals, selected, regime) {
  const panel = document.getElementById('inspector');
  const content = document.getElementById('inspector-content');
  if (!panel || !content) return;

  const dimColors = {
    clarity: '#60a5fa', novelty: '#34d399', defensibility: '#fbbf24',
    tempo: '#f87171', coherence: '#c084fc',
  };

  let html = `<h3 style="color:${PHASE_COLORS[phase.id]}">${phase.label} — Proposals</h3>`;
  html += `<p style="font-size:0.7rem;color:#555566;margin-bottom:0.75rem;">Regime: ${regime}</p>`;

  for (const p of proposals) {
    const isSelected = selected && selected.id === p.id;
    html += `<div class="proposal-card ${isSelected ? 'selected' : ''}">`;
    html += `<div class="proposal-name">${p.description}${isSelected ? ' \u2713' : ''}</div>`;
    for (const dim of SCORE_DIMS) {
      const val = p.scores[dim] || 0;
      html += `<div class="score-bar-row">
        <span class="score-bar-label">${dim}</span>
        <div class="score-bar"><div class="score-bar-fill" style="width:${val * 100}%;background:${dimColors[dim]}"></div></div>
        <span class="score-bar-val">${val.toFixed(2)}</span>
      </div>`;
    }
    if (p.regimeScore !== undefined) {
      html += `<div class="regime-score">regime score: ${p.regimeScore.toFixed(3)}</div>`;
    }
    html += `</div>`;
  }

  content.innerHTML = html;
  panel.classList.add('open');
}
