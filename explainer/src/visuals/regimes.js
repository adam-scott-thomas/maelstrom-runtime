/* ═══════════════════════════════════════════════════════════════════════
   Regime competition — Animated gradient bars
   ═══════════════════════════════════════════════════════════════════════ */
import * as d3 from 'd3';

const REGIMES = [
  { id: 'survival',  color: '#ef4444', label: 'Survival',  desc: 'Minimize termination risk' },
  { id: 'legal',     color: '#f59e0b', label: 'Legal',     desc: 'Minimize liability exposure' },
  { id: 'moral',     color: '#a855f7', label: 'Moral',     desc: 'Minimize unjustified harm' },
  { id: 'economic',  color: '#22c55e', label: 'Economic',  desc: 'Minimize opportunity cost' },
  { id: 'epistemic', color: '#3b82f6', label: 'Epistemic', desc: 'Minimize uncertainty' },
  { id: 'peacetime', color: '#6b7280', label: 'Peacetime', desc: 'Minimize institutional decay' },
];

export function initRegimeVisual() {
  const container = document.getElementById('regime-visual');
  if (!container) return;

  const width = 460;
  const height = 380;
  const margin = { top: 30, right: 30, bottom: 40, left: 90 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const svg = d3.select(container)
    .append('svg')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .style('max-width', '460px');

  const g = svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  const y = d3.scaleBand()
    .domain(REGIMES.map(r => r.id))
    .range([0, innerH])
    .padding(0.25);

  const x = d3.scaleLinear()
    .domain([0, 1])
    .range([0, innerW]);

  // Y axis labels
  g.selectAll('.regime-label')
    .data(REGIMES)
    .enter()
    .append('text')
    .attr('x', -8)
    .attr('y', d => y(d.id) + y.bandwidth() / 2)
    .attr('dy', '0.35em')
    .attr('text-anchor', 'end')
    .attr('fill', d => d.color)
    .attr('font-size', '12px')
    .attr('font-family', 'Inter, sans-serif')
    .attr('font-weight', 500)
    .text(d => d.label);

  // Background bars
  g.selectAll('.bar-bg')
    .data(REGIMES)
    .enter()
    .append('rect')
    .attr('x', 0)
    .attr('y', d => y(d.id))
    .attr('width', innerW)
    .attr('height', y.bandwidth())
    .attr('fill', '#12121a')
    .attr('rx', 4);

  // Value bars
  const bars = g.selectAll('.bar-val')
    .data(REGIMES)
    .enter()
    .append('rect')
    .attr('class', 'bar-val')
    .attr('x', 0)
    .attr('y', d => y(d.id))
    .attr('width', 0)
    .attr('height', y.bandwidth())
    .attr('fill', d => d.color)
    .attr('opacity', 0.7)
    .attr('rx', 4);

  // Gradient labels
  const gradLabels = g.selectAll('.grad-label')
    .data(REGIMES)
    .enter()
    .append('text')
    .attr('class', 'grad-label')
    .attr('y', d => y(d.id) + y.bandwidth() / 2)
    .attr('dy', '0.35em')
    .attr('fill', '#e8e6e3')
    .attr('font-size', '11px')
    .attr('font-family', 'JetBrains Mono, monospace')
    .attr('opacity', 0.7);

  // Active regime indicator
  const activeMarker = g.append('text')
    .attr('font-size', '11px')
    .attr('fill', '#6e8efb')
    .attr('font-family', 'JetBrains Mono, monospace')
    .attr('font-weight', 600)
    .text('r*(t) \u25C0');

  // Title
  svg.append('text')
    .attr('x', margin.left)
    .attr('y', 18)
    .attr('fill', '#555566')
    .attr('font-size', '10px')
    .attr('font-family', 'JetBrains Mono, monospace')
    .attr('letter-spacing', '0.08em')
    .text('\u0394P\u1D63/\u0394t — penalty gradient (simulated)');

  // Simulate a stress ramp scenario
  let tick = 0;
  function simulate() {
    tick += 1;
    const t = tick * 0.015;

    // Simulate gradients that shift over time
    const stress = 0.15 + 0.35 * Math.sin(t * 0.5) + 0.15 * Math.sin(t * 1.3);
    const threat = Math.max(0, Math.sin(t * 0.3 - 1) * 0.5 + 0.1);
    const moral  = Math.max(0, Math.sin(t * 0.2 + 2) * 0.3);

    const grads = {
      survival:  Math.max(0, threat * 0.8 + stress * 0.3),
      legal:     Math.max(0, stress * 0.15 + moral * 0.1),
      moral:     Math.max(0, moral * 0.6),
      economic:  Math.max(0, (1 - stress) * 0.25 + Math.sin(t * 0.7) * 0.1),
      epistemic: Math.max(0, stress * 0.2 + Math.sin(t * 0.4 + 1) * 0.15),
      peacetime: Math.max(0, (1 - stress) * 0.3 - threat * 0.2),
    };

    // Normalize to [0, 1] for display
    const maxVal = Math.max(...Object.values(grads), 0.01);

    const active = Object.entries(grads).reduce((a, b) => a[1] > b[1] ? a : b)[0];

    bars.data(REGIMES)
      .transition().duration(80).ease(d3.easeLinear)
      .attr('width', d => x(grads[d.id] / maxVal))
      .attr('opacity', d => d.id === active ? 0.9 : 0.4);

    gradLabels.data(REGIMES)
      .attr('x', d => x(grads[d.id] / maxVal) + 6)
      .text(d => (grads[d.id]).toFixed(3));

    activeMarker
      .attr('x', innerW + 5)
      .attr('y', y(active) + y.bandwidth() / 2)
      .attr('dy', '0.35em');

    requestAnimationFrame(simulate);
  }
  simulate();

  // Build legend
  const legend = document.getElementById('regime-legend');
  if (legend) {
    REGIMES.forEach(r => {
      const item = document.createElement('div');
      item.className = 'regime-legend-item';
      item.innerHTML = `<span class="regime-dot" style="background:${r.color}"></span>${r.label}: ${r.desc}`;
      legend.appendChild(item);
    });
  }
}
