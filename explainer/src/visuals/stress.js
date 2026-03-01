/* ═══════════════════════════════════════════════════════════════════════
   Stress deformation — Interactive legality graph
   ═══════════════════════════════════════════════════════════════════════ */
import * as d3 from 'd3';

const PHASES = [
  { id: 'evaluate', label: 'E', color: '#60a5fa' },
  { id: 'generate', label: 'G', color: '#34d399' },
  { id: 'select',   label: 'S', color: '#fbbf24' },
  { id: 'execute',  label: 'X', color: '#f87171' },
  { id: 'reflect',  label: 'R', color: '#c084fc' },
];

// Transition specs (simplified from minimal_spec.json)
const TRANSITIONS = [
  { source: 0, target: 1, A: 1.0, W: 0.10, alpha: 0.30, beta: 0.10, label: 'E\u2192G' },
  { source: 1, target: 2, A: 1.0, W: 0.10, alpha: 0.20, beta: 0.10, label: 'G\u2192S' },
  { source: 2, target: 3, A: 1.0, W: 0.10, alpha: 0.25, beta: 0.15, label: 'S\u2192X' },
  { source: 3, target: 4, A: 1.0, W: 0.10, alpha: 0.10, beta: 0.05, label: 'X\u2192R' },
  { source: 4, target: 0, A: 1.0, W: 0.10, alpha: 0.10, beta: 0.05, label: 'R\u2192E' },
];

export function initStressVisual() {
  const container = document.getElementById('stress-visual');
  const slider = document.getElementById('stress-slider');
  const valueDisplay = document.getElementById('stress-value');
  const note = document.getElementById('stress-note');
  if (!container || !slider) return;

  const size = 420;
  const cx = size / 2;
  const cy = size / 2;
  const radius = 140;

  const svg = d3.select(container)
    .append('svg')
    .attr('viewBox', `0 0 ${size} ${size}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .style('max-width', '420px');

  // Compute node positions
  const nodePos = PHASES.map((p, i) => {
    const angle = (i / PHASES.length) * Math.PI * 2 - Math.PI / 2;
    return { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius };
  });

  // Draw edges
  const edges = svg.selectAll('.edge')
    .data(TRANSITIONS)
    .enter()
    .append('g');

  const edgeLines = edges.append('line')
    .attr('x1', d => nodePos[d.source].x)
    .attr('y1', d => nodePos[d.source].y)
    .attr('x2', d => nodePos[d.target].x)
    .attr('y2', d => nodePos[d.target].y)
    .attr('stroke', '#6e8efb')
    .attr('stroke-width', 3)
    .attr('opacity', 0.6);

  // Edge labels (A' value)
  const edgeLabels = edges.append('text')
    .attr('x', d => (nodePos[d.source].x + nodePos[d.target].x) / 2)
    .attr('y', d => (nodePos[d.source].y + nodePos[d.target].y) / 2)
    .attr('text-anchor', 'middle')
    .attr('dy', '-8')
    .attr('fill', '#8a8a9a')
    .attr('font-size', '10px')
    .attr('font-family', 'JetBrains Mono, monospace');

  // Penalty labels (W' value)
  const penaltyLabels = edges.append('text')
    .attr('x', d => (nodePos[d.source].x + nodePos[d.target].x) / 2)
    .attr('y', d => (nodePos[d.source].y + nodePos[d.target].y) / 2)
    .attr('text-anchor', 'middle')
    .attr('dy', '12')
    .attr('fill', '#555566')
    .attr('font-size', '9px')
    .attr('font-family', 'JetBrains Mono, monospace');

  // Draw nodes
  const nodes = svg.selectAll('.node')
    .data(PHASES)
    .enter()
    .append('g')
    .attr('transform', (d, i) => `translate(${nodePos[i].x},${nodePos[i].y})`);

  const nodeCircles = nodes.append('circle')
    .attr('r', 24)
    .attr('fill', '#12121a')
    .attr('stroke', d => d.color)
    .attr('stroke-width', 2);

  nodes.append('text')
    .text(d => d.label)
    .attr('text-anchor', 'middle')
    .attr('dy', '0.35em')
    .attr('fill', d => d.color)
    .attr('font-size', '16px')
    .attr('font-family', 'JetBrains Mono, monospace')
    .attr('font-weight', 600);

  // "INADMISSIBLE" labels (hidden initially)
  const blockLabels = edges.append('text')
    .attr('x', d => (nodePos[d.source].x + nodePos[d.target].x) / 2)
    .attr('y', d => (nodePos[d.source].y + nodePos[d.target].y) / 2)
    .attr('text-anchor', 'middle')
    .attr('dy', '-20')
    .attr('fill', '#ef4444')
    .attr('font-size', '8px')
    .attr('font-family', 'JetBrains Mono, monospace')
    .attr('font-weight', 600)
    .attr('opacity', 0)
    .text('BLOCKED');

  function update(stressVal) {
    const s = stressVal / 100;
    valueDisplay.textContent = s.toFixed(2);

    let blocked = 0;

    TRANSITIONS.forEach((t, i) => {
      const aPrime = t.A - t.alpha * s;
      const wPrime = t.W + t.beta * s;
      const admissible = aPrime > 0;

      if (!admissible) blocked++;

      d3.select(edgeLines.nodes()[i])
        .transition().duration(150)
        .attr('stroke', admissible ? '#6e8efb' : '#ef4444')
        .attr('stroke-width', admissible ? Math.max(1, 3 - wPrime * 8) : 1)
        .attr('opacity', admissible ? Math.max(0.2, 0.7 - wPrime) : 0.15)
        .attr('stroke-dasharray', admissible ? 'none' : '4,4');

      d3.select(edgeLabels.nodes()[i])
        .text(`A'=${aPrime.toFixed(2)}`)
        .attr('fill', admissible ? '#8a8a9a' : '#ef4444');

      d3.select(penaltyLabels.nodes()[i])
        .text(`W'=${wPrime.toFixed(2)}`);

      d3.select(blockLabels.nodes()[i])
        .transition().duration(150)
        .attr('opacity', admissible ? 0 : 0.8);
    });

    // Update note text
    if (s < 0.3) {
      note.textContent = 'At low stress, all five transitions are admissible. The full deliberative loop operates.';
    } else if (s < 0.6) {
      note.textContent = 'Rising stress increases transition costs (W\') and erodes admissibility (A\'). Deliberation becomes expensive.';
    } else if (blocked === 0) {
      note.textContent = 'High stress. Transition penalties are steep. The system is under pressure but all paths remain open.';
    } else if (blocked < 3) {
      note.textContent = `${blocked} transition${blocked > 1 ? 's' : ''} blocked. The canonical loop is fractured. Bypass paths become the only viable option.`;
    } else {
      note.textContent = `${blocked} transitions blocked. Severe governance collapse. Only bypass shortcuts remain admissible.`;
    }
  }

  slider.addEventListener('input', () => update(parseInt(slider.value)));
  update(parseInt(slider.value));
}
