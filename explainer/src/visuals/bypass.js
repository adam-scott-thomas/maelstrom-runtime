/* ═══════════════════════════════════════════════════════════════════════
   Bypass collapse — Interactive path visualization
   ═══════════════════════════════════════════════════════════════════════ */
import * as d3 from 'd3';

const PHASES = ['Evaluate', 'Generate', 'Select', 'Execute', 'Reflect'];
const PHASE_COLORS = ['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#c084fc'];

const BYPASSES = {
  impulse: {
    name: 'Impulse',
    path: [0, 3, 4],          // E → X → R
    skipped: [1, 2],           // G, S
    color: '#ef4444',
    regime: 'Survival',
    benefit: 'Speed prioritized over clarity',
    cost: 'Loss of clarity and defensibility',
    desc: 'Evaluate \u2192 Execute \u2192 Reflect. Speed prioritized over clarity. The survival regime collapses deliberation to act immediately under threat.',
  },
  rumination: {
    name: 'Rumination',
    path: [0, 4],              // E → R
    skipped: [1, 2, 3],        // G, S, X
    color: '#3b82f6',
    regime: 'Epistemic',
    benefit: 'Uncertainty resolution dominates action',
    cost: 'Deadline failure, paralysis',
    desc: 'Evaluate \u2194 Reflect. Uncertainty resolution dominates action. The system loops between evaluation and reflection without ever acting.',
  },
  mania: {
    name: 'Mania',
    path: [0, 1, 3, 4],       // E → G → X → R
    skipped: [2],              // S
    color: '#22c55e',
    regime: 'Economic',
    benefit: 'Opportunity prioritized over defensibility',
    cost: 'Incoherence, hasty execution',
    desc: 'Generate \u2192 Execute. Opportunity prioritized over defensibility. Ideas become actions without selection review.',
  },
  guilt: {
    name: 'Guilt',
    path: [0, 1, 2, 4],       // E → G → S → R
    skipped: [3],              // X
    color: '#a855f7',
    regime: 'Moral',
    benefit: 'Harm minimization reshapes alternatives',
    cost: 'Paralysis, no action taken',
    desc: 'Reflect \u2192 Generate. Harm minimization reshapes alternatives. The system knows what to do but substitutes reflection for execution.',
  },
  over_learning: {
    name: 'Over-learning',
    path: [0, 1, 2, 3, 4, 1], // Full loop + back to G
    skipped: [],
    color: '#f59e0b',
    regime: 'Epistemic / Economic',
    benefit: 'Lesson formation, deeper processing',
    cost: 'Combinatorial blowup, re-churn',
    desc: 'Reflect \u2192 Generate (loop). After reflecting, the system loops back to generate new proposals \u2014 extracting lessons too aggressively.',
  },
};

export function initBypassVisual() {
  const container = document.getElementById('bypass-visual');
  const selector = document.getElementById('bypass-selector');
  const info = document.getElementById('bypass-info');
  if (!container || !selector) return;

  const width = 460;
  const height = 420;
  const nodeSpacing = 70;
  const startY = 50;
  const nodeX = width / 2;

  const svg = d3.select(container)
    .append('svg')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet')
    .style('max-width', '460px');

  // Node positions (vertical layout)
  const nodePositions = PHASES.map((p, i) => ({
    x: nodeX,
    y: startY + i * nodeSpacing,
  }));

  // Canonical path (grey)
  const canonicalG = svg.append('g').attr('class', 'canonical');

  for (let i = 0; i < PHASES.length - 1; i++) {
    canonicalG.append('line')
      .attr('x1', nodePositions[i].x).attr('y1', nodePositions[i].y + 22)
      .attr('x2', nodePositions[i + 1].x).attr('y2', nodePositions[i + 1].y - 22)
      .attr('stroke', '#1e1e2e')
      .attr('stroke-width', 2);
  }
  // Reflect -> Evaluate loop-back (left side)
  canonicalG.append('path')
    .attr('d', `M ${nodePositions[4].x - 22} ${nodePositions[4].y}
                Q ${nodeX - 100} ${(nodePositions[4].y + nodePositions[0].y) / 2}
                  ${nodePositions[0].x - 22} ${nodePositions[0].y}`)
    .attr('stroke', '#1e1e2e')
    .attr('stroke-width', 2)
    .attr('fill', 'none')
    .attr('stroke-dasharray', '4,4');

  // Bypass path (animated)
  const bypassPath = svg.append('path')
    .attr('fill', 'none')
    .attr('stroke-width', 3)
    .attr('opacity', 0);

  // Node circles (on top)
  const nodeG = svg.selectAll('.bp-node')
    .data(PHASES)
    .enter()
    .append('g')
    .attr('transform', (d, i) => `translate(${nodePositions[i].x},${nodePositions[i].y})`);

  const nodeCircles = nodeG.append('circle')
    .attr('r', 22)
    .attr('fill', '#12121a')
    .attr('stroke', (d, i) => PHASE_COLORS[i])
    .attr('stroke-width', 2);

  nodeG.append('text')
    .text(d => d)
    .attr('text-anchor', 'middle')
    .attr('dy', '0.35em')
    .attr('fill', (d, i) => PHASE_COLORS[i])
    .attr('font-size', '11px')
    .attr('font-family', 'Inter, sans-serif')
    .attr('font-weight', 600);

  // "SKIPPED" overlays
  const skipLabels = nodeG.append('text')
    .attr('x', 32)
    .attr('dy', '0.35em')
    .attr('fill', '#ef4444')
    .attr('font-size', '9px')
    .attr('font-family', 'JetBrains Mono, monospace')
    .attr('font-weight', 600)
    .attr('opacity', 0)
    .text('SKIPPED');

  function showBypass(key) {
    const bp = BYPASSES[key];
    if (!bp) return;

    // Update info panel
    info.innerHTML = `
      <div><strong>${bp.name}</strong> — <span style="color:${bp.color}">${bp.regime}</span></div>
      <div class="bypass-path">${bp.path.map(i => PHASES[i]).join(' \u2192 ')}</div>
      <p>${bp.desc}</p>
      <div class="bypass-meta">
        <span>Benefit:</span><span>${bp.benefit}</span>
        <span>Cost:</span><span>${bp.cost}</span>
      </div>
    `;

    // Highlight skip labels
    skipLabels.attr('opacity', (d, i) => bp.skipped.includes(i) ? 0.8 : 0);

    // Dim skipped nodes
    nodeCircles
      .transition().duration(300)
      .attr('opacity', (d, i) => bp.skipped.includes(i) ? 0.2 : 1)
      .attr('stroke-width', (d, i) => bp.skipped.includes(i) ? 1 : 2);

    // Build bypass path
    const points = bp.path.map(i => nodePositions[i]);
    let pathD;
    if (bp.path.length === 2) {
      // Straight arc for rumination (E → R)
      const midX = nodeX + 80;
      pathD = `M ${points[0].x + 22} ${points[0].y}
               Q ${midX} ${(points[0].y + points[1].y) / 2}
                 ${points[1].x + 22} ${points[1].y}`;
    } else if (key === 'over_learning') {
      // Full path + loopback curve
      const line = points.slice(0, 5).map((p, i) =>
        i === 0 ? `M ${p.x + 22} ${p.y}` : `L ${p.x + 22} ${p.y}`
      ).join(' ');
      const lastPt = points[4]; // Reflect
      const loopPt = points[5]; // back to Generate
      pathD = `${line} Q ${nodeX + 110} ${(lastPt.y + loopPt.y) / 2} ${loopPt.x + 22} ${loopPt.y}`;
    } else {
      // Arc path bypassing skipped nodes
      const offsetX = 70;
      let d = `M ${points[0].x + 22} ${points[0].y}`;
      for (let i = 1; i < points.length; i++) {
        const prev = points[i - 1];
        const curr = points[i];
        // Check if this segment skips a node
        const prevIdx = bp.path[i - 1];
        const currIdx = bp.path[i];
        const skip = currIdx - prevIdx > 1;
        if (skip) {
          d += ` Q ${nodeX + offsetX} ${(prev.y + curr.y) / 2} ${curr.x + 22} ${curr.y}`;
        } else {
          d += ` L ${curr.x + 22} ${curr.y}`;
        }
      }
      pathD = d;
    }

    // Animate the bypass path drawing
    bypassPath
      .attr('d', pathD)
      .attr('stroke', bp.color)
      .attr('opacity', 0.8)
      .each(function() {
        const len = this.getTotalLength();
        d3.select(this)
          .attr('stroke-dasharray', `${len} ${len}`)
          .attr('stroke-dashoffset', len)
          .transition().duration(600).ease(d3.easeCubicOut)
          .attr('stroke-dashoffset', 0);
      });
  }

  // Button handlers
  selector.querySelectorAll('.bypass-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      selector.querySelectorAll('.bypass-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      showBypass(btn.dataset.bypass);
    });
  });

  // Initialize with impulse
  showBypass('impulse');
}
