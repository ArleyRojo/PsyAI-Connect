(function () {
  'use strict';

  const carousel = document.getElementById('heroCarousel');
  if (!carousel) return;

  const slides = carousel.querySelectorAll('.carousel-item');
  const imgs = carousel.querySelectorAll('.carousel-item img');
  const prevBtn = carousel.querySelector('.carousel-control-prev');
  const nextBtn = carousel.querySelector('.carousel-control-next');
  const indicators = carousel.querySelectorAll('.carousel-indicators button');
  let current = 0;
  let autoplayTimer = null;
  let isTransitioning = false;
  let isTabVisible = true;

  /* ── Lazy load images via IntersectionObserver ── */
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const img = entry.target;
          if (img.dataset.src && !img.getAttribute('src')) {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
          }
        }
      });
    }, { rootMargin: '200px' });

    imgs.forEach((img) => {
      if (!img.getAttribute('fetchpriority')) {
        const src = img.getAttribute('src');
        if (src) {
          img.setAttribute('data-src', src);
          img.removeAttribute('src');
        }
<<<<<<< HEAD
        img.style.background = '#f0f5fc';
=======
        img.style.background = '';
>>>>>>> 629d7c0 (avances)
      }
      observer.observe(img);
    });
  }

  /* ── Update indicators ── */
  function updateIndicators(index) {
    indicators.forEach((btn, i) => {
      btn.classList.toggle('active', i === index);
    });
  }

  /* ── Autoplay with delay before loading slide 2 & 3 ── */
  function goTo(index) {
    if (isTransitioning) return;
    if (index < 0) index = slides.length - 1;
    if (index >= slides.length) index = 0;
    if (index === current) return;

    isTransitioning = true;
    slides[current].classList.remove('active');
    slides[current].setAttribute('aria-hidden', 'true');

    /* Load image just before showing */
    const nextImg = slides[index].querySelector('img');
    if (nextImg && nextImg.dataset.src && !nextImg.getAttribute('src')) {
      nextImg.src = nextImg.dataset.src;
      nextImg.removeAttribute('data-src');
    }

    slides[index].classList.add('active');
    slides[index].setAttribute('aria-hidden', 'false');
    current = index;
    updateIndicators(current);

    setTimeout(() => { isTransitioning = false; }, 500);
  }

  function next() { goTo(current + 1); }
  function prev() { goTo(current - 1); }

  function startAutoplay() {
    stopAutoplay();
    if (!isTabVisible) return;
    autoplayTimer = setInterval(next, 5000);
  }

  function stopAutoplay() {
    if (autoplayTimer) {
      clearInterval(autoplayTimer);
      autoplayTimer = null;
    }
  }

  /* ── Controls ── */
  if (prevBtn) prevBtn.addEventListener('click', function (e) {
    e.preventDefault();
    stopAutoplay();
    prev();
    startAutoplay();
  });

  if (nextBtn) nextBtn.addEventListener('click', function (e) {
    e.preventDefault();
    stopAutoplay();
    next();
    startAutoplay();
  });

  /* ── Indicator clicks ── */
  indicators.forEach((btn) => {
    btn.addEventListener('click', function () {
      const index = parseInt(this.getAttribute('data-index'));
      if (index === current) return;
      stopAutoplay();
      goTo(index);
      startAutoplay();
    });
  });

  /* ── Touch support ── */
  let touchStartX = 0;
  let touchEndX = 0;
  carousel.addEventListener('touchstart', function (e) {
    touchStartX = e.changedTouches[0].screenX;
  }, { passive: true });
  carousel.addEventListener('touchend', function (e) {
    touchEndX = e.changedTouches[0].screenX;
    const diff = touchStartX - touchEndX;
    if (Math.abs(diff) > 50) {
      stopAutoplay();
      if (diff > 0) next(); else prev();
      startAutoplay();
    }
  }, { passive: true });

  /* ── Keyboard ── */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft') { stopAutoplay(); prev(); startAutoplay(); }
    if (e.key === 'ArrowRight') { stopAutoplay(); next(); startAutoplay(); }
  });

  /* ── Pause on hover ── */
  carousel.addEventListener('mouseenter', stopAutoplay);
  carousel.addEventListener('mouseleave', startAutoplay);

  /* ── Pause on tab hidden ── */
  document.addEventListener('visibilitychange', function () {
    isTabVisible = !document.hidden;
    if (document.hidden) {
      stopAutoplay();
    } else {
      startAutoplay();
    }
  });

  /* ── Init first slide visible ── */
  slides.forEach((s, i) => {
    s.setAttribute('aria-hidden', i === 0 ? 'false' : 'true');
  });
  updateIndicators(0);

  startAutoplay();
})();
