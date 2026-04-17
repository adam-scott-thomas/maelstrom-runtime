/* ═══════════════════════════════════════════════════════════════════════
   Bypass dynamics — Engine-driven eligibility + path visualization
   ═══════════════════════════════════════════════════════════════════════ */
import * as d3 from 'd3';
import { BYPASSES, PHASES } from '../engine/constants.js';
import { showTooltip, hideTooltip } from '../tooltip.js';

const PHASE_LABELS = ['Evaluate', 'Generate', 'Select', 'Execute', 'Reflect'];
const PHASE_COLORS = ['#60a5fa', '#34d399', '#fbbf24', '#f87171', '#c084fc'];

function phaseIndex(name) { return PHASES.indexOf(name); }

export function initBypassVisual(engine) {
  const container = document.getElementById('bypass-visual');
  const selector = document.getElementById('bypass-selector');
  const info = document.getElementById('bypass-info');
  if (!container || !selector) return;

  const width = 460, height = 420, nodeX = width / 2, startY = 50, nodeSpacing = 70;

  const svg = d3.select(container).append('svg')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .attr('preserveAspectRatio', 'xMidYMid meet').style('max-width', '100%');

  const nodePositions = PHASE_LABELS.map((_, i) => ({ x: nodeX, y: startY + i * nodeSpacing }));

  // Canonical path (grey)
  for (let i = 0; i < PHASE_LABELS.length - 1; i++) {
    svg.append('line')
      .attr('x1', nodePositions[i].x).attr('y1', nodePositions[i].y + 22)
      .attr('x2', nodePositions[i + 1].x).attr('y2', nodePositions[i + 1].y - 22)
      .attr('stroke', '#1e1e2e').attr('stroke-width', 2);
  }
  // Loop-back
  svg.append('path')
    .attr('d', `M ${nodePositions[4].x - 22} ${nodePositions[4].y} Q ${nodeX - 100} ${(nodePositions[4].y + nodePositions[0].y) / 2} ${nodePositions[0].x - 22} ${nodePositions[0].y}`)
    .attr('stroke', '#1e1e2e').attr('stroke-width', 2).attr('fill', 'none').attr('stroke-dasharray', '4,4');

  // Bypass path
  const bypassPath = svg.append('path').attr('fill', 'none').attr('stroke-width', 3).attr('opacity', 0);

  // Nodes
  const nodeG = svg.selectAll('.bp-node').data(PHASE_LABELS).enter()
    .append('g').attr('transform', (d, i) => `translate(${nodePositions[i].x},${nodePositions[i].y})`);

  const nodeCircles = nodeG.append('circle').attr('r', 22)
    .attr('fill', '#12121a').attr('stroke', (d, i) => PHASE_COLORS[i]).attr('stroke-width', 2);

  nodeG.append('text').text(d => d).attr('text-anchor', 'middle').attr('dy', '0.35em')
    .attr('fill', (d, i) => PHASE_COLORS[i]).attr('font-size', '11px')
    .attr('font-family', 'Inter, sans-serif').attr('font-weight', 600);

  const skipLabels = nodeG.append('text').attr('x', 32).attr('dy', '0.35em')
    .attr('fill', '#ef4444').attr('font-size', '9px')
    .attr('font-family', 'JetBrains Mono, monospace').attr('font-weight', 600).attr('opacity', 0).text('SKIPPED');

  let currentBypass = 'impulse';

  // Rebuild buttons with eligibility badges
  function rebuildButtons(eligibility) {
    selector.innerHTML = '';
    for (const bp of BYPASSES) {
      const btn = document.createElement('button');
      btn.className = 'bypass-btn' + (bp.name === currentBypass ? ' active' : '');
      btn.dataset.bypass = bp.name;

      const elig = eligibility?.[bp.name];
      const isEligible = elig?.eligible;
      if (elig && !isEligible) btn.classList.add('locked');

      btn.innerHTML = `${bp.label} <span class="badge ${isEligible ? 'eligible' : 'ineligible'}"></span>`;

      btn.addEventListener('click', () => {
        currentBypass = bp.name;
        showBypass(bp.name, eligibility);
        selector.querySelectorAll('.bypass-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });

      // Tooltip on ineligible
      if (elig && !isEligible) {
        btn.addEventListener('mouseover', (event) => {
          let reason = '';
          if (!elig.regimeOk) reason = `Requires ${bp.eligibleRegimes.join('/')} regime (current: ${elig.regime})`;
          else if (!elig.exceedsBudget) reason = `Intensity ${elig.intensity.toFixed(2)} < budget ${elig.budget.toFixed(2)}`;
          else if (!elig.transitionAdmissible) reason = `Bypass transition ${bp.sourcePhase}\u2192${bp.targetPhase} inadmissible`;
          showTooltip(`<span style="color:#ef4444">Ineligible</span><br>${reason}`, event);
        });
        btn.addEventListener('mouseout', hideTooltip);
      }

      selector.appendChild(btn);
    }
  }

  function showBypass(key, eligibility) {
    const bp = BYPASSES.find(b => b.name === key);
    if (!bp) return;

    const elig = eligibility?.[key];
    const pathIndices = bp.collapsedPath.map(p => phaseIndex(p));
    const skippedIndices = PHASES.filter(p => !bp.collapsedPath.includes(p)).map(p => phaseIndex(p));

    // Info panel
    let html = `<div><strong>${bp.label}</strong> — <span style="color:${bp.color}">${bp.eligibleRegimes.join(', ')}</span></div>`;
    html += `<div class="bypass-path">${bp.collapsedPath.map(p => PHASE_LABELS[phaseIndex(p)]).join(' \u2192 ')}</div>`;
    if (elig) {
      html += `<div class="bypass-meta">`;
      html += `<span>Intensity:</span><span>${elig.intensity.toFixed(3)}</span>`;
      html += `<span>Budget:</span><span>${elig.budget.toFixed(2)}</span>`;
      html += `<span>Penalty saving:</span><span>${elig.penaltySaving.toFixed(3)}</span>`;
      html += `<span>Eligible:</span><span style="color:${elig.eligible ? '#22c55e' : '#ef4444'}">${elig.eligible ? 'YES' : 'NO'}</span>`;
      html += `</div>`;
    }
    html += `<p style="margin-top:0.5rem">${bp.benefit}. ${bp.cost}.</p>`;
    if (info) info.innerHTML = html;

    // Skip labels
    skipLabels.attr('opacity', (d, i) => skippedIndices.includes(i) ? 0.8 : 0);
    nodeCircles.transition().duration(300)
      .attr('opacity', (d, i) => skippedIndices.includes(i) ? 0.2 : 1)
      .attr('stroke-dasharray', (d, i) => skippedIndices.includes(i) ? '4,4' : 'none');

    // Build bypass path
    const points = pathIndices.map(i => nodePositions[i]);
    let pathD;
    if (points.length === 2) {
      pathD = `M ${points[0].x + 22} ${points[0].y} Q ${nodeX + 80} ${(points[0].y + points[1].y) / 2} ${points[1].x + 22} ${points[1].y}`;
    } else if (key === 'over_learning') {
      const line = points.slice(0, 5).map((p, i) => i === 0 ? `M ${p.x + 22} ${p.y}` : `L ${p.x + 22} ${p.y}`).join(' ');
      pathD = `${line} Q ${nodeX + 110} ${(points[4].y + points[5].y) / 2} ${points[5].x + 22} ${points[5].y}`;
    } else {
      let d = `M ${points[0].x + 22} ${points[0].y}`;
      for (let i = 1; i < points.length; i++) {
        const prevIdx = pathIndices[i - 1], currIdx = pathIndices[i];
        if (currIdx - prevIdx > 1) {
          d += ` Q ${nodeX + 70} ${(points[i - 1].y + points[i].y) / 2} ${points[i].x + 22} ${points[i].y}`;
        } else {
          d += ` L ${points[i].x + 22} ${points[i].y}`;
        }
      }
      pathD = d;
    }

    bypassPath.attr('d', pathD).attr('stroke', bp.color).attr('opacity', 0.8)
      .each(function() {
        const len = this.getTotalLength();
        d3.select(this).attr('stroke-dasharray', `${len} ${len}`)
          .attr('stroke-dashoffset', len)
          .transition().duration(600).ease(d3.easeCubicOut)
          .attr('stroke-dashoffset', 0);
      });
  }

  // Subscribe to engine
  engine.subscribe(state => {
    if (!state) return;
    rebuildButtons(state.bypassEligibility);
    showBypass(currentBypass, state.bypassEligibility);
  });
}
