/* ═══════════════════════════════════════════════════════════════════════
   Hero storm visualization — Competing regime particles
   ═══════════════════════════════════════════════════════════════════════ */
import * as d3 from 'd3';

const REGIMES = [
  { id: 'survival',  color: '#ef4444', label: 'Survival' },
  { id: 'legal',     color: '#f59e0b', label: 'Legal' },
  { id: 'moral',     color: '#a855f7', label: 'Moral' },
  { id: 'economic',  color: '#22c55e', label: 'Economic' },
  { id: 'epistemic', color: '#3b82f6', label: 'Epistemic' },
  { id: 'peacetime', color: '#6b7280', label: 'Peacetime' },
];

export function initStormVisual() {
  const container = document.getElementById('storm-visual');
  if (!container) return;

  const width = container.clientWidth || 500;
  const height = container.clientHeight || 500;
  const cx = width / 2;
  const cy = height / 2;

  const svg = d3.select(container)
    .append('svg')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet');

  // Background glow
  const defs = svg.append('defs');
  const radGrad = defs.append('radialGradient').attr('id', 'storm-glow');
  radGrad.append('stop').attr('offset', '0%').attr('stop-color', '#6e8efb').attr('stop-opacity', 0.08);
  radGrad.append('stop').attr('offset', '100%').attr('stop-color', '#0a0a0f').attr('stop-opacity', 0);

  svg.append('circle')
    .attr('cx', cx).attr('cy', cy).attr('r', Math.min(width, height) * 0.45)
    .attr('fill', 'url(#storm-glow)');

  // Create particles per regime
  const particleCount = 30;
  const particles = [];

  REGIMES.forEach((regime, ri) => {
    const angle = (ri / REGIMES.length) * Math.PI * 2;
    const orbitR = 100 + Math.random() * 60;
    for (let i = 0; i < particleCount; i++) {
      const a = angle + (Math.random() - 0.5) * 1.2;
      const r = orbitR + (Math.random() - 0.5) * 80;
      particles.push({
        regime: regime.id,
        color: regime.color,
        x: cx + Math.cos(a) * r,
        y: cy + Math.sin(a) * r,
        baseAngle: a,
        baseR: r,
        size: 1.5 + Math.random() * 2.5,
        speed: 0.002 + Math.random() * 0.004,
        phase: Math.random() * Math.PI * 2,
        opacity: 0.3 + Math.random() * 0.5,
      });
    }
  });

  // Draw particles
  const dots = svg.selectAll('.storm-dot')
    .data(particles)
    .enter()
    .append('circle')
    .attr('class', 'storm-dot')
    .attr('r', d => d.size)
    .attr('fill', d => d.color)
    .attr('opacity', d => d.opacity);

  // Regime labels (orbiting)
  const labelG = svg.selectAll('.regime-label')
    .data(REGIMES)
    .enter()
    .append('g')
    .attr('class', 'regime-label');

  labelG.append('circle')
    .attr('r', 5)
    .attr('fill', d => d.color)
    .attr('opacity', 0.8);

  labelG.append('text')
    .text(d => d.label)
    .attr('x', 10)
    .attr('dy', '0.35em')
    .attr('fill', d => d.color)
    .attr('font-size', '11px')
    .attr('font-family', 'Inter, sans-serif')
    .attr('font-weight', 500)
    .attr('opacity', 0.7);

  // Center text
  svg.append('text')
    .attr('x', cx).attr('y', cy - 8)
    .attr('text-anchor', 'middle')
    .attr('fill', '#fff')
    .attr('font-size', '14px')
    .attr('font-family', 'JetBrains Mono, monospace')
    .attr('font-weight', 500)
    .attr('opacity', 0.6)
    .text('r*(t)');

  svg.append('text')
    .attr('x', cx).attr('y', cy + 14)
    .attr('text-anchor', 'middle')
    .attr('fill', '#6e8efb')
    .attr('font-size', '10px')
    .attr('font-family', 'Inter, sans-serif')
    .attr('opacity', 0.4)
    .text('active regime');

  // Animation
  let t = 0;
  function animate() {
    t += 1;

    // Dominant regime shifts over time
    const dominantIdx = Math.floor((t / 300) % REGIMES.length);
    const dominant = REGIMES[dominantIdx].id;

    dots.each(function(d) {
      const isDominant = d.regime === dominant;
      const pull = isDominant ? 0.7 : 1.3;
      const angle = d.baseAngle + t * d.speed + Math.sin(t * 0.005 + d.phase) * 0.3;
      const r = d.baseR * pull + Math.sin(t * 0.01 + d.phase) * 15;

      d.x = cx + Math.cos(angle) * r;
      d.y = cy + Math.sin(angle) * r;
    });

    dots.attr('cx', d => d.x).attr('cy', d => d.y)
      .attr('opacity', d => d.regime === dominant ? d.opacity + 0.3 : d.opacity * 0.6);

    // Update label positions
    labelG.each(function(d, i) {
      const angle = (i / REGIMES.length) * Math.PI * 2 + t * 0.001;
      const r = d.id === dominant ? 60 : 160;
      const x = cx + Math.cos(angle) * r;
      const y = cy + Math.sin(angle) * r;
      d3.select(this).attr('transform', `translate(${x},${y})`);
    });

    requestAnimationFrame(animate);
  }
  animate();
}
