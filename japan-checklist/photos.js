'use strict';
// Every photograph is selected before deployment and served by this site.
// No third-party image search or image request runs here.
window.JapanPhotos = (() => {
  const groups = [[1,'hokkaido'],[7,'tohoku'],[14,'kanto'],[19,'hokuriku'],[24,'tokai'],[30,'kansai'],[35,'chugoku'],[39,'shikoku'],[46,'kyushu'],[47,'okinawa']];
  const catalogues = new Map();
  let observer = null, fallbackObserver = null;
  function regionFor(id) {
    const match = /^JP(\d{2})-\d{2}$/.exec(id || '');
    const n = match ? Number(match[1]) : 0;
    return n > 0 && n <= 47 ? groups.find(([end]) => n <= end)[1] : '';
  }
  function localPath(id, path) {
    return typeof path === 'string' && !!regionFor(id) && new RegExp('^images/' + regionFor(id) + '/' + id + '\\.(jpg|png|webp)$').test(path);
  }
  function validSource(value) {
    try { const u = new URL(value); return u.protocol === 'https:' && u.hostname === 'commons.wikimedia.org'; } catch { return false; }
  }
  function load(region) {
    if (!catalogues.has(region)) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 15000);
      const promise = fetch(`${region}-photos.json?v=all-static-1`, {credentials:'same-origin', signal:controller.signal})
        .then(r => { if (!r.ok) throw new Error('Photo catalogue unavailable'); return r.json(); })
        .then(data => {
          if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('Invalid photo catalogue');
          const valid = Object.create(null);
          for (const [id, photo] of Object.entries(data)) {
            if (regionFor(id) === region && photo && localPath(id, photo.src) && validSource(photo.source) && typeof photo.author === 'string' && typeof photo.license === 'string') valid[id] = photo;
          }
          return valid;
        }).catch(() => Object.create(null)).finally(() => clearTimeout(timer));
      catalogues.set(region, promise);
    }
    return catalogues.get(region);
  }
  function show(card, photo) {
    if (!card.isConnected) return;
    const img = card.querySelector('.thumb'), fallback = card.querySelector('.thumb-fallback'), credit = card.querySelector('.photo-credit');
    const id = card.dataset.id;
    const fail = () => {
      img.hidden = true; credit.hidden = true; fallback.hidden = false;
      fallback.textContent = '照片載入失敗，請重新整理。';
      fallback.setAttribute('aria-label', `${card.querySelector('.spot-name').textContent}：照片載入失敗`);
      card.querySelector('.photo-note')?.remove();
    };
    if (!photo || !localPath(id, photo.src)) { fail(); return; }
    const region = regionFor(id);
    credit.href = `${region === 'hokkaido' ? 'photo-credits.html' : 'photo-credits-' + region + '.html'}#${id}`;
    credit.textContent = `${photo.author} · ${photo.license}`;
    credit.title = `${photo.author} · ${photo.license} · ${photo.caption || '點選查看原圖、授權與縮圖說明'}`;
    img.style.objectFit = photo.fit === 'contain' ? 'contain' : 'cover';
    if (photo.caption) img.alt = `${card.querySelector('.spot-name').textContent}：${photo.caption}`;
    img.onload = () => {
      img.hidden = false; fallback.hidden = true; credit.hidden = false;
      if (photo.note && !card.querySelector('.photo-note')) {
        const note = document.createElement('span'); note.className = 'photo-note';
        note.textContent = photo.note; note.title = photo.caption || photo.note;
        note.style.cssText = 'position:absolute;top:8px;left:8px;right:8px;width:max-content;max-width:calc(100% - 16px);padding:3px 7px;background:rgba(255,253,249,.94);color:#493b32;font-size:11px;border-radius:5px;pointer-events:none';
        card.querySelector('.thumb-wrap').appendChild(note);
      }
    };
    img.onerror = fail; img.loading = 'eager'; img.decoding = 'async'; img.dataset.photoKind = 'fixed';
    img.src = new URL(photo.src, document.baseURI).href;
  }
  function attach(card) {
    if (!card.isConnected || card.dataset.photoRequested === 'yes') return;
    if (card.closest('.region-cards')?.hidden) { observer?.observe(card); return; }
    card.dataset.photoRequested = 'yes';
    const region = regionFor(card.dataset.id);
    if (!region) { show(card, null); return; }
    load(region).then(photos => show(card, photos[card.dataset.id]));
  }
  function disconnect() { observer?.disconnect(); observer = null; fallbackObserver?.disconnect(); fallbackObserver = null; }
  function observe(cards) {
    disconnect();
    if ('IntersectionObserver' in window) {
      observer = new IntersectionObserver(entries => {
        for (const entry of entries) if (entry.isIntersecting) { observer.unobserve(entry.target); attach(entry.target); }
      }, {rootMargin:'240px 0px'});
      cards.forEach(card => observer.observe(card));
    } else {
      const refresh = () => cards.forEach(card => { if (!card.closest('.region-cards')?.hidden) attach(card); });
      refresh(); fallbackObserver = new MutationObserver(refresh);
      const root = document.getElementById('cards');
      if (root) fallbackObserver.observe(root, {subtree:true,attributes:true,attributeFilter:['hidden']});
    }
  }
  return {observe, disconnect};
})();
