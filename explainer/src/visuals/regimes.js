/* ═══════════════════════════════════════════════════════════════════════
   Regime competition — Engine-driven gradient bars with tooltips
   ═══════════════════════════════════════════════════════════════════════ */
import * as d3 from 'd3';
import { REGIMES } from '../engine/constants.js';
import { showTooltip, hideTooltip } from '../tooltip.js';

export function initRegimeVisual(engine) {
  const container = document.getElementById('regime-visual');
  if (!container) return;

  const width = 460, height = 380;
  const margin = { top: 30, right: 30, bottom: 40, left: 90 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const svg = d3.select(container).append('svg')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet').style('max-width', '100%');

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  const y = d3.scaleBand().domain(REGIMES.map(r => r.id)).range([0, innerH]).padding(0.25);
  const x = d3.scaleLinear().domain([0, 1]).range([0, innerW]);

  // Y labels
  g.selectAll('.regime-label').data(REGIMES).enter()
    .append('text').attr('x', -8).attr('y', d => y(d.id) + y.bandwidth() / 2)
    .attr('dy', '0.35em').attr('text-anchor', 'end')
    .attr('fill', d => d.color).attr('font-size', '12px')
    .attr('font-family', 'Inter, sans-serif').attr('font-weight', 500)
    .text(d => d.label);

  // Background bars
  g.selectAll('.bar-bg').data(REGIMES).enter()
    .append('rect').attr('x', 0).attr('y', d => y(d.id))
    .attr('width', innerW).attr('height', y.bandwidth())
    .attr('fill', '#12121a').attr('rx', 4);

  // Value bars
  const bars = g.selectAll('.bar-val').data(REGIMES).enter()
    .append('rect').attr('class', 'bar-val')
    .attr('x', 0).attr('y', d => y(d.id))
    .attr('width', 0).attr('height', y.bandwidth())
    .attr('fill', d => d.color).attr('opacity', 0.4).attr('rx', 4)
    .style('cursor', 'pointer');

  // Gradient labels
  const gradLabels = g.selectAll('.grad-label').data(REGIMES).enter()
    .append('text').attr('class', 'grad-label')
    .attr('y', d => y(d.id) + y.bandwidth() / 2).attr('dy', '0.35em')
    .attr('fill', '#e8e6e3').attr('font-size', '11px')
    .attr('font-family', 'JetBrains Mono, monospace').attr('opacity', 0.7);

  // Active marker
  const activeMarker = g.append('text')
    .attr('font-size', '11px').attr('fill', '#6e8efb')
    .attr('font-family', 'JetBrains Mono, monospace').attr('font-weight', 600)
    .text('r*(t) \u25C0');

  // Title
  svg.append('text').attr('x', margin.left).attr('y', 18)
    .attr('fill', '#555566').attr('font-size', '10px')
    .attr('font-family', 'JetBrains Mono, monospace').attr('letter-spacing', '0.08em')
    .text('\u0394P\u1D63/\u0394t — penalty gradient');

  // Tooltip on bars
  bars.on('mouseover', (event, d) => {
    const state = engine.getState();
    if (!state) return;
    const p = state.penalties[d.id] || 0;
    const grad = state.gradients[d.id] || 0;
    const active = state.activeRegime === d.id;
    showTooltip(
      `<span class="tt-regime" style="color:${d.color}">${d.label}</span>${active ? ' (active)' : ''}<br>` +
      `<div class="tt-row"><span class="tt-label">P(t)</span><span class="tt-value">${p.toFixed(4)}</span></div>` +
      `<div class="tt-row"><span class="tt-label">\u0394P/\u0394t</span><span class="tt-value">${grad >= 0 ? '+' : ''}${grad.toFixed(4)}</span></div>` +
      `<div class="tt-row"><span class="tt-label">${d.desc}</span></div>`,
      event
    );
  }).on('mousemove', (event) => {
    const el = document.getElementById('tooltip');
    if (el) showTooltip(el.innerHTML, event);
  }).on('mouseout', hideTooltip);

  // Subscribe to engine
  engine.subscribe(state => {
    if (!state || !state.gradients) return;

    const grads = state.gradients;
    const maxVal = Math.max(...Object.values(grads).map(Math.abs), 0.001);

    bars.data(REGIMES)
      .transition().duration(120).ease(d3.easeLinear)
      .attr('width', d => x(Math.max(0, grads[d.id] || 0) / maxVal))
      .attr('opacity', d => d.id === state.activeRegime ? 0.9 : 0.4);

    gradLabels.data(REGIMES)
      .attr('x', d => x(Math.max(0, grads[d.id] || 0) / maxVal) + 6)
      .text(d => {
        const v = grads[d.id] || 0;
        return (v >= 0 ? '+' : '') + v.toFixed(4);
      });

    activeMarker
      .attr('x', innerW + 5)
      .attr('y', y(state.activeRegime) + y.bandwidth() / 2)
      .attr('dy', '0.35em');
  });

  // Build legend
  const legend = document.getElementById('regime-legend');
  if (legend) {
    legend.innerHTML = '';
    REGIMES.forEach(r => {
      const item = document.createElement('div');
      item.className = 'regime-legend-item';
      item.innerHTML = `<span class="regime-dot" style="background:${r.color}"></span>${r.label}: ${r.desc}`;
      legend.appendChild(item);
    });
  }
}
