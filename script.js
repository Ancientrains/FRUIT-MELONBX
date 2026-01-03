
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

  function showWarning(msg) {
    warning.textContent = msg;
    warning.style.display = 'block';
    clearTimeout(showWarning._t);
    showWarning._t = setTimeout(() => (warning.style.display = 'none'), 2500);
  }

  function updateHintVisibility() {
    hint.style.display = photos.length ? 'none' : 'block';
    syncUploadButton();
  }
  function layoutStack() {
  // You can customize these per image (index 0,1,2)
  const poses = [
    { x: 30,  y: 80,  r: -10, z: 3 }, // photo #1
    { x: 240,  y: 155,  r:  8,  z: 2 }, // photo #2
    { x: 480, y: 100,  r: -2,  z: 1 }, // photo #3
  ];

  photos.forEach((p, i) => {
    const pose = poses[i] || poses[poses.length - 1];
    p.el.style.left = "0px";
    p.el.style.top = "0px";
    p.el.style.zIndex = String(pose.z);
    p.el.style.transform = `translate(${pose.x}px, ${pose.y}px) rotate(${pose.r}deg)`;
  });
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

  updateHintVisibility();
})();
