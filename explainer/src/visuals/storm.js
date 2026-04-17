/* ═══════════════════════════════════════════════════════════════════════
   Hero storm — Engine-driven regime particle visualization
   ═══════════════════════════════════════════════════════════════════════ */
import * as d3 from 'd3';
import { REGIMES } from '../engine/constants.js';
import { showTooltip, hideTooltip } from '../tooltip.js';

export function initStormVisual(engine) {
  const container = document.getElementById('storm-visual');
  if (!container) return;

  const width = container.clientWidth || 500;
  const height = container.clientHeight || 500;
  const cx = width / 2, cy = height / 2;

  const svg = d3.select(container).append('svg')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet');

  // Background glow
  const defs = svg.append('defs');
  const radGrad = defs.append('radialGradient').attr('id', 'storm-glow');
  radGrad.append('stop').attr('offset', '0%').attr('stop-color', '#6e8efb').attr('stop-opacity', 0.08);
  radGrad.append('stop').attr('offset', '100%').attr('stop-color', '#0a0a0f').attr('stop-opacity', 0);
  svg.append('circle').attr('cx', cx).attr('cy', cy).attr('r', Math.min(width, height) * 0.45).attr('fill', 'url(#storm-glow)');

  // Particles
  const particleCount = 25;
  const particles = [];
  REGIMES.forEach((regime, ri) => {
    const angle = (ri / REGIMES.length) * Math.PI * 2;
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        regime: regime.id, color: regime.color,
        baseAngle: angle + (Math.random() - 0.5) * 1.2,
        baseR: 100 + (Math.random() - 0.5) * 80 + Math.random() * 60,
        size: 1.5 + Math.random() * 2.5,
        speed: 0.002 + Math.random() * 0.004,
        phase: Math.random() * Math.PI * 2,
        opacity: 0.3 + Math.random() * 0.5,
        x: cx, y: cy,
      });
    }
  });

  const dots = svg.selectAll('.storm-dot').data(particles).enter()
    .append('circle').attr('class', 'storm-dot')
    .attr('r', d => d.size).attr('fill', d => d.color).attr('opacity', d => d.opacity);

  // Regime labels
  const labelG = svg.selectAll('.regime-label').data(REGIMES).enter()
    .append('g').attr('class', 'regime-label').style('cursor', 'pointer');
  labelG.append('circle').attr('r', 5).attr('fill', d => d.color).attr('opacity', 0.8);
  labelG.append('text').text(d => d.label).attr('x', 10).attr('dy', '0.35em')
    .attr('fill', d => d.color).attr('font-size', '11px').attr('font-family', 'Inter, sans-serif')
    .attr('font-weight', 500).attr('opacity', 0.7);

  // Center
  svg.append('text').attr('x', cx).attr('y', cy - 8).attr('text-anchor', 'middle')
    .attr('fill', '#fff').attr('font-size', '14px').attr('font-family', 'JetBrains Mono, monospace')
    .attr('font-weight', 500).attr('opacity', 0.6).text('r*(t)');
  const activeLabel = svg.append('text').attr('x', cx).attr('y', cy + 14).attr('text-anchor', 'middle')
    .attr('fill', '#6e8efb').attr('font-size', '10px').attr('font-family', 'Inter, sans-serif').attr('opacity', 0.5);

  // Tooltip on regime labels
  labelG.on('mouseover', (event, d) => {
    const state = engine.getState();
    if (!state) return;
    const p = state.penalties[d.id] || 0;
    const g = state.gradients[d.id] || 0;
    showTooltip(`<span class="tt-regime" style="color:${d.color}">${d.label}</span><br>` +
      `<span class="tt-label">P(t) =</span> <span class="tt-value">${p.toFixed(4)}</span><br>` +
      `<span class="tt-label">\u0394P/\u0394t =</span> <span class="tt-value">${g.toFixed(4)}</span>`, event);
  }).on('mousemove', (event) => {
    showTooltip(document.getElementById('tooltip')?.innerHTML || '', event);
  }).on('mouseout', hideTooltip);

  // Animation loop driven by engine state
  let t = 0;
  let currentActive = 'peacetime';
  let penalties = {};

  engine.subscribe(state => {
    if (!state) return;
    currentActive = state.activeRegime;
    penalties = state.penalties || {};
    activeLabel.text(currentActive);
  });

  function animate() {
    t++;
    const maxP = Math.max(...Object.values(penalties), 0.01);

    dots.each(function(d) {
      const isDominant = d.regime === currentActive;
      const regimeP = (penalties[d.regime] || 0) / maxP;
      const pull = isDominant ? 0.5 + 0.2 * regimeP : 1.0 + 0.4 * (1 - regimeP);
      const speedMult = 1 + maxP * 0.5;  // Storm intensifies with total penalty
      const angle = d.baseAngle + t * d.speed * speedMult + Math.sin(t * 0.005 + d.phase) * 0.3;
      const r = d.baseR * pull + Math.sin(t * 0.01 + d.phase) * 15;
      d.x = cx + Math.cos(angle) * r;
      d.y = cy + Math.sin(angle) * r;
    });

    dots.attr('cx', d => d.x).attr('cy', d => d.y)
      .attr('opacity', d => d.regime === currentActive ? d.opacity + 0.3 : d.opacity * 0.5);

    labelG.each(function(d, i) {
      const angle = (i / REGIMES.length) * Math.PI * 2 + t * 0.001;
      const r = d.id === currentActive ? 55 : 165;
      d3.select(this).attr('transform', `translate(${cx + Math.cos(angle) * r},${cy + Math.sin(angle) * r})`);
    });

    requestAnimationFrame(animate);
  }
  animate();
}
