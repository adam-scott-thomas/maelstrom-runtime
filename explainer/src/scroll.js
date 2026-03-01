/* ═══════════════════════════════════════════════════════════════════════
   Scroll behavior — progress bar, nav, section observers
   ═══════════════════════════════════════════════════════════════════════ */

export function initScroll() {
  const progressBar = document.getElementById('progress-bar');
  const nav = document.getElementById('nav');
  const navLinks = document.querySelectorAll('.nav-links a');
  const sections = document.querySelectorAll('.section');

  // ── Progress bar ──────────────────────────────────────────────────
  window.addEventListener('scroll', () => {
    const scrollTop = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
    progressBar.style.width = progress + '%';

    // Show nav after scrolling past hero
    if (scrollTop > window.innerHeight * 0.5) {
      nav.classList.add('visible');
    } else {
      nav.classList.remove('visible');
    }
  }, { passive: true });

  // ── Section observer for nav highlighting ─────────────────────────
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        navLinks.forEach(link => {
          link.classList.toggle('active', link.dataset.section === id);
        });
      }
    });
  }, { threshold: 0.3 });

  sections.forEach(section => observer.observe(section));

  // ── Fade-in observer ──────────────────────────────────────────────
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
