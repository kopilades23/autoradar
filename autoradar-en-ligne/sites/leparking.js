// LeParking.fr : moteur qui référence déjà les annonces de nombreux sites (dont Leboncoin et
// La Centrale). Sa page de résultats est alimentée par POST /index.php (champ « ajax » = contexte
// JSON : texte recherché, critères, curseurs prix/km/année, page, tri). Exécuté DANS l'onglet LeParking.
async (args) => {
  const [ctx] = args;
  const ctl = new AbortController(); setTimeout(() => ctl.abort(), 20000);
  let r;
  try {
    r = await fetch('/index.php', { method: 'POST', credentials: 'include', signal: ctl.signal,
      headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'X-Requested-With': 'XMLHttpRequest' },
      body: 'ajax=' + encodeURIComponent(JSON.stringify(ctx)) });
  } catch (e) { return { status: 0 }; }
  if (r.status >= 400) return { status: r.status };
  let j = await r.text();
  for (let k = 0; k < 3 && typeof j === 'string'; k++) { try { j = JSON.parse(j); } catch (e) { break; } }
  if (!j || typeof j !== 'object') return { status: 403 };
  const doc = new DOMParser().parseFromString(j['#lists'] || '', 'text/html');
  const num = (s) => +String(s || '').replace(/\D/g, '');
  const annonces = [];
  for (const li of doc.querySelectorAll('li.li-result')) {
    const parts = []; const w = doc.createTreeWalker(li, NodeFilter.SHOW_TEXT); let n;
    while ((n = w.nextNode())) { const t = n.nodeValue.replace(/[  ]/g, ' ').replace(/\s+/g, ' ').trim(); if (t) parts.push(t); }
    if (parts.some(p => /^sponsoris/i.test(p))) continue;   // annonces sponsorisées (souvent hors France)
    const ext = li.querySelector('a.external[name]');
    const detail = li.querySelector('[data-url]')?.getAttribute('data-url') || '';
    const lien = ext?.getAttribute('href') || detail;
    if (!lien) continue;
    const titre = [...li.querySelectorAll('.sample-holder h2 .title-block')].map(e => e.textContent.replace(/\s+/g, ' ').trim()).join(' ').replace(/\s+4X2$/i, '');
    // Le « slug » de la fiche contient souvent la version complète (« …-1-5-bhdi-garantie-1an-focal-sound »)
    const version = (detail.split('/').slice(-2, -1)[0] || '').replace(/-/g, ' ');
    const iDet = parts.findIndex(p => /^d[ée]tail$/i.test(p));
    const specs = iDet >= 0 ? parts.slice(iDet + 1, iDet + 8) : parts;
    let km = null, annee = null, carburant = null, boite = null;
    for (const p of specs) {
      if (km == null && /km$/i.test(p)) km = num(p);
      else if (annee == null && /^(19|20)\d\d$/.test(p)) annee = +p;
      else if (!carburant && /^(essence|diesel|hybride|electrique|électrique|gpl|ethanol)/i.test(p)) carburant = p[0] + p.slice(1).toLowerCase();
      else if (!boite && /^(manuelle|automatique)/i.test(p)) boite = p[0] + p.slice(1).toLowerCase();
    }
    const img = li.querySelector('picture img')?.getAttribute('src') || '';
    annonces.push({
      lien: new URL(lien, location.origin).href, titre: titre || 'Annonce', version, detail,
      prix: num(li.querySelector('p.prix')?.textContent) || null, km, annee,
      carburant: carburant === 'Electrique' ? 'Électrique' : carburant, boite,
      image: img && !/visuel_generique/.test(img) ? new URL(img, location.origin).href : null,
      plateforme: (ext?.getAttribute('name') || '').replace(/^www\./, '') || null,
      vendeur: parts.find(p => /^(particulier|professionnel)$/i.test(p)) || null,
    });
  }
  return { status: 200, annonces, total: num(j.context && j.context.nb_results) };
}
