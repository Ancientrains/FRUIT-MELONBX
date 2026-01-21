
(() => {
    const target = document.querySelector('.placeholder-section');
    if (!target) return;

    const io = new IntersectionObserver((entries) => {
        entries.forEach(e => {
            if (e.isIntersecting) {
                target.classList.add('visible');
                io.disconnect(); // only animate once
            }
        });
    }, { threshold: 0.2 });

    io.observe(target);
})();

(function () {
  var loader = document.getElementById("page-loader");
  if (!loader) {
    return;
  }

  var config = {
    images: [
      "load-screen-assets/DSC_0669.JPG",
      "load-screen-assets/DSC_0670.JPG",
      "load-screen-assets/DSC_0671.JPG",
      "load-screen-assets/DSC_0672.JPG",
      "load-screen-assets/DSC_0686.JPG",
      "load-screen-assets/DSC_0687.JPG",
      "load-screen-assets/DSC_0689.JPG",
      "load-screen-assets/DSC_0690.JPG",
      "load-screen-assets/DSC_0692.JPG",
      "load-screen-assets/DSC_0694.JPG",
      "load-screen-assets/DSC_0695.JPG"
    ],
    holdMs: 1000,
    fadeMs: 600,
    zoom: 1.04,
    minVisibleMs: 1500
  };

  loader.style.setProperty("--slide-fade-ms", String(config.fadeMs));
  loader.style.setProperty("--slide-zoom", String(config.zoom));

  var slideA = loader.querySelector(".page-loader__slide--a");
  var slideB = loader.querySelector(".page-loader__slide--b");
  var slides = [slideA, slideB];
  var activeIndex = 0;
  var imageIndex = Math.floor(Math.random() * config.images.length);

  if (config.images.length) {
    slides[activeIndex].style.backgroundImage = "url('" + config.images[imageIndex] + "')";
  }

  function cycle() {
    if (!loader.isConnected || config.images.length < 2) {
      return;
    }

    var nextSlideIndex = (activeIndex + 1) % slides.length;
    var nextImageIndex = (imageIndex + 1) % config.images.length;
    var nextSlide = slides[nextSlideIndex];

    nextSlide.style.backgroundImage = "url('" + config.images[nextImageIndex] + "')";
    nextSlide.classList.add("is-active");
    slides[activeIndex].classList.remove("is-active");

    activeIndex = nextSlideIndex;
    imageIndex = nextImageIndex;

    window.setTimeout(cycle, config.holdMs);
  }

  window.setTimeout(cycle, config.holdMs);

  var startTime = Date.now();

  function hideLoader() {
    document.body.classList.remove("is-loading");
    loader.classList.add("is-hidden");
    loader.addEventListener("transitionend", function () {
      loader.remove();
    });
  }

  window.addEventListener("load", function () {
    var elapsed = Date.now() - startTime;
    var remaining = Math.max(0, config.minVisibleMs - elapsed);
    window.setTimeout(hideLoader, remaining);
  });
})();

(() => {
        const timers = new WeakMap();
        const $all = (sel, root=document) => Array.from(root.querySelectorAll(sel));

        function clearHold(el){
            const t = timers.get(el);
            if (t){ clearTimeout(t); timers.delete(el); }
        }
        function clearHoldAll(list){ list.forEach(clearHold); }

        function holdOff(el, ms){
            clearHold(el);
            const id = setTimeout(() => {
            el.classList.remove('is-active');
            timers.delete(el);
            }, ms);
            timers.set(el, id);
        }
        function holdOffAll(list, ms){ list.forEach(el => holdOff(el, ms)); }

        function attach(el){
            const groupName = el.dataset.stickyGroup;
            const groupEls  = groupName ? $all(`[data-sticky-group="${groupName}"]`) : [el];

            const holdMs = Number.parseInt(el.dataset.hold || '', 10);
            const HOLD   = Number.isFinite(holdMs) ? holdMs : 1500;

            const onEnter = () => {
            clearHoldAll(groupEls);
            groupEls.forEach(n => n.classList.add('is-active'));
            };
            const onLeave = () => holdOffAll(groupEls, HOLD);

            el.addEventListener('mouseenter', onEnter);
            el.addEventListener('mouseleave', onLeave);

            // Accessibility + touch
            el.addEventListener('focusin',  onEnter);
            el.addEventListener('focusout', onLeave);
            el.addEventListener('touchstart', onEnter, {passive:true});
            el.addEventListener('touchend',   onLeave);
        }

        document.addEventListener('DOMContentLoaded', () => {
            document.querySelectorAll('.sticky-transform').forEach(attach);
        });
        })();

    (() => {
        const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        const footer = document.querySelector('.footer-root');
        const path1   = document.querySelector('.footer-root .wave-1-component .wave-path1');
        const path2   = document.querySelector('.footer-root .wave-2-component .wave-path2');
        if (!footer || !path1 ||!path2) return;
        
        if (prefersReduced) {
            path1.classList.remove('wave-calm1', 'wave-active1');
            path2.classList.remove('wave-calm2', 'wave-active2');
            return;
        }

        const ACTIVE_MS   = 5500; // how long the active wave runs
        const COOLDOWN_MS = 6000; // minimum time before re-trigger
        let isActive = false, cooling = false, t1 = 0, t2 = 0;

        function activate() {
            if (isActive || cooling) return;
            isActive = true;

            // swap calm -> active (restart animation cleanly)
            path1.classList.remove('wave-calm1');
            path2.classList.remove('wave-calm2');
            void path1.offsetWidth;
            void path2.offsetWidth;
            path1.classList.add('wave-active1');
            path2.classList.add('wave-active2');

            clearTimeout(t1);
            t1 = setTimeout(() => {
            // revert to calm, then cooldown
            path1.classList.remove('wave-active1');
            path2.classList.remove('wave-active2')
            path1.classList.add('wave-calm1');
            path2.classList.add('wave-calm2');
            isActive = false;
            cooling = true;
            clearTimeout(t2);
            t2 = setTimeout(() => (cooling = false), COOLDOWN_MS);
            }, ACTIVE_MS);
        }

        // Trigger when footer is at least 25% visible
        const io = new IntersectionObserver((entries) => {
            entries.forEach(e => {
            if (e.isIntersecting && e.intersectionRatio >= 0.25) activate();
            });
        }, { threshold: [0, 0.25, 1] });

        io.observe(footer);
        })();

(() => {
  const cards = document.querySelectorAll('.about-card');
  if (!cards.length) return;

  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReduced) {
    cards.forEach(c => c.classList.add('is-inview'));
    return;
  }

  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (e.isIntersecting) {
        e.target.classList.add('is-inview');
        io.unobserve(e.target); // animate once
      }
    }
  }, {
    threshold: 0.25,
    rootMargin: '0px 0px -10% 0px'
  });

  cards.forEach(card => io.observe(card));
})();

// Needed only because your HTML uses onclick="handleUploadClick()".
// If you switch to addEventListener instead, you can delete this.
(() => {
  const MAX_IMAGES = 3;

  /** @type {{id:string,file:File,url:string,el:HTMLElement}[]} */
  let photos = [];
  /** @type {string|null} */
  let editingId = null;

  const uploadBg = document.querySelector('.upload-image-bg');
  if (!uploadBg) return;
  const uploadBtnWrap = document.querySelector('.buttons-upload');

    function syncUploadButton() {
    if (!uploadBtnWrap) return;
    uploadBtnWrap.classList.toggle('is-hidden', photos.length > 0);
    }

  // --- Minimal styles so it works even if you don't touch style.css ---
  const style = document.createElement('style');
  style.textContent = `
    .upload-image-bg{overflow:hidden; }
    .upload-gallery{ position:absolute; inset:0; display:block; align-items:center; justify-content:flex-start; gap:14px; padding:14px; overflow:hidden; }
    .upload-gallery::-webkit-scrollbar{ height:10px; }
    .upload-thumb{ position:absolute; flex:0 0 auto; width:240px; height:240px; border-radius:16px; overflow:hidden; box-shadow:0 8px 20px rgba(0,0,0,.12); }
    .upload-thumb img{ width:100%; height:100%; object-fit:cover; display:block; cursor:pointer; }
    .upload-thumb__x{ position:absolute; top:8px; right:8px; width:28px; height:28px; border-radius:999px; border:0; cursor:pointer;
      background:rgba(0,0,0,.55); color:#fff; font-size:18px; line-height:28px; display:flex; align-items:center; justify-content:center; }
    .upload-thumb__x:hover{ background:rgba(0,0,0,.75); }
    .upload-hint{ position:absolute; right:14px; bottom:14px; padding:8px 10px; border-radius:12px; background:rgba(255,255,255,.85); font: 14px/1.2 system-ui, -apple-system, Segoe UI, Roboto, Arial; }
    .upload-warning{ position:absolute; right:14px; top:14px; padding:8px 10px; border-radius:12px; background:rgba(255, 220, 220, .95); border:1px solid rgba(200,0,0,.25);
      font: 14px/1.2 system-ui, -apple-system, Segoe UI, Roboto, Arial; display:none; }
    .upload-analyze{ position:absolute; right:14px; bottom:14px; padding:10px 14px; border-radius:12px; border:0; cursor:pointer;
      background:#111; color:#fff; font: 14px/1.2 system-ui, -apple-system, Segoe UI, Roboto, Arial; letter-spacing:.2px; }
    .upload-analyze[disabled]{ opacity:.6; cursor:default; }
    .upload-download{ position:absolute; right:14px; bottom:56px; padding:10px 14px; border-radius:12px; border:0; cursor:pointer;
      background:#fff; color:#111; font: 14px/1.2 system-ui, -apple-system, Segoe UI, Roboto, Arial; letter-spacing:.2px; }
    .upload-download[disabled]{ opacity:.6; cursor:default; }
  `;
  document.head.appendChild(style);

  // --- DOM helpers ---
  const gallery = document.createElement('div');
  gallery.className = 'upload-gallery';
  uploadBg.appendChild(gallery);

  const hint = document.createElement('div');
  hint.className = 'upload-hint';
  hint.textContent = `Upload up to ${MAX_IMAGES} images. Click a photo to replace it.`;
  uploadBg.appendChild(hint);

  const warning = document.createElement('div');
  warning.className = 'upload-warning';
  uploadBg.appendChild(warning);

  const analyzeBtn = document.createElement('button');
  analyzeBtn.type = 'button';
  analyzeBtn.className = 'upload-analyze';
  analyzeBtn.textContent = 'Check Sweetness';
  uploadBg.appendChild(analyzeBtn);

  const downloadBtn = document.createElement('button');
  downloadBtn.type = 'button';
  downloadBtn.className = 'upload-download';
  downloadBtn.textContent = 'Download Labels';
  uploadBg.appendChild(downloadBtn);

  function showWarning(msg) {
    warning.textContent = msg;
    warning.style.display = 'block';
    clearTimeout(showWarning._t);
    showWarning._t = setTimeout(() => (warning.style.display = 'none'), 2500);
  }

  function updateHintVisibility() {
    hint.style.display = photos.length ? 'none' : 'block';
    analyzeBtn.style.display = photos.length ? 'block' : 'none';
    downloadBtn.style.display = photos.length ? 'block' : 'none';
    syncUploadButton();
  }
  function layoutStack() {
  if (!photos.length) return;

  // Container (gallery) size
  const g = gallery.getBoundingClientRect();
  const cx = g.width / 2;
  const cy = g.height / 2;

  // Thumb size (read from the real element so it stays correct if you change CSS)
  const t0 = photos[0].el.getBoundingClientRect();
  const w = t0.width;
  const h = t0.height;

  const gap = 18;              // space between thumbs when 2-up
  const yCenter = cy - h / 2;  // vertically centered

  // helper to apply pose
  const place = (p, x, y, rDeg, z) => {
    p.el.style.left = "0px";
    p.el.style.top = "0px";
    p.el.style.zIndex = String(z);
    p.el.style.transform = `translate(${x}px, ${y}px) rotate(${rDeg}deg)`;
  };

  if (photos.length === 1) {
    // single image: centered
    const x = cx - w / 2;
    place(photos[0], x, yCenter, 0, 3);
    return;
  }

  if (photos.length === 2) {
    // two images: center the *pair*
    const totalW = w * 2 + gap;
    const leftX = cx - totalW / 2;
    const rightX = leftX + w + gap;

    // slight rotations optional
    place(photos[0], leftX,  yCenter, -6, 2);
    place(photos[1], rightX, yCenter,  6, 3);
    return;
  }

  // 3 images: keep your “stacked” style but centered around container
  // (You can tweak these offsets/rotations)
  const baseX = cx - w / 2;
  const baseY = yCenter;

  place(photos[0], baseX - 250, baseY + 10,  0, 3);
  place(photos[1], baseX + 0,   baseY + 10,   0, 4);
  place(photos[2], baseX + 250, baseY + 10,   0, 2);
}

  // --- Hidden file inputs ---
  const uploadInput = document.createElement('input');
  uploadInput.type = 'file';
  uploadInput.accept = 'image/*';
  uploadInput.multiple = true;
  uploadInput.style.display = 'none';
  document.body.appendChild(uploadInput);

  const editInput = document.createElement('input');
  editInput.type = 'file';
  editInput.accept = 'image/*';
  editInput.multiple = false;
  editInput.style.display = 'none';
  document.body.appendChild(editInput);

  function makeId() {
    return (crypto?.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random()));
  }

  function createThumb({ id, url, file }) {
    const card = document.createElement('div');
    card.className = 'upload-thumb';
    card.dataset.photoId = id;

    const img = document.createElement('img');
    img.src = url;
    img.alt = file?.name || 'uploaded image';
    img.addEventListener('click', () => {
      editingId = id;
      editInput.value = '';
      editInput.click();
    });

    const x = document.createElement('button');
    x.type = 'button';
    x.className = 'upload-thumb__x';
    x.textContent = '×';
    x.title = 'Delete';
    x.addEventListener('click', (e) => {
      e.stopPropagation();
      removePhoto(id);
    });

    card.appendChild(img);
    card.appendChild(x);
    return card;
  }

  function addFiles(files) {
    const incoming = Array.from(files || []).filter(f => f && f.type && f.type.startsWith('image/'));
    if (!incoming.length) return;

    const available = MAX_IMAGES - photos.length;
    if (available <= 0) {
      showWarning(`Max ${MAX_IMAGES} images. Delete one to add more.`);
      return;
    }

    if (incoming.length > available) {
      showWarning(`Only ${available} more allowed (max ${MAX_IMAGES}). Extra files were ignored.`);
    }

    incoming.slice(0, available).forEach((file) => {
      const id = makeId();
      const url = URL.createObjectURL(file);
      const el = createThumb({ id, url, file });
      gallery.appendChild(el);
      photos.push({ id, file, url, el });
    });

    updateHintVisibility();
    layoutStack();
  }

  function removePhoto(id) {
    const idx = photos.findIndex(p => p.id === id);
    if (idx === -1) return;
    const p = photos[idx];
    try { URL.revokeObjectURL(p.url); } catch {}
    p.el.remove();
    photos.splice(idx, 1);
    updateHintVisibility();
    layoutStack();
  }

  function clearAllPhotos() {
    photos.slice().forEach(p => removePhoto(p.id));
  }

  function replacePhoto(id, file) {
    const idx = photos.findIndex(p => p.id === id);
    if (idx === -1) return;
    const p = photos[idx];
    if (!file || !file.type.startsWith('image/')) return;
    try { URL.revokeObjectURL(p.url); } catch {}
    const url = URL.createObjectURL(file);
    const img = p.el.querySelector('img');
    if (img) {
      img.src = url;
      img.alt = file.name || 'uploaded image';
    }
    photos[idx] = { ...p, file, url };
  }

  function setAnalyzeState(isLoading) {
    analyzeBtn.disabled = isLoading;
    analyzeBtn.textContent = isLoading ? 'Analyzing...' : 'Check Sweetness';
  }

  function setDownloadState(isLoading) {
    downloadBtn.disabled = isLoading;
    downloadBtn.textContent = isLoading ? 'Preparing...' : 'Download Labels';
  }

  function scrollToFirstArticle() {
    const firstArticle = document.querySelector('.about-story article');
    if (!firstArticle) return;
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    firstArticle.scrollIntoView({ behavior: prefersReduced ? 'auto' : 'smooth', block: 'start' });
  }

  async function runPrediction() {
    if (!photos.length) {
      showWarning('Upload at least one image first.');
      return;
    }

    setAnalyzeState(true);
    const fd = new FormData();
    photos.forEach((p) => {
      if (p.file) fd.append('images', p.file, p.file.name);
    });

    try {
      const res = await fetch('/api/predict', { method: 'POST', body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || 'Prediction failed.');
      }
      const data = await res.json();
      if (typeof data.sweetness !== 'number') {
        throw new Error('Invalid response from server.');
      }
      if (data.detected === false) {
        showWarning('No watermelon detected. Try a clearer image.');
      }
      if (typeof window.setSweetnessScore === 'function') {
        window.setSweetnessScore(data.sweetness);
        if (Number(data.sweetness) === 0) {
          scrollToFirstArticle();
        }
      }
    } catch (err) {
      showWarning(err.message || 'Prediction failed.');
    } finally {
      setAnalyzeState(false);
    }
  }

  async function runDownload() {
    if (!photos.length) {
      showWarning('Upload at least one image first.');
      return;
    }

    setDownloadState(true);
    const fd = new FormData();
    photos.forEach((p) => {
      if (p.file) fd.append('images', p.file, p.file.name);
    });

    try {
      const res = await fetch('/api/annotate', { method: 'POST', body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || 'Download failed.');
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'labeled_images.zip';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      showWarning(err.message || 'Download failed.');
    } finally {
      setDownloadState(false);
    }
  }

  // Upload flow
  uploadInput.addEventListener('change', () => {
    addFiles(uploadInput.files);
    uploadInput.value = '';
  });

  // Edit flow (click image to replace)
  editInput.addEventListener('change', () => {
    const file = editInput.files && editInput.files[0];
    if (editingId && file) replacePhoto(editingId, file);
    editingId = null;
    editInput.value = '';
  });

  // Expose global click handler because your HTML uses onclick="handleUploadClick()".
  window.handleUploadClick = function handleUploadClick() {
    uploadInput.value = '';
    uploadInput.click();
  };

  async function loadTestImages() {
    const urls = [
      '/test/DSC_0516.JPG',
      '/test/DSC_0517.JPG',
      '/test/DSC_0518.JPG'
    ];

    try {
      const files = await Promise.all(urls.map(async (url) => {
        const res = await fetch(url);
        if (!res.ok) throw new Error('Failed to load test images.');
        const blob = await res.blob();
        const name = url.split('/').pop() || 'test.jpg';
        const type = blob.type || 'image/jpeg';
        return new File([blob], name, { type });
      }));
      clearAllPhotos();
      addFiles(files);
    } catch (err) {
      showWarning(err.message || 'Failed to load test images.');
    }
  }

  function scrollToUploadButton() {
    const target = document.querySelector('.button-upload, .buttons-upload, .button-component');
    if (!target) return;
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    target.scrollIntoView({ behavior: prefersReduced ? 'auto' : 'smooth', block: 'center' });
  }

  function updatePoetryText() {
    const poetry = document.querySelector('.poetry-text p');
    if (!poetry) return;
    poetry.textContent = 'Be sure to upload the photos from the same watermelon, and Whole Watermelons...';
  }

  const ctaTestBtn = document.querySelector('.cta-test');
  if (ctaTestBtn) {
    ctaTestBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      updatePoetryText();
      loadTestImages().then(scrollToUploadButton);
    });
  }

  analyzeBtn.addEventListener('click', runPrediction);
  downloadBtn.addEventListener('click', runDownload);

  updateHintVisibility();
})();
(() => {
  const MAX = 14;

  const bar = document.querySelector(".progress-bar");
  const fill = bar?.querySelector(".progress-bar-fill");
  if (!bar || !fill) return;

  // Ensure fill scales from bottom
  fill.style.transformOrigin = "50% 100%";
  fill.style.willChange = "transform";

  // Create moving indicator dot
  const dot = document.createElement("div");
  dot.className = "progress-indicator-dot";
  Object.assign(dot.style, {
    position: "absolute",
    left: "50%",
    width: "14px",
    height: "14px",
    borderRadius: "99px",
    transform: "translate(-50%, -50%)",
    background: "#000",
    pointerEvents: "none",
    zIndex: "5",
  });
  bar.appendChild(dot);

  // Create moving "title-text" label
  const label = document.createElement("div");
  label.className = "progress-indicator-label";
   Object.assign(label.style, {
    position: "absolute",
    right: "-360px",          // label to the left of the bar; tweak if needed
    width: "330px", 
    transform: "translateY(-50%)",
    fontFamily: "'IBM Plex Mono', monospace",
    fontWeight: "670",
    fontSize: "27px", 
    lineHeight: "1.2",
    whiteSpace: "pre-line",
    color: "#FCF9EF",
    pointerEvents: "none",
    zIndex: "5",
    textAlign: "Left",
  });
  bar.appendChild(label);

  let currentP = 1;
  let defaultMode = true;
  let rafId = 0;

  const clamp01 = (x) => Math.max(0, Math.min(1, x));
  const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);

  function getFillGeometry() {
    const cs = getComputedStyle(fill);
    const topPx = parseFloat(cs.top) || 0;       // usually 0
    const bottomPx = parseFloat(cs.bottom) || 0; // your CSS uses 3.05% -> resolves to px
    const barH = bar.clientHeight;

    // The fill element occupies barH - top - bottom
    const usableH = Math.max(0, barH - topPx - bottomPx);

    return { topPx, bottomPx, usableH, barH };
  }

  function apply(p, scoreText) {
  p = clamp01(p);

  // Fill from bottom using height
  fill.style.height = `${p * 100}%`;

  // Indicator position: top of the filled region
  const barH = bar.clientHeight;
  const yTopOfFill = barH - (p * barH); // 0% => bottom, 100% => top

  dot.style.top = `${yTopOfFill}px`;
  label.style.top = `${yTopOfFill}px`;
  label.textContent = scoreText;
}

  function animateTo(targetP, scoreText) {
  currentP = clamp01(targetP);
  apply(currentP, scoreText);
}

  const melon = document.querySelector(".illustration-melon");
  const footer_melon = document.querySelector(".footer-upper-content .illustration-melon");

function setMelonIconByPercent(p) {
  if (!melon) return;
  if (!footer_melon) return;

  let idx = 0;
  if (p < 0.05) idx = 0; //default
  else if (p < 0.25) idx = 1; // below average
  else if (p < 0.50) idx = 2; // around average
  else if (p < 0.75) idx = 3; // above average
  else idx = 4; // perfect sweetness

  melon.style.backgroundImage = `url('assets/icons${idx}.png')`;
  footer_melon.style.backgroundImage = `url('assets/icons${idx}.png')`;
  melon.style.backgroundRepeat = "no-repeat";
  melon.style.backgroundPosition = "center";
  melon.style.backgroundSize = "contain";
}
function spinMelon() {
  if (!melon) return;
  melon.classList.remove("spin");
  void melon.offsetWidth;         // force reflow so animation restarts
  melon.classList.add("spin");
}

  // Public API: call this when you get your model output (0..14)
  function getSweetnessLabel(score) {
    if (score < 2) return "You Are Sure That is a Watermelon Right?";
    if (score < 5) return "Eat a Lemon at this point";
    if (score < 8) return "It's ok... but we can definitly find somthing better";
    if (score < 11) return "This is good... if you want to settle for average";
    return "GRAB IT! GRAB IT!";
  }

  window.setSweetnessScore = function setSweetnessScore(score) {
    defaultMode = false;

    const s = Math.max(0, Math.min(MAX, Number(score) || 0));
    const p = s / MAX;
    const label = getSweetnessLabel(s);
    const brixText = Number.isFinite(s) ? s.toFixed(2) : "0.00";

    setMelonIconByPercent(p);
    spinMelon();

    const scoreText = `${brixText}(Brix)\n${label}`;
    animateTo(p, scoreText);
  };

function setDefaultProgressPose() {
  defaultMode = true;
  fill.style.height = "100%";
  currentP = 1;

  const barH = bar.clientHeight;
  dot.style.top = `${barH}px`;
  label.style.top = `${barH}px`;
  label.textContent = "";
}




  // Keep label aligned if window resizes
  window.addEventListener("resize", () => {
    if (defaultMode) setDefaultProgressPose();
    else apply(currentP, label.textContent || "");
  });
  // Optional initial state
  setDefaultProgressPose();
  

})();


