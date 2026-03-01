/* ═══════════════════════════════════════════════════════════════════════
   Five-phase cognitive loop — Animated ring visualization
   ═══════════════════════════════════════════════════════════════════════ */
import * as d3 from 'd3';

const PHASES = [
  { id: 'evaluate', label: 'Evaluate',  color: '#60a5fa', icon: 'E' },
  { id: 'generate', label: 'Generate',  color: '#34d399', icon: 'G' },
  { id: 'select',   label: 'Select',    color: '#fbbf24', icon: 'S' },
  { id: 'execute',  label: 'Execute',   color: '#f87171', icon: 'X' },
  { id: 'reflect',  label: 'Reflect',   color: '#c084fc', icon: 'R' },
];

export function initLoopVisual() {
  const container = document.getElementById('loop-visual');
  if (!container) return;

  const size = 420;
  const cx = size / 2;
  const cy = size / 2;
  const radius = 140;

  const svg = d3.select(container)
    .append('svg')
    .attr('viewBox', `0 0 ${size} ${size}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .style('max-width', '420px');

  // Connection arcs
  PHASES.forEach((phase, i) => {
    const nextIdx = (i + 1) % PHASES.length;
    const a1 = (i / PHASES.length) * Math.PI * 2 - Math.PI / 2;
    const a2 = (nextIdx / PHASES.length) * Math.PI * 2 - Math.PI / 2;
    const x1 = cx + Math.cos(a1) * radius;
    const y1 = cy + Math.sin(a1) * radius;
    const x2 = cx + Math.cos(a2) * radius;
    const y2 = cy + Math.sin(a2) * radius;

    svg.append('line')
      .attr('x1', x1).attr('y1', y1)
      .attr('x2', x2).attr('y2', y2)
      .attr('stroke', '#1e1e2e')
      .attr('stroke-width', 2);
  });

  // Phase nodes
  const nodes = svg.selectAll('.phase-node')
    .data(PHASES)
    .enter()
    .append('g')
    .attr('class', 'phase-node')
    .attr('transform', (d, i) => {
      const angle = (i / PHASES.length) * Math.PI * 2 - Math.PI / 2;
      return `translate(${cx + Math.cos(angle) * radius},${cy + Math.sin(angle) * radius})`;
    });

  // Node circles
  nodes.append('circle')
    .attr('r', 28)
    .attr('fill', '#12121a')
    .attr('stroke', d => d.color)
    .attr('stroke-width', 2);

  nodes.append('text')
    .text(d => d.icon)
    .attr('text-anchor', 'middle')
    .attr('dy', '0.35em')
    .attr('fill', d => d.color)
    .attr('font-size', '16px')
    .attr('font-family', 'JetBrains Mono, monospace')
    .attr('font-weight', 600);

  // Node labels
  nodes.append('text')
    .text(d => d.label)
    .attr('text-anchor', 'middle')
    .attr('dy', '48px')
    .attr('fill', '#8a8a9a')
    .attr('font-size', '11px')
    .attr('font-family', 'Inter, sans-serif')
    .attr('font-weight', 500);

  // Animated pulse traveling along the loop
  const pulse = svg.append('circle')
    .attr('r', 6)
    .attr('fill', '#6e8efb')
    .attr('opacity', 0.9)
    .style('filter', 'drop-shadow(0 0 6px rgba(110,142,251,0.6))');

  let progress = 0;
  function animatePulse() {
    progress = (progress + 0.004) % 1;

    const totalPhases = PHASES.length;
    const segIdx = Math.floor(progress * totalPhases);
    const segProgress = (progress * totalPhases) - segIdx;
    const nextIdx = (segIdx + 1) % totalPhases;

    const a1 = (segIdx / totalPhases) * Math.PI * 2 - Math.PI / 2;
    const a2 = (nextIdx / totalPhases) * Math.PI * 2 - Math.PI / 2;

    const x = cx + Math.cos(a1) * radius + (Math.cos(a2) * radius - Math.cos(a1) * radius) * segProgress;
    const y = cy + Math.sin(a1) * radius + (Math.sin(a2) * radius - Math.sin(a1) * radius) * segProgress;

    pulse.attr('cx', x).attr('cy', y);

    // Highlight active phase
    nodes.select('circle')
      .attr('stroke-width', (d, i) => i === segIdx ? 3 : 2)
      .attr('r', (d, i) => i === segIdx ? 32 : 28);

    // Highlight corresponding card
    const cards = document.querySelectorAll('.phase-card');
    cards.forEach((card, i) => {
      card.classList.toggle('active', i === segIdx);
    });

    requestAnimationFrame(animatePulse);
  }
  animatePulse();

  // Center label
  svg.append('text')
    .attr('x', cx).attr('y', cy - 6)
    .attr('text-anchor', 'middle')
    .attr('fill', '#555566')
    .attr('font-size', '10px')
    .attr('font-family', 'Inter, sans-serif')
    .attr('letter-spacing', '0.1em')
    .text('CYCLE');

  svg.append('text')
    .attr('x', cx).attr('y', cy + 10)
    .attr('text-anchor', 'middle')
    .attr('fill', '#6e8efb')
    .attr('font-size', '10px')
    .attr('font-family', 'JetBrains Mono, monospace')
    .attr('opacity', 0.5)
    .text('t = 1..T');
}
