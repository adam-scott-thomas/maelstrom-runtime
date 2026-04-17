/* ═══════════════════════════════════════════════════════════════════════
   Scroll behavior — progress bar, nav, fade-in, auto-ramp engine state
   ═══════════════════════════════════════════════════════════════════════ */

// Section presets for auto-ramp (sensible defaults to demonstrate each concept)
const SECTION_PRESETS = {
  intro:   { time_pressure: 0.30, ambiguity: 0.25, threat_level: 0.15, moral_weight: 0.20 },
  loop:    { time_pressure: 0.10, ambiguity: 0.10, threat_level: 0.05, moral_weight: 0.10 },
  regimes: { time_pressure: 0.25, ambiguity: 0.20, threat_level: 0.50, moral_weight: 0.35 },
  stress:  null, // user takes control
  bypass:  { time_pressure: 0.70, ambiguity: 0.30, threat_level: 0.65, moral_weight: 0.25 },
  regret:  null, // uses current stressors
  determinism: null,
  why: null,
};

export function initScroll(engine) {
  const progressBar = document.getElementById('progress-bar');
  const nav = document.getElementById('nav');
  const navLinks = document.querySelectorAll('.nav-links a');
  const sections = document.querySelectorAll('.section');

  let userOverridden = false;

  // Mark as user-overridden when any stressor slider is touched
  document.addEventListener('input', (e) => {
    if (e.target.dataset?.stressor) userOverridden = true;
  });

  // Progress bar
  window.addEventListener('scroll', () => {
    const scrollTop = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    progressBar.style.width = (docHeight > 0 ? (scrollTop / docHeight) * 100 : 0) + '%';

    if (scrollTop > window.innerHeight * 0.5) {
      nav.classList.add('visible');
    } else {
      nav.classList.remove('visible');
    }
  }, { passive: true });

  // Section observer for nav + auto-ramp
  const sectionObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;

        // Nav highlighting
        navLinks.forEach(link => link.classList.toggle('active', link.dataset.section === id));

        // Auto-ramp (only if user hasn't manually overridden)
        if (!userOverridden && SECTION_PRESETS[id]) {
          engine.setStressors(SECTION_PRESETS[id]);
        }
      }
    });
  }, { threshold: 0.3 });

  sections.forEach(section => sectionObserver.observe(section));

  // Fade-in observer
  const fadeEls = document.querySelectorAll('.text-col, .visual-col, .section__inner--center');
  fadeEls.forEach(el => el.classList.add('fade-up'));

  const fadeObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        fadeObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  fadeEls.forEach(el => fadeObserver.observe(el));
}
