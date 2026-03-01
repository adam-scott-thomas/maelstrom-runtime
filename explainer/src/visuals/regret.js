/* ═══════════════════════════════════════════════════════════════════════
   Regret & counterfactual archive — Path comparison visualization
   ═══════════════════════════════════════════════════════════════════════ */
import * as d3 from 'd3';

export function initRegretVisual() {
  const container = document.getElementById('regret-visual');
  if (!container) return;

  const width = 460;
  const height = 420;
  const margin = { top: 40, right: 30, bottom: 50, left: 50 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const svg = d3.select(container)
    .append('svg')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .style('max-width', '460px');

  const g = svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  // Simulated 12-cycle scenario data
  const cycles = 12;
  const executed = [];
  const counterfactual = [];
  const regret = [];

  // Generate data: executed follows survival-oriented path, counterfactual is "what-if"
  for (let i = 0; i < cycles; i++) {
    const stress = 0.1 + 0.6 * Math.sin(i / cycles * Math.PI);
    const exec = 0.3 + 0.2 * (1 - stress) + 0.05 * Math.sin(i * 0.8);
    const cf = 0.3 + 0.35 * (1 - stress * 0.5) + 0.1 * Math.cos(i * 0.5);
    executed.push(exec);
    counterfactual.push(cf);
    regret.push(Math.max(0, cf - exec));
  }

  const x = d3.scaleLinear().domain([1, cycles]).range([0, innerW]);
  const y = d3.scaleLinear().domain([0, 0.8]).range([innerH, 0]);

  // Grid lines
  [0.2, 0.4, 0.6].forEach(v => {
    g.append('line')
      .attr('x1', 0).attr('x2', innerW)
      .attr('y1', y(v)).attr('y2', y(v))
      .attr('stroke', '#1e1e2e')
      .attr('stroke-width', 1);
  });

  // Regret fill area
  const regretArea = d3.area()
    .x((d, i) => x(i + 1))
    .y0((d, i) => y(executed[i]))
    .y1((d, i) => y(counterfactual[i]))
    .curve(d3.curveMonotoneX);

  g.append('path')
    .datum(regret)
    .attr('d', regretArea)
    .attr('fill', '#6e8efb')
    .attr('opacity', 0.1);

  // Executed line
  const executedLine = d3.line()
    .x((d, i) => x(i + 1))
    .y(d => y(d))
    .curve(d3.curveMonotoneX);

  g.append('path')
    .datum(executed)
    .attr('d', executedLine)
    .attr('fill', 'none')
    .attr('stroke', '#ef4444')
    .attr('stroke-width', 2.5)
    .attr('opacity', 0.8);

  // Counterfactual line (dashed)
  g.append('path')
    .datum(counterfactual)
    .attr('d', executedLine)
    .attr('fill', 'none')
    .attr('stroke', '#6e8efb')
    .attr('stroke-width', 2)
    .attr('stroke-dasharray', '6,4')
    .attr('opacity', 0.7);

  // Data points
  g.selectAll('.exec-dot')
    .data(executed)
    .enter()
    .append('circle')
    .attr('cx', (d, i) => x(i + 1))
    .attr('cy', d => y(d))
    .attr('r', 3.5)
    .attr('fill', '#ef4444');

  g.selectAll('.cf-dot')
    .data(counterfactual)
    .enter()
    .append('circle')
    .attr('cx', (d, i) => x(i + 1))
    .attr('cy', d => y(d))
    .attr('r', 3)
    .attr('fill', '#6e8efb')
    .attr('opacity', 0.7);

  // Regret bars (vertical)
  g.selectAll('.regret-bar')
    .data(regret)
    .enter()
    .append('line')
    .attr('x1', (d, i) => x(i + 1))
    .attr('x2', (d, i) => x(i + 1))
    .attr('y1', (d, i) => y(executed[i]))
    .attr('y2', (d, i) => y(counterfactual[i]))
    .attr('stroke', '#6e8efb')
    .attr('stroke-width', 1)
    .attr('opacity', d => d > 0.01 ? 0.3 : 0)
    .attr('stroke-dasharray', '2,2');

  // Axes
  g.append('g')
    .attr('transform', `translate(0,${innerH})`)
    .call(d3.axisBottom(x).ticks(cycles).tickSize(0).tickFormat(d => `t=${d}`))
    .call(g => g.select('.domain').attr('stroke', '#1e1e2e'))
    .selectAll('text')
    .attr('fill', '#555566')
    .attr('font-size', '9px')
    .attr('font-family', 'JetBrains Mono, monospace');

  g.append('g')
    .call(d3.axisLeft(y).ticks(4).tickSize(0).tickFormat(d => d.toFixed(1)))
    .call(g => g.select('.domain').attr('stroke', '#1e1e2e'))
    .selectAll('text')
    .attr('fill', '#555566')
    .attr('font-size', '9px')
    .attr('font-family', 'JetBrains Mono, monospace');

  // Legend
  const legend = g.append('g').attr('transform', `translate(${innerW - 160}, -20)`);

  legend.append('line').attr('x1', 0).attr('x2', 20).attr('y1', 0).attr('y2', 0)
    .attr('stroke', '#ef4444').attr('stroke-width', 2.5);
  legend.append('text').attr('x', 25).attr('dy', '0.35em')
    .text('Executed path')
    .attr('fill', '#8a8a9a').attr('font-size', '10px').attr('font-family', 'Inter, sans-serif');

  legend.append('line').attr('x1', 0).attr('x2', 20).attr('y1', 18).attr('y2', 18)
    .attr('stroke', '#6e8efb').attr('stroke-width', 2).attr('stroke-dasharray', '6,4');
  legend.append('text').attr('x', 25).attr('y', 18).attr('dy', '0.35em')
    .text('Best counterfactual')
    .attr('fill', '#8a8a9a').attr('font-size', '10px').attr('font-family', 'Inter, sans-serif');

  legend.append('rect').attr('x', 0).attr('y', 32).attr('width', 20).attr('height', 10)
    .attr('fill', '#6e8efb').attr('opacity', 0.15);
  legend.append('text').attr('x', 25).attr('y', 37).attr('dy', '0.35em')
    .text('Regret gap')
    .attr('fill', '#8a8a9a').attr('font-size', '10px').attr('font-family', 'Inter, sans-serif');

  // Y-axis label
  svg.append('text')
    .attr('transform', `translate(14, ${margin.top + innerH / 2}) rotate(-90)`)
    .attr('text-anchor', 'middle')
    .attr('fill', '#555566')
    .attr('font-size', '10px')
    .attr('font-family', 'JetBrains Mono, monospace')
    .text('regime-weighted value');

  // X-axis label
  svg.append('text')
    .attr('x', margin.left + innerW / 2)
    .attr('y', height - 8)
    .attr('text-anchor', 'middle')
    .attr('fill', '#555566')
    .attr('font-size', '10px')
    .attr('font-family', 'JetBrains Mono, monospace')
    .text('cycle');

  // Annotation: peak regret
  const maxRegretIdx = regret.indexOf(Math.max(...regret));
  if (maxRegretIdx >= 0) {
    const ax = x(maxRegretIdx + 1);
    const ay = y(counterfactual[maxRegretIdx]) - 12;

    g.append('text')
      .attr('x', ax)
      .attr('y', ay)
      .attr('text-anchor', 'middle')
      .attr('fill', '#6e8efb')
      .attr('font-size', '9px')
      .attr('font-family', 'JetBrains Mono, monospace')
      .text(`regret=${regret[maxRegretIdx].toFixed(3)}`);
  }
}
