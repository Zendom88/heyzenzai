/* ============================================
   HEYZENZAI — Interactive JavaScript
   ============================================ */

// ---- NAV: Scroll state ----
const navbar = document.getElementById('navbar');

window.addEventListener('scroll', () => {
  if (window.scrollY > 30) navbar.classList.add('scrolled');
  else navbar.classList.remove('scrolled');
}, { passive: true });

// ---- MOBILE FAB + GLASSMORPHISM DRAWER ----
const fabBtn       = document.getElementById('fab-menu');
const drawer       = document.getElementById('mobile-drawer');
const drawerClose  = document.getElementById('drawer-close');
const drawerBack   = document.getElementById('drawer-backdrop');
const drawerLinks  = drawer ? drawer.querySelectorAll('.drawer-links a, .drawer-btn') : [];
const drawerTheme  = document.getElementById('drawer-theme-btn');

function openDrawer() {
  if (!drawer || !fabBtn) return;
  drawer.classList.add('is-open');
  drawer.setAttribute('aria-hidden', 'false');
  fabBtn.classList.add('is-open');
  fabBtn.setAttribute('aria-expanded', 'true');
  document.body.style.overflow = 'hidden';
  // Move focus into drawer for a11y
  if (drawerClose) setTimeout(() => drawerClose.focus(), 50);
}

function closeDrawer() {
  if (!drawer || !fabBtn) return;
  drawer.classList.remove('is-open');
  drawer.setAttribute('aria-hidden', 'true');
  fabBtn.classList.remove('is-open');
  fabBtn.setAttribute('aria-expanded', 'false');
  document.body.style.overflow = '';
  fabBtn.focus();
}

if (fabBtn)      fabBtn.addEventListener('click', openDrawer);
if (drawerClose) drawerClose.addEventListener('click', closeDrawer);
if (drawerBack)  drawerBack.addEventListener('click', closeDrawer);

// Close on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && drawer && drawer.classList.contains('is-open')) {
    closeDrawer();
  }
});

// Close on any nav link click inside drawer
drawerLinks.forEach(link => {
  link.addEventListener('click', closeDrawer);
});

// Sync drawer theme button with main theme toggle
if (drawerTheme) {
  drawerTheme.addEventListener('click', () => {
    toggleTheme();
    // Update icon in drawer
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    drawerTheme.innerHTML = (current === 'light' ? '🌙' : '☀️') + ' Toggle Theme';
  });
}

// ---- OLD HAMBURGER (desktop fallback) — kept for screens 769–1024px ----
const hamburger = document.getElementById('hamburger');
const navLinks  = document.getElementById('nav-links');

if (hamburger && navLinks) {
  hamburger.addEventListener('click', () => {
    navLinks.classList.toggle('open');
    hamburger.classList.toggle('open');
    hamburger.setAttribute('aria-expanded', navLinks.classList.contains('open'));
  });

  // Close desktop menu on link click
  navLinks.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => navLinks.classList.remove('open'));
  });
}



// ---- SCROLL REVEAL ----
const revealEls = document.querySelectorAll('.pain-card, .agent-card, .feature-card, .grant-card, .testimonial-card, .pricing-card, .setup-strip, .problem-callout, .pricing-guarantee, .grants-math, .comparison-table-wrap, .roi-calculator');

revealEls.forEach(el => {
  el.classList.add('reveal');
  // Only hide if JS is running (progressive enhancement)
  el.classList.add('pre-reveal');
});

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      setTimeout(() => {
        entry.target.classList.remove('pre-reveal');
        entry.target.classList.add('visible');
      }, i * 80);
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.05, rootMargin: '0px 0px -20px 0px' });

revealEls.forEach(el => revealObserver.observe(el));


// ---- STAT COUNTER ANIMATION ----
function animateCounter(el, target, suffix) {
  const duration = 1800;
  const start = performance.now();

  function step(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 4);
    el.textContent = Math.floor(eased * target);
    if (progress < 1) requestAnimationFrame(step);
    else el.textContent = target;
  }
  requestAnimationFrame(step);
}

const statsObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      document.querySelectorAll('.stat-num').forEach(el => {
        animateCounter(el, parseInt(el.dataset.target), '');
      });
      statsObserver.disconnect();
    }
  });
}, { threshold: 0.5 });

const heroStats = document.querySelector('.hero-stats');
if (heroStats) statsObserver.observe(heroStats);


// ---- WHATSAPP CHAT ANIMATION ----
function runChatAnimation() {
  const typing = document.querySelector('.typing-start');
  const botMsg1 = document.getElementById('bot-msg-1');
  const clientMsg2 = document.getElementById('client-msg-2');
  const botMsg2 = document.getElementById('bot-msg-2');
  const chat = document.querySelector('.wa-chat');

  if (!typing || !botMsg1) return;

  const seq = [
    { delay: 2000, action: () => { typing.classList.remove('typing-start'); } },
    { delay: 800,  action: () => { typing.classList.add('hidden'); botMsg1.classList.remove('chat-hidden'); botMsg1.classList.add('chat-visible'); } },
    { delay: 2200, action: () => { clientMsg2.classList.remove('chat-hidden'); clientMsg2.classList.add('chat-visible'); } },
    { delay: 1800, action: () => { botMsg2.classList.remove('chat-hidden'); botMsg2.classList.add('chat-visible'); } },
    { delay: 6000, action: () => resetChat() }
  ];


  let accum = 0;
  seq.forEach(({ delay, action }) => {
    accum += delay;
    setTimeout(action, accum);
  });
}

function resetChat() {
  const typing = document.querySelector('.typing-start');
  const botMsg1 = document.getElementById('bot-msg-1');
  const clientMsg2 = document.getElementById('client-msg-2');
  const botMsg2 = document.getElementById('bot-msg-2');

  if (!typing) return;

  botMsg1?.classList.remove('chat-visible'); botMsg1?.classList.add('chat-hidden');
  clientMsg2?.classList.remove('chat-visible'); clientMsg2?.classList.add('chat-hidden');
  botMsg2?.classList.remove('chat-visible'); botMsg2?.classList.add('chat-hidden');
  typing.classList.remove('hidden');
  typing.classList.add('typing-start');

  setTimeout(runChatAnimation, 2000);
}

// Start chat animation after a brief delay
setTimeout(runChatAnimation, 1500);


// ---- ROI CALCULATOR ----
const roiInputs = ['avg-ticket', 'weekly-bookings', 'noshows'].map(id => document.getElementById(id));

function calcROI() {
  const ticket = parseFloat(document.getElementById('avg-ticket').value) || 200;
  const weekly = parseFloat(document.getElementById('weekly-bookings').value) || 50;
  const noshowPct = parseFloat(document.getElementById('noshows').value) || 15;

  const monthly = weekly * 4.33;
  const currentNoShows = monthly * (noshowPct / 100);
  const afterNoShows = monthly * 0.03;
  const recovered = Math.round((currentNoShows - afterNoShows) * ticket);
  const labor = 3000;
  const total = recovered + labor;

  function animateVal(el, val, prefix = 'SGD ', suffix = '') {
    const current = parseInt(el.textContent.replace(/\D/g, '')) || 0;
    const dur = 600;
    const start = performance.now();
    const from = current;
    function step(now) {
      const t = Math.min((now - start) / dur, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      el.textContent = prefix + Math.round(from + (val - from) * eased).toLocaleString() + suffix;
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  animateVal(document.getElementById('val-recovered'), recovered);
  animateVal(document.getElementById('val-labor'), labor);
  animateVal(document.getElementById('val-total'), total);
}

roiInputs.forEach(input => {
  if (input) input.addEventListener('input', calcROI);
});
calcROI(); // initial calc


// ---- FORM SUBMIT ----
async function handleSubmit(e) {
  e.preventDefault();
  const btn = document.getElementById('submit-btn');
  const text = document.getElementById('submit-text');
  const loading = document.getElementById('submit-loading');
  const form = document.getElementById('contact-form');
  const success = document.getElementById('form-success');

  // Read field values
  const name     = document.getElementById('f-name').value.trim();
  const phone    = document.getElementById('f-phone').value.trim();
  const bizType  = document.getElementById('f-type').value;
  const botField = document.getElementById('bot-field').value;

  // Honeypot check
  if (botField) {
    form.querySelectorAll('.form-group, .form-row, .btn-submit, .form-disclaimer, .g-recaptcha').forEach(el => {
      el.style.display = 'none';
    });
    success.classList.remove('hidden');
    return; 
  }

  // reCAPTCHA validation
  const captchaResponse = grecaptcha.getResponse();
  if (!captchaResponse) {
    alert("Please complete the checkbox to verify you are human.");
    return;
  }

  // Show loading state
  btn.disabled = true;
  text.classList.add('hidden');
  loading.classList.remove('hidden');

  try {
    const res = await fetch('https://formspree.io/f/mqeggwze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({
        name:          name,
        whatsapp:      phone,
        business_type: bizType,
        "g-recaptcha-response": captchaResponse,
        _subject:      `New Early Access Request from ${name}`,
      }),
    });


    if (res.ok) {
      // Success — hide form fields, show confirmation
      form.querySelectorAll('.form-group, .form-row, .btn-submit, .form-disclaimer, .g-recaptcha').forEach(el => {
        el.style.display = 'none';
      });
      success.classList.remove('hidden');
    } else {
      // Formspree returned an error
      throw new Error('Submission failed');
    }
  } catch (err) {
    // Network error or Formspree error — re-enable form so they can retry
    btn.disabled = false;
    text.classList.remove('hidden');
    loading.classList.add('hidden');
    alert('Something went wrong. Please try again or WhatsApp us directly.');
  }
}



// ---- SMOOTH ACTIVE NAV LINKS ----
const sections = document.querySelectorAll('section[id]');
const navLinksAll = document.querySelectorAll('.nav-links a');

window.addEventListener('scroll', () => {
  let current = '';
  sections.forEach(section => {
    if (window.scrollY >= section.offsetTop - 120) {
      current = section.getAttribute('id');
    }
  });
  navLinksAll.forEach(a => {
    a.style.color = '';
    if (a.getAttribute('href') === `#${current}`) {
      a.style.color = 'var(--accent-green)';
    }
  });
}, { passive: true });


// ---- PARTICLE CANVAS (hero background) — deferred, mobile-optimized ----
function initParticles() {
  const heroEl = document.querySelector('.hero');
  if (!heroEl) return;

  const canvas = document.createElement('canvas');
  canvas.style.cssText = 'position:absolute;inset:0;pointer-events:none;z-index:0;opacity:0.4';
  heroEl.prepend(canvas);

  const ctx = canvas.getContext('2d');
  let w, h, particles;
  // Reduce particle count on mobile to ease main-thread load
  const PARTICLE_COUNT = window.innerWidth < 768 ? 20 : 60;

  function resize() {
    w = canvas.width = canvas.offsetWidth;
    h = canvas.height = canvas.offsetHeight;
  }

  function createParticles() {
    particles = Array.from({ length: PARTICLE_COUNT }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      r: Math.random() * 1.5 + 0.5,
      dx: (Math.random() - 0.5) * 0.3,
      dy: (Math.random() - 0.5) * 0.3,
      opacity: Math.random() * 0.5 + 0.1,
      color: Math.random() > 0.5 ? '0, 229, 160' : '59, 130, 246'
    }));
  }

  function draw() {
    ctx.clearRect(0, 0, w, h);
    particles.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${p.color}, ${p.opacity})`;
      ctx.fill();
      p.x += p.dx;
      p.y += p.dy;
      if (p.x < 0 || p.x > w) p.dx *= -1;
      if (p.y < 0 || p.y > h) p.dy *= -1;
    });

    // Draw connections (desktop only for performance)
    if (window.innerWidth >= 768) {
      particles.forEach((a, i) => {
        particles.slice(i + 1).forEach(b => {
          const dist = Math.hypot(a.x - b.x, a.y - b.y);
          if (dist < 120) {
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.strokeStyle = `rgba(59, 130, 246, ${0.08 * (1 - dist / 120)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        });
      });
    }

    requestAnimationFrame(draw);
  }

  window.addEventListener('resize', () => { resize(); createParticles(); });
  resize();
  createParticles();
  draw();
}

// Defer particle init until browser is idle (after LCP)
if ('requestIdleCallback' in window) {
  requestIdleCallback(initParticles, { timeout: 2000 });
} else {
  setTimeout(initParticles, 1000);
}


// ---- PRICING TOGGLE HOVER EFFECTS ----
document.querySelectorAll('.pricing-card').forEach(card => {
  card.addEventListener('mouseenter', function() {
    this.style.boxShadow = this.classList.contains('pricing-card--pro')
      ? '0 20px 60px rgba(0, 229, 160, 0.15)'
      : '0 20px 60px rgba(59, 130, 246, 0.1)';
  });
  card.addEventListener('mouseleave', function() {
    this.style.boxShadow = '';
  });
});


// ---- GSAP-like micro animation on section entry ----
const staggerObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    const children = entry.target.querySelectorAll('.pain-card, .agent-card, .feature-card, .grant-card, .testimonial-card');
    children.forEach((el, i) => {
      el.style.transitionDelay = `${i * 0.08}s`;
    });
    staggerObserver.unobserve(entry.target);
  });
}, { threshold: 0.1 });

document.querySelectorAll('.pain-grid, .agents-flow, .features-grid, .grants-grid, .testimonials-grid').forEach(el => {
  staggerObserver.observe(el);
});


// ---- PRICING PLAN TOGGLE ----
const planData = {
  monthly: {
    starter: { price: '49',  billing: '+ SGD 149 one-time setup fee' },
    growth:  { price: '149', billing: '+ SGD 149 one-time setup fee' }
  },
  biannual: {
    starter: { price: '42',  billing: 'SGD 252 billed every 6 months  ·  SGD 99 setup' },
    growth:  { price: '127', billing: 'SGD 762 billed every 6 months  ·  SGD 99 setup' }
  },
  annual: {
    starter: { price: '39',  billing: 'SGD 468 billed annually  ·  Setup fee waived ✓' },
    growth:  { price: '119', billing: 'SGD 1,428 billed annually  ·  Setup fee waived ✓' }
  }
};

function switchPlan(period) {
  const p = planData[period];
  if (!p) return;
  const starterPrice   = document.getElementById('starter-price');
  const growthPrice    = document.getElementById('growth-price');
  const starterBilling = document.getElementById('starter-billing');
  const growthBilling  = document.getElementById('growth-billing');

  [starterPrice, growthPrice].forEach(el => {
    if (el) { el.style.transition = 'none'; el.style.transform = 'translateY(-10px)'; el.style.opacity = '0'; }
  });
  setTimeout(() => {
    if (starterPrice)   starterPrice.textContent  = p.starter.price;
    if (growthPrice)    growthPrice.textContent    = p.growth.price;
    if (starterBilling) starterBilling.textContent = p.starter.billing;
    if (growthBilling)  growthBilling.textContent  = p.growth.billing;
    [starterPrice, growthPrice].forEach(el => {
      if (el) {
        el.style.transform = 'translateY(8px)';
        requestAnimationFrame(() => {
          el.style.transition = 'transform 0.35s ease, opacity 0.35s ease';
          el.style.transform  = 'translateY(0)';
          el.style.opacity    = '1';
        });
      }
    });
  }, 160);
  document.querySelectorAll('.ptoggle-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.period === period);
  });
}


// ---- THEME TOGGLE (Dark / Light) ----
function initTheme() {
  const saved = localStorage.getItem('hz-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  updateThemeIcon(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('hz-theme', next);
  updateThemeIcon(next);
}

function updateThemeIcon(theme) {
  const btn = document.getElementById('theme-toggle-btn');
  if (btn) btn.textContent = theme === 'light' ? '🌙' : '☀️';
}

initTheme();
