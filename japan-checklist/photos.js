'use strict';
// Only request photos near the viewport; never fan out 700 network requests.
window.JapanPhotos = (() => {
  const CACHE_KEY = 'japan700-photo-cache-v3';
  const aliases = {'大通公園＋札幌電視塔':'大通公園','北海道廳舊本廳舍':'北海道庁旧本庁舎','白色戀人公園':'白い恋人パーク','小樽運河':'小樽運河','函館山':'函館山','美瑛青池':'青い池','富田農場':'ファーム富田','登別地獄谷':'地獄谷 (登別市)','東京晴空塔':'東京スカイツリー','東京迪士尼樂園':'東京ディズニーランド','東京迪士尼海洋':'東京ディズニーシー','伏見稻荷大社':'伏見稲荷大社','沖繩美麗海水族館':'沖縄美ら海水族館'};
  let cache = {}, observer = null, running = 0, queue = [];
  const inFlight = new Map();
  try { const v = JSON.parse(sessionStorage.getItem(CACHE_KEY) || '{}'); if (v && typeof v === 'object' && !Array.isArray(v)) cache = v; } catch {}
  const text = html => new DOMParser().parseFromString(String(html || ''), 'text/html').body.textContent.trim();
  function safeURL(value, host) {
    try { const u = new URL(value); return u.protocol === 'https:' && u.hostname === host ? u.href : ''; } catch { return ''; }
  }
  async function api(host, params) {
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 7000);
    try {
      const url = `https://${host}/w/api.php?` + new URLSearchParams({action:'query',format:'json',formatversion:'2',origin:'*',...params});
      const r = await fetch(url, {signal:controller.signal,credentials:'omit',referrerPolicy:'no-referrer'});
      if (!r.ok) throw new Error('Photo request failed');
      const data = await r.json(); if (data.error) throw new Error('Photo API error'); return data;
    } finally { clearTimeout(timer); }
  }
  async function creditFor(filename) {
    const data = await api('commons.wikimedia.org', {prop:'imageinfo', titles:`File:${filename}`, iiprop:'url|extmetadata', iiurlwidth:'640', iiextmetadatafilter:'Artist|LicenseShortName|LicenseUrl|Attribution'});
    const info = data.query?.pages?.[0]?.imageinfo?.[0];
    if (!info) return null;
    const src = safeURL(info.thumburl || info.url, 'upload.wikimedia.org');
    const source = safeURL(info.descriptionurl, 'commons.wikimedia.org');
    const meta = info.extmetadata || {};
    const license = text(meta.LicenseShortName?.value);
    const author = text(meta.Attribution?.value || meta.Artist?.value) || 'Wikimedia Commons';
    // Do not display unknown or non-free image licenses.
    if (!src || !source || !/^(CC|Public domain|PDM|GFDL)/i.test(license)) return null;
    return {src, source, author, license};
  }
  async function lookup(spot) {
    const exact = String(spot.name).trim();
    const clean = exact.replace(/（[^）]*）|\([^)]*\)/g, '').trim();
    const base = clean.split(/[＋+／/]/)[0].trim();
    const variants = [...new Set([exact, clean, base])].filter(Boolean).slice(0,3);
    for (const lang of ['ja','zh']) {
      const titles = lang === 'ja' && aliases[exact] ? [aliases[exact]] : variants;
      const data = await api(`${lang}.wikipedia.org`, {prop:'pageimages|pageprops', titles:titles.join('|'), redirects:'1', converttitles:'1', piprop:'name|thumbnail', pithumbsize:'640', pilicense:'free'});
      const pages = data.query?.pages || [];
      for (const page of pages) {
        if (page.missing || !page.pageimage || page.pageprops?.disambiguation !== undefined) continue;
        const result = await creditFor(page.pageimage);
        if (result) return result;
      }
    }
    return null;
  }
  function getPhoto(spot) {
    const old = cache[spot.id];
    if (old && Date.now() - old.at < (old.photo ? 7*86400000 : 600000)) return Promise.resolve(old.photo);
    if (inFlight.has(spot.id)) return inFlight.get(spot.id);
    const promise = lookup(spot).catch(() => null).then(photo => {
      cache[spot.id] = {at:Date.now(),photo};
      try { sessionStorage.setItem(CACHE_KEY, JSON.stringify(cache)); } catch {}
      inFlight.delete(spot.id); return photo;
    });
    inFlight.set(spot.id, promise); return promise;
  }
  function show(card, photo) {
    if (!card.isConnected) return;
    const fallback = card.querySelector('.thumb-fallback'), img = card.querySelector('.thumb'), credit = card.querySelector('.photo-credit');
    const src = photo && safeURL(photo.src, 'upload.wikimedia.org');
    const source = photo && safeURL(photo.source, 'commons.wikimedia.org');
    const fail = () => { img.hidden = true; credit.hidden = true; fallback.hidden = false; fallback.textContent = '尚無照片／暫時無法載入'; fallback.setAttribute('aria-label', `${card.querySelector('.spot-name').textContent}：尚無照片`); };
    if (!src || !source) { fail(); return; }
    img.onload = () => { img.hidden = false; fallback.hidden = true; credit.hidden = false; };
    img.onerror = fail;
    credit.href = source;
    credit.textContent = `${photo.author} · ${photo.license}`;
    credit.title = `${photo.author} · ${photo.license} · 已裁切顯示；點選查看原圖與授權`;
    // IntersectionObserver already controls laziness; a hidden lazy image never loads.
    img.loading = 'eager'; img.referrerPolicy = 'no-referrer'; img.src = src;
  }
  function pump() {
    while (running < 3 && queue.length) {
      const {card, spot} = queue.shift();
      if (!card.isConnected || card.closest('.region-cards')?.hidden) { if (observer && card.isConnected) observer.observe(card); continue; }
      running++;
      getPhoto(spot).then(photo => show(card, photo)).finally(() => { running--; pump(); });
    }
  }
  function disconnect() { observer?.disconnect(); queue = []; }
  function observe(cards, byId) {
    disconnect();
    if ('IntersectionObserver' in window) {
      observer = new IntersectionObserver(entries => {
        for (const entry of entries) if (entry.isIntersecting) {
          observer.unobserve(entry.target);
          const spot = byId.get(entry.target.dataset.id);
          if (spot) queue.push({card:entry.target, spot});
        }
        pump();
      }, {rootMargin:'200px 0px'});
      cards.forEach(card => observer.observe(card));
    } else {
      // Older browsers still get a bounded queue; collapsed sections stay unloaded.
      cards.forEach(card => { if (!card.closest('.region-cards')?.hidden) queue.push({card,spot:byId.get(card.dataset.id)}); }); pump();
    }
  }
  return {observe, disconnect};
})();
