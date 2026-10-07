// Extracteur générique d'annonces à partir du HTML d'une page de résultats.
// Exécuté DANS le navigateur (DOMParser) : repère les liens d'annonces (regex propre au site),
// remonte jusqu'au plus grand bloc qui ne contient qu'une annonce (la « carte »),
// puis lit prix, km, année, carburant, boîte, titre, image dans ce bloc.
(args) => {
  const [html, base, reSrc, marque] = args;
  const mq = (marque || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const low = (t) => t.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const re = new RegExp(reSrc);
  const doc = new DOMParser().parseFromString(html, 'text/html');
  doc.querySelectorAll('script,style,noscript,svg,template').forEach(e => e.remove());
  const NON_PHOTO = /efficiency|logo|icon|picto|badge|label|sprite|flag|\.svg(\?|$)|placeholder|novisu/i;
  // Toutes les images citées dans le HTML brut (y compris le JSON échappé des pages React) :
  // sert à retrouver la photo d'une carte dont l'image n'est chargée qu'en JavaScript.
  const IMAGES = (html.replace(/\\u002F/gi, '/').replace(/\\\//g, '/').match(/https?:\/\/[^"'\s\\<>()]+?\.(?:jpe?g|png|webp|avif)(?:\?[^"'\s\\<>()]*)?/gi) || []).filter(u => !NON_PHOTO.test(u));
  const imageParId = (lien) => {
    const j = (lien.match(/[A-Za-z0-9]+/g) || []).filter(t => t.length >= 6 && /\d/.test(t)).map(t => t.toLowerCase());
    const cands = (j.length >= 2 ? [j[j.length - 2] + j[j.length - 1]] : []).concat([...j].reverse().filter(t => t.length >= 8));
    for (const c of cands) { const u = IMAGES.find(x => x.toLowerCase().includes(c)); if (u) return u.replace(/_small\.(jpe?g|webp|png)/i, '_medium.$1'); }
    return null;
  };
  const abs = (h) => { try { return new URL(h, base).href.split('#')[0]; } catch (e) { return null; } };
  const linksOf = (el) => { const s = new Set(); for (const a of el.querySelectorAll('a[href]')) { const h = abs(a.getAttribute('href')); if (h && re.test(h)) s.add(h); if (s.size > 1) break; } return s; };
  const parts = (el) => { const out = []; const w = doc.createTreeWalker(el, NodeFilter.SHOW_TEXT); let n; while ((n = w.nextNode())) { const t = n.nodeValue.replace(/[  ]/g, ' ').replace(/\s+/g, ' ').trim(); if (t) out.push(t); } return out; };
  const num = (s) => +String(s).replace(/\D/g, '');
  const NB = '(\\d{1,3}(?:[ .]\\d{3})+|\\d{1,7})';
  const DATE_COMPLETE = /\b\d{1,2}[\/.-]\d{1,2}[\/.-](?:19|20)\d{2}\b/;
  const YEAR = /(?:^|ann[ée]e\s*:?\s*|mill[ée]sime\s*:?\s*|mec\s*:?\s*|circulation\s*:?\s*|\b\d{1,2}[\/.-])((?:19[89]|20[0-3])\d)\b/i;
  const FUEL = [[/hybride|hybrid|e-tech|\bhev\b|\bphev\b/i, 'Hybride'], [/[ée]lectrique|electric|\bev\b/i, 'Électrique'],
                [/diesel|gazole/i, 'Diesel'], [/essence|petrol|benzin/i, 'Essence'], [/\bgpl\b|gnv|[ée]thanol/i, 'GPL / autre']];
  const by = new Map();
  for (const a of doc.querySelectorAll('a[href]')) { const h = abs(a.getAttribute('href')); if (h && re.test(h) && !by.has(h)) by.set(h, a); }
  const res = [];
  for (const [href, a] of by) {
    let card = a;
    while (card.parentElement && card.parentElement !== doc.body && linksOf(card.parentElement).size === 1) card = card.parentElement;
    const P = parts(card);
    let prix = null, km = null, annee = null, carburant = null, boite = null;
    for (let i = 0; i < P.length; i++) {
      const p = P[i], suivant = P[i + 1] || '';
      if (prix == null && !/mois|mensualit|loyer|remise|[ée]conom|r[ée]duction|^-|neuf|initial/i.test(p + ' ' + suivant.slice(0, 8))) {
        let m = p.match(new RegExp(NB + '\\s?(€|EUR)'));
        if (!m && /^(€|EUR)$/.test(suivant)) m = p.match(new RegExp('^' + NB + '$'));   // « 12 490 | € »
        if (m && num(m[1]) >= 300) prix = num(m[1]);
      }
      if (km == null) {
        let m = p.match(new RegExp(NB + '\\s?km\\b', 'i'));
        if (!m && /^km\b/i.test(suivant)) m = p.match(new RegExp('^' + NB + '$'));      // « 58 000 | km »
        if (m) km = num(m[1]);
      }
      if (annee == null && !/€|km\b/i.test(p) && !DATE_COMPLETE.test(p)) {
        let m = p.match(YEAR);
        if (!m && /^(ann[ée]e|mill[ée]sime|mise en circulation)\s*:?$/i.test(P[i - 1] || '')) m = p.match(/^((?:19[89]|20[0-3])\d)$/);
        if (m) annee = +m[1];
      }
      if (!carburant && p.length < 40) { const f = FUEL.find(([rx]) => rx.test(p)); if (f) carburant = f[1]; }
      if (!boite && p.length < 40) { if (/automatique|\bauto\b|\bbva\b|\beat\s?\d/i.test(p) && !/clim/i.test(p)) boite = 'Automatique'; else if (/manuelle|\bbvm\b/i.test(p)) boite = 'Manuelle'; }
    }
    const img = [...card.querySelectorAll('img')].find(i => !NON_PHOTO.test((i.getAttribute('data-src') || '') + (i.getAttribute('src') || ''))) || null;
    let src = img && (img.getAttribute('data-src') || img.getAttribute('data-lazy-src') || img.getAttribute('src') || (img.getAttribute('srcset') || '').split(' ')[0]);
    if (src && src.startsWith('data:')) src = null;
    if (!src) for (const s of card.querySelectorAll('source')) {   // <picture><source srcset> sans <img> exploitable
      const v = (s.getAttribute('srcset') || s.getAttribute('data-srcset') || '').split(',')[0].trim().split(' ')[0];
      if (v && !v.startsWith('data:') && !NON_PHOTO.test(v)) { src = v; break; }
    }
    if (!src) for (const el of [card, ...card.querySelectorAll('[style]')]) {  // image de fond
      const m = (el.getAttribute('style') || '').match(/url\(['"]?([^'")]+)/);
      if (m && !m[1].startsWith('data:') && !NON_PHOTO.test(m[1])) { src = m[1]; break; }
    }
    // Titre : le titre de la carte s'il cite la marque ; sinon la 1re ligne qui cite la marque,
    // complétée par les lignes suivantes (modèle, version) jusqu'aux caractéristiques.
    const STOP = /€|\bkm\b|kilom|ann[ée]e|bo[iî]te|[ée]nergie|carburant|mois|garantie|^\d{4}$|^\d{1,2}[\/.-]\d{4}$|^(essence|diesel|hybride|[ée]lectrique|manuelle|automatique)$/i;
    const suite = (i) => { const out = [P[i]]; for (let k = i + 1; k < P.length && out.length < 4; k++) { if (STOP.test(P[k]) || P[k].length > 90) break; if (/^[•|·\-–]+$/.test(P[k])) continue; out.push(P[k]); } return out.join(' '); };
    const hh = card.querySelector('h1,h2,h3,h4');
    let titre = ((hh && hh.textContent) || '').replace(/\s+/g, ' ').trim();
    if (!titre || (mq && !low(titre).includes(mq))) {
      let i = mq ? P.findIndex(p => low(p).includes(mq) && p.length < 120) : -1;
      if (i >= 0) titre = suite(i);
      else if (!titre) titre = (a.getAttribute('title') || (img && img.alt) || '').replace(/\s+/g, ' ').trim();
      if (!titre) { const j = P.findIndex(p => /[a-z]{3}/i.test(p) && p.length > 5 && !STOP.test(p)); titre = j >= 0 ? suite(j) : 'Annonce'; }
    } else if (titre.length < 22) {
      const i = P.findIndex(p => p.includes(titre) || titre.includes(p));
      if (i >= 0) {
        const t2 = suite(i);
        if (t2.length > titre.length && t2.length < 140) titre = t2.includes(titre) ? t2 : titre + ' ' + t2;
        else { // version placée après le prix (« Peugeot 208 | 11 190 € | 1.2 PureTech Style »)
          const v = P.slice(i + 1, i + 5).find(p => /[a-z]{2}/i.test(p) && p.length > 3 && p.length < 90 && !STOP.test(p) && !titre.includes(p));
          if (v) titre = titre + ' ' + v;
        }
      }
    }
    res.push({ lien: href, titre: titre.replace(/\s*\|\s*/g, ' ').slice(0, 140), prix, km, annee, carburant, boite,
               image: src ? abs(src) : imageParId(href), texte: P.join(' | ').slice(0, 900) });
  }
  return { annonces: res };
}
