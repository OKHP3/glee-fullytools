// Render index-generated diagrams in strict mode, with ordinary links as fallback.
const elements = [...document.querySelectorAll('.mermaid')];
const sources = new Map(elements.map(element => [element, element.textContent]));
const origin = 'https://glee-fully.tools';
let runtime;
let sequence = 0;
let pending = Promise.resolve();

async function nodeId(url) {
  const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(url));
  return 'n' + [...new Uint8Array(hash)].map(value => value.toString(16).padStart(2, '0')).join('').slice(0, 16);
}

async function renderVisible() {
  const visible = elements.filter(element => (!element.closest('details') || element.closest('details').open) && !element.dataset.rendered);
  if (!visible.length) return;
  try {
    runtime ||= (await import('/assets/vendor/mermaid/mermaid.esm.min.mjs')).default;
    const styles = getComputedStyle(document.documentElement);
    const token = (name, fallback) => styles.getPropertyValue(name).trim() || fallback;
    runtime.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: 'base',
      themeVariables: {
        primaryColor: token('--color-surface', '#fffdfa'),
        primaryTextColor: token('--color-fg', '#2e2b29'),
        primaryBorderColor: token('--color-accent', '#d35b2d'),
        lineColor: token('--color-fg', '#2e2b29'),
      },
      flowchart: { htmlLabels: false, wrappingWidth: 200, useMaxWidth: true },
    });
    for (const element of visible) {
      const {svg} = await runtime.render('glee-universe-' + sequence++, sources.get(element));
      element.innerHTML = svg;
      const view = element.querySelector('svg');
      element.removeAttribute('role');
      element.removeAttribute('aria-label');
      view.setAttribute('role', 'group');
      view.setAttribute('aria-label', element.closest('details')?.querySelector('summary').textContent || 'The three sibling sites');
      // Mermaid click directives remain disabled. Only same-site links already
      // present in the accessible outline become keyboard-focusable SVG links.
      for (const link of element.closest('details')?.querySelectorAll('li a[href]') || []) {
        const target = new URL(link.getAttribute('href'), origin);
        if (target.origin !== origin || target.username || target.password || target.search) continue;
        const id = await nodeId(target.href);
        const node = [...view.querySelectorAll('g.node')].find(item => item.id.includes('flowchart-' + id + '-'));
        if (!node) continue;
        const anchor = document.createElementNS('http://www.w3.org/2000/svg', 'a');
        anchor.setAttribute('href', target.pathname + target.hash);
        anchor.setAttribute('aria-label', link.textContent);
        anchor.setAttribute('tabindex', '0');
        while (node.firstChild) anchor.append(node.firstChild);
        node.append(anchor);
      }
      element.hidden = false;
      element.dataset.processed = 'true';
      element.dataset.rendered = 'true';
    }
  } catch (error) {
    for (const element of visible) {
      element.textContent = 'Use the page links below while the diagram is unavailable.';
      element.hidden = false;
      element.dataset.processed = 'true';
    }
    console.warn('Universe diagram unavailable', error);
  }
}

function enqueue() { pending = pending.then(renderVisible); }
document.querySelectorAll('.universe-map details').forEach(details => details.addEventListener('toggle', enqueue));
new MutationObserver(() => {
  elements.forEach(element => { delete element.dataset.rendered; });
  enqueue();
}).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'data-color-scheme'] });
matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', () => {
  elements.forEach(element => { delete element.dataset.rendered; });
  enqueue();
});
enqueue();
