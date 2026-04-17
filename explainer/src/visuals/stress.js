/* ═══════════════════════════════════════════════════════════════════════
   Stress deformation — Engine-driven legality graph with tooltips
   ═══════════════════════════════════════════════════════════════════════ */
import * as d3 from 'd3';
import { PHASES, PHASE_COLORS, STRESSOR_NAMES } from '../engine/constants.js';
import { showTooltip, hideTooltip } from '../tooltip.js';

const PHASE_META = [
  { id: 'evaluate', label: 'E', color: PHASE_COLORS.evaluate },
  { id: 'generate', label: 'G', color: PHASE_COLORS.generate },
  { id: 'select',   label: 'S', color: PHASE_COLORS.select },
  { id: 'execute',  label: 'X', color: PHASE_COLORS.execute },
  { id: 'reflect',  label: 'R', color: PHASE_COLORS.reflect },
];

export function initStressVisual(engine) {
  const container = document.getElementById('stress-visual');
  const note = document.getElementById('stress-note');
  if (!container) return;

  const size = 420, cx = size / 2, cy = size / 2, radius = 140;

  const svg = d3.select(container).append('svg')
    .attr('viewBox', `0 0 ${size} ${size}`)
    .attr('preserveAspectRatio', 'xMidYMid meet').style('max-width', '100%');

  const nodePos = PHASE_META.map((_, i) => {
    const angle = (i / PHASE_META.length) * Math.PI * 2 - Math.PI / 2;
    return { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius };
  });

  // Canonical edges (5 transitions)
  const canonicalEdges = [
    [0, 1], [1, 2], [2, 3], [3, 4], [4, 0],
  ];
  const canonicalKeys = [
    'evaluate->generate', 'generate->select', 'select->execute',
    'execute->reflect', 'reflect->evaluate',
  ];

  const edges = svg.selectAll('.edge').data(canonicalEdges).enter().append('g');

  const edgeLines = edges.append('line')
    .attr('x1', d => nodePos[d[0]].x).attr('y1', d => nodePos[d[0]].y)
    .attr('x2', d => nodePos[d[1]].x).attr('y2', d => nodePos[d[1]].y)
    .attr('stroke', '#6e8efb').attr('stroke-width', 3).attr('opacity', 0.6);

  const edgeLabels = edges.append('text')
    .attr('x', d => (nodePos[d[0]].x + nodePos[d[1]].x) / 2)
    .attr('y', d => (nodePos[d[0]].y + nodePos[d[1]].y) / 2)
    .attr('text-anchor', 'middle').attr('dy', '-8')
    .attr('fill', '#8a8a9a').attr('font-size', '10px').attr('font-family', 'JetBrains Mono, monospace');

  const penaltyLabels = edges.append('text')
    .attr('x', d => (nodePos[d[0]].x + nodePos[d[1]].x) / 2)
    .attr('y', d => (nodePos[d[0]].y + nodePos[d[1]].y) / 2)
    .attr('text-anchor', 'middle').attr('dy', '12')
    .attr('fill', '#555566').attr('font-size', '9px').attr('font-family', 'JetBrains Mono, monospace');

  const blockLabels = edges.append('text')
    .attr('x', d => (nodePos[d[0]].x + nodePos[d[1]].x) / 2)
    .attr('y', d => (nodePos[d[0]].y + nodePos[d[1]].y) / 2)
    .attr('text-anchor', 'middle').attr('dy', '-20')
    .attr('fill', '#ef4444').attr('font-size', '8px')
    .attr('font-family', 'JetBrains Mono, monospace').attr('font-weight', 600).attr('opacity', 0).text('BLOCKED');

  // Invisible hover targets (wider)
  const edgeHitAreas = edges.append('line')
    .attr('x1', d => nodePos[d[0]].x).attr('y1', d => nodePos[d[0]].y)
    .attr('x2', d => nodePos[d[1]].x).attr('y2', d => nodePos[d[1]].y)
    .attr('stroke', 'transparent').attr('stroke-width', 20).style('cursor', 'pointer');

  edgeHitAreas.on('mouseover', (event, d, i) => {
    const state = engine.getState();
    if (!state) return;
    const idx = canonicalEdges.indexOf(d);
    const key = canonicalKeys[idx];
    const leg = state.legality[key];
    if (!leg) return;

    let html = `<strong>${key}</strong><br>`;
    html += `<div class="tt-row"><span class="tt-label">A' =</span><span class="tt-value">${leg.A_prime.toFixed(4)}</span></div>`;
    html += `<div class="tt-row"><span class="tt-label">W' =</span><span class="tt-value">${leg.W_prime.toFixed(4)}</span></div>`;
    html += `<div class="tt-row"><span class="tt-label">A =</span><span>${leg.A.toFixed(2)}</span></div>`;
    html += `<span class="tt-label">Admissible: </span><span style="color:${leg.admissible ? '#22c55e' : '#ef4444'}">${leg.admissible ? 'yes' : 'NO'}</span>`;
    showTooltip(html, event);
  }).on('mousemove', (event) => {
    const el = document.getElementById('tooltip');
    if (el) showTooltip(el.innerHTML, event);
  }).on('mouseout', hideTooltip);

  // Nodes
  const nodes = svg.selectAll('.node').data(PHASE_META).enter()
    .append('g').attr('transform', (d, i) => `translate(${nodePos[i].x},${nodePos[i].y})`);

  nodes.append('circle').attr('r', 24).attr('fill', '#12121a')
    .attr('stroke', d => d.color).attr('stroke-width', 2);
  nodes.append('text').text(d => d.label).attr('text-anchor', 'middle').attr('dy', '0.35em')
    .attr('fill', d => d.color).attr('font-size', '16px')
    .attr('font-family', 'JetBrains Mono, monospace').attr('font-weight', 600);

  // Subscribe to engine
  engine.subscribe(state => {
    if (!state || !state.legality) return;

    let blocked = 0;

    canonicalKeys.forEach((key, i) => {
      const leg = state.legality[key];
      if (!leg) return;

      const admissible = leg.admissible;
      if (!admissible) blocked++;

      d3.select(edgeLines.nodes()[i])
        .transition().duration(150)
        .attr('stroke', admissible ? '#6e8efb' : '#ef4444')
        .attr('stroke-width', admissible ? Math.max(1, 3 - leg.W_prime * 4) : 1)
        .attr('opacity', admissible ? Math.max(0.2, 0.7 - leg.W_prime * 0.5) : 0.15)
        .attr('stroke-dasharray', admissible ? 'none' : '4,4');

      d3.select(edgeLabels.nodes()[i])
        .text(`A'=${leg.A_prime.toFixed(2)}`)
        .attr('fill', admissible ? '#8a8a9a' : '#ef4444');

      d3.select(penaltyLabels.nodes()[i])
        .text(`W'=${leg.W_prime.toFixed(2)}`);

      d3.select(blockLabels.nodes()[i])
        .transition().duration(150)
        .attr('opacity', admissible ? 0 : 0.8);
    });

    // Update note
    if (note) {
      if (blocked === 0) {
        const totalW = canonicalKeys.reduce((sum, k) => sum + (state.legality[k]?.W_prime || 0), 0);
        if (totalW < 0.8) {
          note.textContent = 'All transitions admissible. Low penalty cost. Full deliberative loop operates normally.';
        } else {
          note.textContent = `All transitions admissible but costly (total W' = ${totalW.toFixed(2)}). Deliberation is expensive.`;
        }
      } else if (blocked < 3) {
        note.textContent = `${blocked} transition${blocked > 1 ? 's' : ''} blocked. The canonical loop is fractured. Bypass paths may be the only viable option.`;
      } else {
        note.textContent = `${blocked} transitions blocked. Severe governance collapse. Only bypass shortcuts remain admissible.`;
      }
    }
  });
}
