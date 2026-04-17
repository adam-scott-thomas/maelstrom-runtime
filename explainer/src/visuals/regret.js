/* ═══════════════════════════════════════════════════════════════════════
   Regret — Engine-driven with hover crosshair
   ═══════════════════════════════════════════════════════════════════════ */
import * as d3 from 'd3';
import { showTooltip, hideTooltip } from '../tooltip.js';

export function initRegretVisual(engine) {
  const container = document.getElementById('regret-visual');
  if (!container) return;

  const width = 460, height = 420;
  const margin = { top: 40, right: 30, bottom: 50, left: 50 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const svg = d3.select(container).append('svg')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet').style('max-width', '100%');

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);

  // Scales (will be updated)
  const x = d3.scaleLinear().range([0, innerW]);
  const y = d3.scaleLinear().domain([0, 0.8]).range([innerH, 0]);

  // Grid
  [0.2, 0.4, 0.6].forEach(v => {
    g.append('line').attr('x1', 0).attr('x2', innerW)
      .attr('y1', y(v)).attr('y2', y(v)).attr('stroke', '#1e1e2e');
  });

  // Regret fill
  const regretArea = g.append('path').attr('fill', '#6e8efb').attr('opacity', 0.1);

  // Lines
  const executedLine = g.append('path').attr('fill', 'none').attr('stroke', '#ef4444')
    .attr('stroke-width', 2.5).attr('opacity', 0.8);
  const counterfactualLine = g.append('path').attr('fill', 'none').attr('stroke', '#6e8efb')
    .attr('stroke-width', 2).attr('stroke-dasharray', '6,4').attr('opacity', 0.7);

  // Dots
  const execDotsG = g.append('g');
  const cfDotsG = g.append('g');

  // Crosshair
  const crosshairLine = g.append('line').attr('y1', 0).attr('y2', innerH)
    .attr('stroke', '#555566').attr('stroke-width', 1).attr('stroke-dasharray', '3,3').attr('opacity', 0);

  // Hover overlay
  const overlay = g.append('rect').attr('width', innerW).attr('height', innerH)
    .attr('fill', 'transparent').style('cursor', 'crosshair');

  // Axes
  const xAxisG = g.append('g').attr('transform', `translate(0,${innerH})`);
  const yAxisG = g.append('g');

  // Legend
  const legend = g.append('g').attr('transform', `translate(${innerW - 170}, -20)`);
  legend.append('line').attr('x1', 0).attr('x2', 20).attr('y1', 0).attr('y2', 0)
    .attr('stroke', '#ef4444').attr('stroke-width', 2.5);
  legend.append('text').attr('x', 25).attr('dy', '0.35em').text('Executed path')
    .attr('fill', '#8a8a9a').attr('font-size', '10px').attr('font-family', 'Inter, sans-serif');
  legend.append('line').attr('x1', 0).attr('x2', 20).attr('y1', 18).attr('y2', 18)
    .attr('stroke', '#6e8efb').attr('stroke-width', 2).attr('stroke-dasharray', '6,4');
  legend.append('text').attr('x', 25).attr('y', 18).attr('dy', '0.35em').text('Best counterfactual')
    .attr('fill', '#8a8a9a').attr('font-size', '10px').attr('font-family', 'Inter, sans-serif');
  legend.append('rect').attr('x', 0).attr('y', 32).attr('width', 20).attr('height', 10)
    .attr('fill', '#6e8efb').attr('opacity', 0.15);
  legend.append('text').attr('x', 25).attr('y', 37).attr('dy', '0.35em').text('Regret gap')
    .attr('fill', '#8a8a9a').attr('font-size', '10px').attr('font-family', 'Inter, sans-serif');

  // Axis labels
  svg.append('text')
    .attr('transform', `translate(14, ${margin.top + innerH / 2}) rotate(-90)`)
    .attr('text-anchor', 'middle').attr('fill', '#555566').attr('font-size', '10px')
    .attr('font-family', 'JetBrains Mono, monospace').text('regime-weighted value');
  svg.append('text')
    .attr('x', margin.left + innerW / 2).attr('y', height - 8)
    .attr('text-anchor', 'middle').attr('fill', '#555566').attr('font-size', '10px')
    .attr('font-family', 'JetBrains Mono, monospace').text('cycle');

  let traceData = [];

  // Hover handler
  overlay.on('mousemove', (event) => {
    if (traceData.length === 0) return;
    const [mx] = d3.pointer(event);
    const t = Math.round(x.invert(mx));
    const idx = t - 1;
    if (idx < 0 || idx >= traceData.length) return;
    const d = traceData[idx];

    crosshairLine.attr('x1', x(t)).attr('x2', x(t)).attr('opacity', 0.6);

    const regimeColors = {
      survival: '#ef4444', legal: '#f59e0b', moral: '#a855f7',
      economic: '#22c55e', epistemic: '#3b82f6', peacetime: '#6b7280',
    };
    showTooltip(
      `<strong>Cycle ${t}</strong><br>` +
      `<div class="tt-row"><span class="tt-label">Regime:</span><span class="tt-regime" style="color:${regimeColors[d.activeRegime] || '#fff'}">${d.activeRegime}</span></div>` +
      `<div class="tt-row"><span class="tt-label">Executed:</span><span class="tt-value">${d.executedValue.toFixed(3)}</span></div>` +
      `<div class="tt-row"><span class="tt-label">Best alt:</span><span class="tt-value">${d.counterfactualBest.toFixed(3)}</span></div>` +
      `<div class="tt-row"><span class="tt-label">Regret:</span><span class="tt-value">${d.regret.toFixed(3)}</span></div>` +
      (d.activatedBypass ? `<div class="tt-row"><span class="tt-label">Bypass:</span><span style="color:#ef4444">${d.activatedBypass}</span></div>` : ''),
      event
    );
  }).on('mouseout', () => {
    crosshairLine.attr('opacity', 0);
    hideTooltip();
  });

  // Subscribe
  engine.subscribe(state => {
    if (!state) return;
    const trace = engine.getFullTrace();
    if (!trace || trace.length === 0) return;
    traceData = trace;

    const cycles = trace.length;
    x.domain([1, cycles]);

    const executed = trace.map(d => d.executedValue);
    const cf = trace.map(d => d.counterfactualBest);
    const maxVal = Math.max(...executed, ...cf, 0.5);
    y.domain([0, Math.ceil(maxVal * 10) / 10]);

    // Lines
    const lineGen = d3.line().x((d, i) => x(i + 1)).y(d => y(d)).curve(d3.curveMonotoneX);
    executedLine.attr('d', lineGen(executed));
    counterfactualLine.attr('d', lineGen(cf));

    // Area
    const areaGen = d3.area()
      .x((d, i) => x(i + 1))
      .y0((d, i) => y(executed[i]))
      .y1((d, i) => y(cf[i]))
      .curve(d3.curveMonotoneX);
    regretArea.attr('d', areaGen(cf));

    // Dots
    execDotsG.selectAll('circle').data(executed).join('circle')
      .attr('cx', (d, i) => x(i + 1)).attr('cy', d => y(d))
      .attr('r', 3.5).attr('fill', '#ef4444');
    cfDotsG.selectAll('circle').data(cf).join('circle')
      .attr('cx', (d, i) => x(i + 1)).attr('cy', d => y(d))
      .attr('r', 3).attr('fill', '#6e8efb').attr('opacity', 0.7);

    // Axes
    xAxisG.call(d3.axisBottom(x).ticks(cycles).tickSize(0).tickFormat(d => `t=${d}`))
      .call(g => g.select('.domain').attr('stroke', '#1e1e2e'))
      .selectAll('text').attr('fill', '#555566').attr('font-size', '9px').attr('font-family', 'JetBrains Mono, monospace');
    yAxisG.call(d3.axisLeft(y).ticks(4).tickSize(0).tickFormat(d => d.toFixed(1)))
      .call(g => g.select('.domain').attr('stroke', '#1e1e2e'))
      .selectAll('text').attr('fill', '#555566').attr('font-size', '9px').attr('font-family', 'JetBrains Mono, monospace');
  });
}
