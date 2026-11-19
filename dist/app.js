const main = document.querySelector('#main');
const header = document.querySelector('#site-header');
const footer = document.querySelector('#site-footer');
const description = document.querySelector('meta[name="description"]');
const detailPrefix = '#/item/';
const toolIcons = {
  'asp.net': 'dotnet.svg',
  'azure devops': 'azuredevops.svg',
  'c': 'c.svg',
  'c#': 'csharp.svg',
  'cloudflare': 'cloudflare.svg',
  'expo': 'expo.svg',
  'git': 'git.svg',
  'google gemini api': 'googlegemini.svg',
  'javascript': 'javascript.svg',
  'mediapipe': 'mediapipe.svg',
  'microsoft azure': 'azure.svg',
  'mysql': 'mysql.svg',
  'next.js': 'nextdotjs.svg',
  'postgresql': 'postgresql.svg',
  'python': 'python.svg',
  'react': 'react.svg',
  'react native': 'react.svg',
  'react native cli': 'react.svg',
  'redux': 'redux.svg',
  'rust': 'rust.svg',
  'sql': 'sql.svg',
  'sql server': 'microsoftsqlserver.svg',
  'supabase': 'supabase.svg',
  'tauri': 'tauri.svg',
  'tensorflow lite (tflite)': 'tensorflow.svg',
  'testflight': 'testflight.png',
  'xcode': 'xcode.svg',
  'pandas': 'pandas.svg',
  'scikit-learn': 'scikitlearn.svg'
};
const positions = new Map();
let currentView;
let currentEntry;
let entryNumber = 0;
let cleanupGuide;
let portfolio;
let records;
let mountGuide;
let ignorePosition = false;

const itemHref = id => detailPrefix + encodeURIComponent(id);
const sectionHref = section => '#' + encodeURIComponent(section.id);

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text) element.textContent = text;
  return element;
}

function add(parent, ...children) {
  parent.append(...children.filter(Boolean));
  return parent;
}

function optional(tag, className, text) {
  return text ? node(tag, className, text) : null;
}

function toolItem(technology) {
  const item = node('li');
  const icon = toolIcons[technology.trim().toLowerCase()];
  if (icon) {
    const image = node('img', 'tool-icon');
    image.src = './assets/tools/' + icon;
    image.alt = '';
    image.width = 18;
    image.height = 18;
    item.append(image);
  }
  item.append(document.createTextNode(technology));
  return item;
}

function link(label, href, className, symbol) {
  const anchor = node('a', className, label);
  anchor.href = href;
  if (symbol) {
    const arrow = node('span', 'link-arrow', symbol);
    arrow.setAttribute('aria-hidden', 'true');
    anchor.append(arrow);
  }
  return anchor;
}

function action(source, className, symbol = '↗') {
  if (!source?.label || !source.url) return null;
  const anchor = link(source.label, source.url, className, symbol);
  if (source === portfolio.profile.cv && anchor.origin === location.origin) {
    anchor.download = '';
    anchor.querySelector('.link-arrow').textContent = '↓';
  }
  return anchor;
}

function renderHeader() {
  const { profile, ui = {} } = portfolio;
  const home = link(profile.name, '#top', 'wordmark');
  home.setAttribute('aria-label', ui.homeLabel ?? profile.name + ', home');
  if (ui.skipLink) document.querySelector('.skip').textContent = ui.skipLink;
  if (profile.initials) home.prepend(node('span', 'monogram', profile.initials));
  const nav = node('nav', 'main-nav');
  nav.setAttribute('aria-label', ui.navLabel ?? 'Main navigation');
  for (const item of ui.nav ?? []) nav.append(link(item.label, item.href));
  add(header, home, nav, action(profile.cv, 'header-cv', '↗'));
  add(footer, add(node('div', 'frame footer-inner'),
    node('span', '', ui.copyright ?? profile.name),
    ui.backToTop && link(ui.backToTop, '#top', 'footer-top', '↑')));
  footer.hidden = false;
}

function media(item, className, eager = false) {
  if (!item.image?.src) return null;
  const figure = node('figure', className);
  const image = node('img');
  image.src = item.image.src;
  image.alt = item.image.alt ?? '';
  image.loading = eager ? 'eager' : 'lazy';
  image.decoding = 'async';
  return add(figure, image, optional('figcaption', '', item.image.caption));
}

function productCard(item, ui) {
  const actions = node('div', 'product-actions');
  const label = ui.productsAction ?? 'View project';
  const details = link(label, itemHref(item.id), 'button button-primary product-detail', '→');
  details.setAttribute('aria-label', label + ': ' + item.title);
  add(actions, details, action(item.links?.[0], 'text-link'));
  return add(node('article', 'product-card'),
    media(item, 'product-media', true),
    add(node('div', 'product-body'),
      optional('p', 'meta platform-label', item.subtitle),
      node('h3', '', item.title),
      optional('p', 'product-summary', item.summary),
      actions));
}

function timelineRow(item) {
  const row = link('', itemHref(item.id), 'timeline-link');
  const arrow = node('span', 'row-arrow', '→');
  arrow.setAttribute('aria-hidden', 'true');
  add(row,
    node('span', 'meta row-date', item.period),
    add(node('div', 'row-copy'),
      add(node('h3', 'row-title', item.title), optional('span', 'row-subtitle', item.subtitle)),
      optional('p', 'row-summary', item.summary)),
    arrow);
  return add(node('li'), row);
}

function skillCard(item) {
  const title = add(node('h3'), node('span', '', item.title));
  const arrow = node('span', 'link-arrow', '→');
  arrow.setAttribute('aria-hidden', 'true');
  return add(node('li'), add(link('', itemHref(item.id), 'skill-link'),
    add(title, arrow), optional('p', '', item.summary)));
}

function renderSection(section, aliases) {
  const { ui = {} } = portfolio;
  const element = node('section', 'home-section section-' + section.kind);
  element.id = section.id;
  const heading = node('h2', '', section.title);
  heading.id = 'heading-' + section.id;
  element.setAttribute('aria-labelledby', heading.id);
  for (const alias of aliases) {
    if (alias === section.id || portfolio.sections.some(candidate => candidate.id === alias)) continue;
    const target = node('span', 'anchor-marker');
    target.id = alias;
    element.append(target);
  }
  add(element, add(node('div', 'section-heading'), heading, optional('p', '', section.intro)));
  if (section.kind === 'products') {
    element.append(add(node('div', 'product-grid'), ...section.items.map(item => productCard(item, ui))));
  } else if (section.kind === 'skills') {
    element.append(add(node('ul', 'skills-list'), ...section.items.map(skillCard)));
  } else {
    const list = node('ul', 'timeline-list');
    for (const item of section.items) list.append(timelineRow(item));
    element.append(list);
  }
  return element;
}

function renderHome() {
  const { profile, sections, guide, ui = {} } = portfolio;
  const products = sections.find(section => section.kind === 'products');
  const about = sections.find(section => section.kind === 'timeline');
  const title = node('h1', '', profile.name);
  title.id = 'hero-name';
  title.tabIndex = -1;
  const hero = node('section', 'hero');
  hero.setAttribute('aria-labelledby', title.id);
  const guideHost = node('div', 'guide-host');
  guideHost.id = 'project-guide';
  const heroLinks = node('div', 'hero-actions');
  if (products) {
    heroLinks.append(link(ui.heroAction ?? 'Explore my work', ui.heroActionHref ?? sectionHref(products), 'button button-primary', '↓'));
  }
  add(heroLinks, action(profile.cv, 'button button-secondary'));
  add(hero,
    add(node('div', 'hero-copy'),
      optional('p', 'hero-role', profile.role),
      title,
      optional('p', 'hero-intro', profile.intro),
      heroLinks,
      profile.location && add(node('p', 'meta hero-location'), node('span', 'location-dot'), profile.location)),
    guideHost);
  main.append(hero);
  for (const section of sections) {
    const aliases = [section === products && 'work', section === about && 'about'].filter(Boolean);
    main.append(renderSection(section, aliases));
  }
  const contact = node('section', 'contact');
  contact.id = 'contact';
  const contactTitle = node('h2', '', ui.contactTitle ?? 'Contact');
  contactTitle.id = 'contact-title';
  contact.setAttribute('aria-labelledby', contactTitle.id);
  const contactLinks = node('div', 'contact-links');
  for (const item of profile.links ?? []) add(contactLinks, action(item, 'button button-secondary'));
  add(main, add(contact, add(node('div'), contactTitle, optional('p', '', ui.contactIntro)), contactLinks));
  if (mountGuide && guide && products) {
    cleanupGuide = mountGuide(guideHost, { guide, products: products.items, itemHref });
  }
  document.title = profile.title ?? profile.name;
  description.content = profile.description ?? profile.intro ?? '';
}

function backLink(text, href) {
  const anchor = link(text ?? 'Back to portfolio', href, 'back-link text-link');
  const arrow = node('span', 'link-arrow', '←');
  arrow.setAttribute('aria-hidden', 'true');
  anchor.prepend(arrow);
  anchor.dataset.routeBack = '';
  return anchor;
}

function renderDetail(record) {
  const { profile, ui = {} } = portfolio;
  const article = node('article', 'detail-page');
  let title;
  if (record) {
    const { item, section } = record;
    title = node('h1', '', item.title);
    const badges = node('p', 'meta detail-meta', [item.subtitle, item.period].filter(Boolean).join(' · '));
    add(article,
      backLink(ui.detailBack, sectionHref(section)),
      add(node('header', 'detail-header'), badges, title, optional('p', 'detail-summary', item.summary)));
    if (section.kind === 'products') add(article, media(item, 'detail-media', true));

    const prose = node('div', 'detail-prose');
    for (const block of item.blocks ?? []) {
      const content = add(node('section', 'detail-block'), optional('h2', '', block.heading));
      for (const paragraph of block.paragraphs ?? []) add(content, node('p', '', paragraph));
      if (block.bullets?.length) add(content, add(node('ul'), ...block.bullets.map(bullet => node('li', '', bullet))));
      prose.append(content);
    }
    const sidebar = node('aside', 'detail-sidebar');
    if (item.stack?.length) {
      add(sidebar, add(node('section'),
        node('h2', '', ui.detailStack ?? 'Tech stack'),
        add(node('ul', 'stack-list'), ...item.stack.map(toolItem))));
    }
    if (item.links?.length) {
      const links = node('ul', 'detail-links');
      for (const itemLink of item.links) add(links, add(node('li'), action(itemLink, 'text-link')));
      add(sidebar, add(node('section'), node('h2', '', ui.detailLinks ?? 'Links'), links));
    }
    if (item.certificates?.length) {
      const certificates = node('ul', 'detail-certificates');
      for (const itemCertificates of item.certificates) add(certificates, add(node('li'), action(itemCertificates, 'text-link')));
      add(sidebar, add(node('section'), node('h2', '', ui.detailCertificates ?? 'Certificates'), certificates));
    }
    add(article, add(node('div', 'detail-columns'), prose.childElementCount && prose, sidebar.childElementCount && sidebar));
    description.content = item.summary ?? profile.description ?? '';
  } else {
    title = node('h1', '', ui.unavailableTitle ?? 'Page unavailable');
    const message = ui.unavailableDescription ?? 'This portfolio entry could not be found.';
    add(article, backLink(ui.detailBack, '#top'), add(node('header', 'detail-header'), title, node('p', 'detail-summary', message)));
    description.content = message;
  }
  title.tabIndex = -1;
  document.title = title.textContent + ' — ' + profile.name;
  main.append(article);
}

function routeFromHash(hash) {
  if (!hash.startsWith(detailPrefix)) return { key: 'home' };
  try {
    return { key: hash, record: records.get(decodeURIComponent(hash.slice(detailPrefix.length))) };
  } catch {
    return { key: hash };
  }
}

function snapshot(anchor) {
  if ((!anchor && ignorePosition) || !currentEntry) return;
  const focus = anchor ?? document.activeElement;
  const oldPosition = positions.get(currentEntry);
  const sameLinks = focus instanceof HTMLAnchorElement
    ? [...document.links].filter(candidate => candidate.getAttribute('href') === focus.getAttribute('href'))
    : [];
  const focusedLink = sameLinks.length ? { href: focus.getAttribute('href'), index: sameLinks.indexOf(focus) } : null;
  const position = {
    scroll: window.scrollY,
    link: focusedLink ?? oldPosition?.link
  };
  positions.set(currentEntry, position);
  if (anchor) history.replaceState({ ...history.state, portfolioPosition: position }, '');
}

function targetFor(hash) {
  try {
    return document.getElementById(decodeURIComponent(hash.slice(1)));
  } catch {
    return null;
  }
}

function activateRoute({ initial = false, restore = false, smoothTop = false } = {}) {
  const entry = history.state;
  if (entry?.portfolioEntry === currentEntry && currentView) return;
  currentEntry = entry?.portfolioEntry;
  const route = routeFromHash(location.hash);
  const changedView = currentView !== route.key;

  if (changedView) {
    cleanupGuide?.();
    cleanupGuide = undefined;
    main.replaceChildren();
    if (route.key === 'home') renderHome();
    else renderDetail(route.record);
    currentView = route.key;
  }

  ignorePosition = true;
  const renderedEntry = currentEntry;
  requestAnimationFrame(() => {
    if (renderedEntry !== currentEntry) return;
    const saved = restore && (positions.get(currentEntry) ?? entry?.portfolioPosition);
    const section = route.key === 'home' ? targetFor(location.hash) : null;
    const lastFocus = saved?.link && [...document.links]
      .filter(candidate => candidate.getAttribute('href') === saved.link.href)[saved.link.index];
    const sectionHeading = section?.closest('section')?.querySelector('h2');
    const focus = lastFocus || sectionHeading || (section === main ? main : main.querySelector('h1'));
    if (focus && (!initial || location.hash)) {
      if (focus.tabIndex < 0 && !focus.hasAttribute('tabindex')) focus.tabIndex = -1;
      focus.focus({ preventScroll: true });
    }

    if (saved) window.scrollTo(0, saved.scroll);
    else if (section && section !== document.body && section !== main) section.scrollIntoView({ block: 'start' });
    else window.scrollTo({ top: 0, left: 0, behavior: smoothTop ? 'smooth' : 'instant' });

    requestAnimationFrame(() => {
      if (renderedEntry !== currentEntry) return;
      ignorePosition = false;
      snapshot();
    });
  });
}

function createEntry(extra = {}) {
  entryNumber += 1;
  return { portfolioEntry: Date.now() + '-' + entryNumber, ...extra };
}

function syncBrowserRoute() {
  if (!records) return;
  if (!history.state?.portfolioEntry) history.replaceState(createEntry(), '');
  activateRoute({ restore: true });
}

document.addEventListener('click', event => {
  if (!portfolio || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const anchor = event.target.closest('a[href^="#"]');
  if (!anchor || (anchor.target && anchor.target !== '_self')) return;
  const hash = anchor.getAttribute('href');
  if (anchor.classList.contains('skip')) {
    event.preventDefault();
    main.focus({ preventScroll: true });
    main.scrollIntoView();
    return;
  }

  event.preventDefault();
  snapshot(anchor);
  if ('routeBack' in anchor.dataset && history.state?.fromHome) {
    history.back();
    return;
  }

  const extra = currentView === 'home' && hash.startsWith(detailPrefix) ? { fromHome: true } : {};
  if (hash === location.hash) history.replaceState(createEntry(extra), '', hash);
  else history.pushState(createEntry(extra), '', hash);
  const smoothTop = anchor.classList.contains('footer-top') && !matchMedia('(prefers-reduced-motion: reduce)').matches;
  activateRoute({ smoothTop });
});

window.addEventListener('scroll', () => snapshot(), { passive: true });
window.addEventListener('popstate', syncBrowserRoute);
window.addEventListener('hashchange', syncBrowserRoute);

async function loadPortfolio() {
  try {
    const [response, guideModule] = await Promise.all([
      fetch('./portfolio.json', { cache: 'no-store' }),
      import('./cat.js').catch(error => {
        console.warn('The project guide could not load.', error);
        return null;
      })
    ]);
    if (!response.ok) throw new Error('HTTP ' + response.status);
    portfolio = await response.json();
    mountGuide = guideModule?.mountGuide;
    records = new Map();
    for (const section of portfolio.sections) {
      for (const item of section.items) records.set(item.id, { item, section });
    }
    history.scrollRestoration = 'manual';
    if (!history.state?.portfolioEntry) history.replaceState(createEntry(), '');
    renderHeader();
    activateRoute({ initial: true });
  } catch (error) {
    console.error('The portfolio could not load.', error);
    main.replaceChildren(add(node('section', 'page-status'),
      node('h1', '', 'Portfolio unavailable'),
      node('p', '', 'The portfolio could not load.'),
      link('Reload page', location.href, 'text-link')));
  } finally {
    main.removeAttribute('aria-busy');
  }
}

loadPortfolio();

