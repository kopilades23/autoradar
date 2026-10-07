// Lecture générique d'une fiche annonce (HTML) : description + équipements.
// Priorité : JSON-LD (Vehicle/Car/Product.description), puis le bloc de texte le plus
// « dense » de la page (peu de liens, beaucoup de texte), puis listes d'équipements.
(args) => {
  const [html, lien] = args;
  // Pages React (ex. Renew) : options/équipements du véhicule dans le JSON embarqué, autour de son identifiant
  const equipementsJson = () => {
    const m = (lien || '').match(/[?&]productId=([^&#]+)/); if (!m) return [];
    const u = html.replace(/\\"/g, '"').replace(/\\u002F/g, '/');
    const cle = '"productId":"' + m[1] + '"';
    for (let i = u.indexOf(cle); i >= 0; i = u.indexOf(cle, i + 1)) {   // 1re occurrence qui a des données
      const avant = u.lastIndexOf('"productId":"', i - 1), apres = u.indexOf('"productId":"', i + cle.length);
      const opts = [...u.slice(Math.max(avant, 0, i - 30000), i).matchAll(/"options":\[(.*?)\]/g)].slice(-1);
      const eqs = [...u.slice(i, apres > 0 ? apres : i + 60000).matchAll(/"equipments":\[(.*?)\]/g)].slice(0, 1);
      const out = [...opts, ...eqs].flatMap(a => [...a[1].matchAll(/"description":"([^"]{3,120})"/g)].map(x => x[1]));
      if (out.length) return out;
    }
    return [];
  };
  // Date de mise en ligne (AAAA-MM-JJ) : « Publiée le 08/09/2026 », JSON-LD, ou JSON embarqué près de l'identifiant
  const datePublication = () => {
    let m = (html || '').match(/publi[ée]e?\s+le(?:\s|&nbsp;|<[^>]{0,200}>)*(\d{1,2})\/(\d{1,2})\/(\d{4})/i);
    if (m) return `${m[3]}-${String(+m[2]).padStart(2, '0')}-${String(+m[1]).padStart(2, '0')}`;
    const u = (html || '').replace(/\\"/g, '"').replace(/\\u002F/g, '/');
    m = u.match(/"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})/); if (m) return m[1];
    const id = (lien || '').match(/[?&]productId=([^&#]+)/) || (lien || '').match(/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/);
    if (!id) return null;
    const CLES = /"(?:publicationDateTime|publicationDate|datePublished|createdTimestampWithOffset|created|createdAt|firstPublicationDate|first_publication_date)"\s*:\s*"(\d{4}-\d{2}-\d{2})/g;
    let meilleur = null, dist = 5001;
    for (let i = u.indexOf(id[1]); i >= 0; i = u.indexOf(id[1], i + 1)) {
      const debut = Math.max(0, i - 5000), zone = u.slice(debut, i + 5000);
      for (const d of zone.matchAll(CLES)) { const e = Math.abs(debut + d.index - i); if (e < dist) { meilleur = d[1]; dist = e; } }
    }
    return meilleur;
  };
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const txt = (el) => (el.textContent || '').replace(/[  ]/g, ' ').replace(/[ \t]+/g, ' ').replace(/\s*\n\s*/g, '\n').trim();
  let ld = '', image = null;
  for (const s of doc.querySelectorAll('script[type="application/ld+json"]')) {
    try {
      const walk = (o) => { if (!o || typeof o !== 'object') return; if (Array.isArray(o)) return o.forEach(walk);
        if (/vehicle|car|product|offer/i.test(String(o['@type']))) {
          if (typeof o.description === 'string' && o.description.length > ld.length) ld = o.description;
          let im = o.image; if (Array.isArray(im)) im = im[0]; if (im && typeof im === 'object') im = im.url;
          if (!image && typeof im === 'string' && im.startsWith('http')) image = im;
        }
        Object.values(o).forEach(walk); };
      walk(JSON.parse(s.textContent));
    } catch (e) {}
  }
  // Annonce « miroir » d'une autre plateforme (ex. L'argus reprend des annonces Leboncoin)
  const og = doc.querySelector('meta[property="og:image"]')?.getAttribute('content') || '';
  if (og.startsWith('http') && !/efficiency|logo|icon|picto|badge|label|sprite|flag|\.svg(\?|$)|placeholder|novisu/i.test(og)) image = og;
  let miroir = null, miroir_lien = null;
  for (const a of doc.querySelectorAll('a[href]')) {
    const h = a.getAttribute('href') || '';
    if (/leboncoin\.fr\/(ad|voitures)\//i.test(h)) { miroir = 'Leboncoin'; miroir_lien = h.split('#')[0]; break; }
    if (/lacentrale\.fr\/auto-occasion-annonce/i.test(h)) { miroir = 'La Centrale'; miroir_lien = h.split('#')[0]; break; }
  }
  doc.querySelectorAll('script,style,noscript,svg,header,footer,nav,aside,form,iframe,template').forEach(e => e.remove());
  // sauts de ligne entre blocs, sinon « Description » et le texte se collent
  doc.body.querySelectorAll('p,div,li,br,h1,h2,h3,h4,h5,h6,section,article,tr,dt,dd').forEach(e => e.append('\n'));
  let best = null, bestScore = 0;
  for (const el of doc.body.querySelectorAll('div,section,article,p')) {
    const brut = el.textContent || ''; if (brut.length < 120 || brut.length > 40000) continue;
    const t = txt(el); if (t.length < 120 || t.length > 15000) continue;
    const lt = [...el.querySelectorAll('a')].reduce((s, a) => s + (a.textContent || '').length, 0);
    const score = t.length - 4 * lt - 0.5 * el.querySelectorAll('div,section').length * 10;
    if (lt / t.length < 0.25 && score > bestScore && !/cookie|consentement/i.test(t.slice(0, 200))) { best = el; bestScore = score; }
  }
  const equip = [];
  for (const h of doc.body.querySelectorAll('h2,h3,h4,h5,dt,strong')) {   // listes sous un titre « Équipements / Options »
    if (!/[ée]quipement|options?\b|[ée]quipé/i.test(h.textContent || '') || (h.textContent || '').length > 60) continue;
    const zone = h.parentElement && h.parentElement.querySelectorAll('li').length ? h.parentElement : (h.parentElement && h.parentElement.parentElement);
    if (zone) zone.querySelectorAll('li').forEach(li => { const t = txt(li); if (t.length > 2 && t.length < 80) equip.push(t); });
  }
  let corps = '';
  if (best) { const c = best.cloneNode(true); c.querySelectorAll('h1,h2,h3,h4,h5,h6,button').forEach(e => e.remove()); corps = txt(c); }
  const description = [ld, corps].filter(Boolean).join('\n').slice(0, 12000);
  equip.push(...equipementsJson());
  return { description, equipements: [...new Set(equip)].slice(0, 300), miroir, miroir_lien, image, date: datePublication() };
}
