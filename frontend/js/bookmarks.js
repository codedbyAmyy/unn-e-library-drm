import { apiRequest } from './api.js';

const create = (tag, className = '', text = '') => {
  const element = document.createElement(tag);
  element.className = className;
  element.textContent = text;
  return element;
};

let savedIds = null;
let inFlight = null;

async function loadBookmarkIds(force = false) {
  if (force) { savedIds = null; inFlight = null; }
  if (savedIds) return savedIds;
  if (!inFlight) {
    inFlight = (async () => {
      const ids = new Set();
      let offset = 0;
      const limit = 100;
      while (true) {
        const result = await apiRequest(`/bookmarks?limit=${limit}&offset=${offset}`);
        const rows = result.items || [];
        rows.forEach(row => ids.add(Number(row.resource_id)));
        offset += rows.length;
        if (!rows.length || offset >= Number(result.total || 0)) break;
      }
      savedIds = ids;
      return ids;
    })().finally(() => { inFlight = null; });
  }
  return inFlight;
}

export function makeBookmarkControl(resourceId, onUpdated = null) {
  const id = Number(resourceId);
  const control = create('button', 'btn-quiet bookmark-toggle', 'Checking saved status…');
  control.type = 'button';
  control.disabled = true;
  control.setAttribute('aria-label', 'Check whether resource is saved');
  const feedback = create('span', 'sr-only');
  feedback.setAttribute('role', 'status');

  function paint(saved) {
    control.textContent = saved ? '★ Remove from My Library' : '☆ Save to My Library';
    control.setAttribute('aria-pressed', String(saved));
    control.setAttribute('aria-label', saved ? 'Remove resource from My Library' : 'Save resource to My Library');
    control.disabled = false;
  }
  loadBookmarkIds().then(ids => paint(ids.has(id))).catch(() => {
    control.textContent = 'Could not check saved status';
    control.disabled = true;
  });
  control.addEventListener('click', async () => {
    if (control.disabled) return;
    control.disabled = true;
    const wasSaved = control.getAttribute('aria-pressed') === 'true';
    control.textContent = wasSaved ? 'Removing…' : 'Saving…';
    try {
      await apiRequest(`/bookmarks/${encodeURIComponent(id)}`, {
        method: wasSaved ? 'DELETE' : 'POST'
      });
      const ids = await loadBookmarkIds();
      if (wasSaved) ids.delete(id);
      else ids.add(id);
      paint(!wasSaved);
      feedback.textContent = wasSaved ? 'Resource removed from My Library.' : 'Resource saved to My Library.';
      if (onUpdated) await onUpdated();
    } catch (err) {
      paint(wasSaved);
      feedback.textContent = `Could not update saved resource: ${err.message}`;
    }
  });
  const wrapper = create('span', 'bookmark-control');
  wrapper.append(control, feedback);
  return wrapper;
}

export async function showMyLibrary({ content, openPdf, showDetails }) {
  const header = create('div', 'page-heading');
  header.append(create('h1', '', 'My Library'), create('p', 'subheading', 'Resources you have saved for later. Your collection is linked to your account.'));
  content.append(header);
  const status = create('p', 'results-count', 'Loading saved resources…');
  status.setAttribute('role', 'status');
  content.append(status);
  const grid = create('div', 'resource-grid-v2');
  content.append(grid);
  const pager = create('div', 'pager');
  content.append(pager);
  let offset = 0;
  const limit = 12;

  async function refresh() {
    grid.replaceChildren();
    pager.replaceChildren();
    status.textContent = 'Loading saved resources…';
    try {
      const data = await apiRequest(`/bookmarks?limit=${limit}&offset=${offset}`);
      const rows = data.items || [];
      const total = Number(data.total || 0);
      status.textContent = `${total} saved resource${total === 1 ? '' : 's'}`;
      if (!rows.length && offset > 0) { offset = Math.max(0, offset - limit); return refresh(); }
      if (!rows.length) {
        grid.append(create('p', 'empty-state', 'Your library is empty. Browse Library & Discovery and select “Save to My Library” on a resource.'));
        return;
      }
      await Promise.all(rows.map(async record => {
        const id = Number(record.resource_id);
        const card = create('article', 'resource-card-v2');
        try {
          const resource = await apiRequest(`/resources/${encodeURIComponent(id)}`);
          card.append(create('span', 'pill', (resource.resource_type || 'Academic resource').replaceAll('_',' ')));
          card.append(create('h3', '', resource.title || `Resource #${id}`));
          if (resource.authors?.length) {
            const names = resource.authors.map(a => typeof a === 'string' ? a : a.author_name).filter(Boolean);
            if (names.length) card.append(create('p', 'card-meta', names.join(', ')));
          }
          if (resource.abstract) card.append(create('p', 'card-abstract', resource.abstract.slice(0, 220)));
          const buttons = create('div', 'card-actions');
          const read = create('button', 'btn-primary-alt', 'Read PDF'); read.type = 'button'; read.addEventListener('click', () => openPdf(id));
          const details = create('button', 'btn-quiet', 'Details'); details.type = 'button'; details.addEventListener('click', () => showDetails(id));
          buttons.append(read, details, makeBookmarkControl(id, () => { savedIds = null; return refresh(); }));
          card.append(buttons);
        } catch (e) {
          card.append(create('h3', '', `Resource #${id}`));
          card.append(create('p', 'error-state', 'This resource is no longer available to your account.'));
          card.append(makeBookmarkControl(id, () => { savedIds = null; return refresh(); }));
        }
        grid.append(card);
      }));
      const previous = create('button', 'btn-quiet', '← Previous'); previous.type = 'button'; previous.disabled = offset === 0;
      previous.addEventListener('click', () => { offset -= limit; refresh(); });
      const next = create('button', 'btn-quiet', 'Next →'); next.type = 'button'; next.disabled = offset + limit >= total;
      next.addEventListener('click', () => { offset += limit; refresh(); });
      pager.append(previous, create('span', '', `Page ${Math.floor(offset / limit) + 1}`), next);
    } catch (e) {
      status.textContent = 'Could not load your saved resources.';
      grid.append(create('p', 'error-state', e.message || 'Please try again.'));
    }
  }
  await loadBookmarkIds(true);
  await refresh();
}
