/* ═══════════════════════════════════════════════════════════════════════
   Shared tooltip — single DOM element, positioned on mousemove
   ═══════════════════════════════════════════════════════════════════════ */

let tooltipEl = null;

function ensureTooltip() {
  if (tooltipEl) return tooltipEl;
  tooltipEl = document.getElementById('tooltip');
  if (!tooltipEl) {
    tooltipEl = document.createElement('div');
    tooltipEl.id = 'tooltip';
    document.body.appendChild(tooltipEl);
  }
  return tooltipEl;
}

export function showTooltip(html, event) {
  const el = ensureTooltip();
  el.innerHTML = html;
  el.style.opacity = '1';
  el.style.pointerEvents = 'none';
  positionTooltip(event);
}

export function positionTooltip(event) {
  const el = ensureTooltip();
  const pad = 12;
  let x = event.clientX + pad;
  let y = event.clientY + pad;

  // Keep within viewport
  const rect = el.getBoundingClientRect();
  if (x + rect.width > window.innerWidth - pad) {
    x = event.clientX - rect.width - pad;
  }
  if (y + rect.height > window.innerHeight - pad) {
    y = event.clientY - rect.height - pad;
  }

  el.style.left = x + 'px';
  el.style.top = y + 'px';
}

export function hideTooltip() {
  const el = ensureTooltip();
  el.style.opacity = '0';
}
