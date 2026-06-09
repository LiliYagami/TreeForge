/* ═══════════════════════════════════════════
   TreeForge — main.js
   Version fusionnée (inclut accordéon + reveal)
═══════════════════════════════════════════ */

'use strict';

// ── Nav scroll state ──────────────────────────────────────
const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {
  nav.classList.toggle('scrolled', window.scrollY > 20);
}, { passive: true });

// ── Scroll reveal (général) ───────────────────────────────
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

// Éléments existants + nouveaux (docs/releases)
document.querySelectorAll(
  '.feature-card, .step, .workflow-bonus, .download-box, .hero-terminal, ' +
  '.roadmap.reveal, .release-item.reveal, .acc-item'
).forEach(el => {
  el.classList.add('reveal');
  revealObserver.observe(el);
});

// Staggered animation for feature cards
document.querySelectorAll('.feature-card').forEach((card, i) => {
  card.style.transitionDelay = `${i * 80}ms`;
});

// ── Download tracking (console only) ──────────────────────
['dl-hero', 'dl-main'].forEach(id => {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener('click', () => {
    console.info('[TreeForge] Download initiated from:', id);
  });
});

// ── Smooth active nav highlight ───────────────────────────
const sections = document.querySelectorAll('section[id]');
const navLinks  = document.querySelectorAll('.nav-links a[href^="#"]');

const sectionObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    const id = entry.target.id;
    navLinks.forEach(link => {
      link.style.color = link.getAttribute('href') === `#${id}`
        ? 'var(--text)'
        : '';
    });
  });
}, { threshold: 0.4 });

sections.forEach(s => sectionObserver.observe(s));

// ── Ticker pause on hover ─────────────────────────────────
const ticker = document.querySelector('.ticker');
if (ticker) {
  const wrap = ticker.parentElement;
  wrap.addEventListener('mouseenter', () => {
    ticker.style.animationPlayState = 'paused';
  });
  wrap.addEventListener('mouseleave', () => {
    ticker.style.animationPlayState = 'running';
  });
}

// ── Copy code on terminal click ───────────────────────────
const treeEl = document.querySelector('.t-line.tree');
if (treeEl) {
  treeEl.style.cursor = 'pointer';
  treeEl.title = 'Cliquer pour copier';
  treeEl.addEventListener('click', () => {
    const text = treeEl.innerText;
    navigator.clipboard?.writeText(text).then(() => {
      const orig = treeEl.style.color;
      treeEl.style.color = 'var(--green)';
      setTimeout(() => { treeEl.style.color = orig; }, 800);
    });
  });
}

/* ═══════════════════════════════════════════════════════════
   ACCORDÉON pour la section Documentation
   Comportement : un seul item ouvert à la fois
   Applique max-height dynamique sur scrollHeight
═══════════════════════════════════════════════════════════ */
document.querySelectorAll('[data-acc]').forEach(item => {
  const header = item.querySelector('.acc-header');
  const body   = item.querySelector('.acc-body');

  // Initialisation : si l'item a la classe 'open', on ajuste sa hauteur
  if (item.classList.contains('open')) {
    body.style.maxHeight = body.scrollHeight + 'px';
  } else {
    body.style.maxHeight = '0';
  }

  header.addEventListener('click', () => {
    const isOpen = item.classList.contains('open');

    // Fermer tous les accordéons
    document.querySelectorAll('[data-acc]').forEach(i => {
      i.classList.remove('open');
      const b = i.querySelector('.acc-body');
      b.style.maxHeight = '0';
    });

    // Si celui-ci n'était pas ouvert, on l'ouvre
    if (!isOpen) {
      item.classList.add('open');
      body.style.maxHeight = body.scrollHeight + 'px';
    }
  });
});

// Optionnel : recalcul des max-height si le contenu change dynamiquement
// (utile si jamais du texte est chargé plus tard, mais pas nécessaire ici)
window.addEventListener('resize', () => {
  document.querySelectorAll('.acc-item.open').forEach(item => {
    const body = item.querySelector('.acc-body');
    if (body) body.style.maxHeight = body.scrollHeight + 'px';
  });
});