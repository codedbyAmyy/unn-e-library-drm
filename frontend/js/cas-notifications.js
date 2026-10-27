import { apiRequest } from './api.js';

const make = (tag, cls, text) => {
  const x = document.createElement(tag);
  if (cls) x.className = cls;
  if (text !== undefined) x.textContent = text;
  return x;
};

function prettyDate(value) {
  if (!value) return '';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString();
}

async function updateBadge() {
  const links = document.querySelectorAll('.nav-item[href="#notifications"]');
  if (!links.length) return;
  try {
    const result = await apiRequest('/notifications/unread-count');
    const count = Number(result.unread_count || 0);
    for (const link of links) {
      let badge = link.querySelector('.cas-nav-count');
      if (!count) { badge?.remove(); continue; }
      if (!badge) { badge = make('span', 'cas-nav-count'); link.append(badge); }
      badge.textContent = count > 99 ? '99+' : String(count);
      badge.setAttribute('aria-label', `${count} unread notifications`);
    }
  } catch (error) {
    // A failed badge refresh should never block navigation.
    if (error.status !== 401) console.warn('Could not refresh notification count', error);
  }
}

export { updateBadge as refreshCasBadge };

export async function showCasNotifications({ content, onOpenResource }) {
  content.replaceChildren();
  const heading = make('div', 'page-heading');
  heading.append(make('h1', '', 'Notifications'), make('p', 'subheading', 'Your latest academic-resource updates and alert preferences.'));
  content.append(heading);

  const preferences = make('section', 'data-panel cas-preferences');
  preferences.append(make('h2', 'panel-heading', 'Notification preferences'));
  const prefHelp = make('p', 'cas-muted', 'Choose how you receive new-resource announcements. Your academic eligibility is determined by your course and department.');
  preferences.append(prefHelp);
  const prefRows = make('div', 'cas-pref-rows');
  const prefStatus = make('p', 'cas-feedback');
  prefStatus.setAttribute('role', 'status');
  const toggles = {};
  for (const [field, title, description] of [
    ['new_resource_in_app', 'In-app notifications', 'Show matching resources in this notification centre.'],
    ['new_resource_email', 'Email notifications', 'Receive matching resource announcements in your inbox.']
  ]) {
    const label = make('label', 'cas-pref-row');
    const copy = make('span', 'cas-pref-copy');
    copy.append(make('strong', '', title), make('small', '', description));
    const checkbox = make('input', 'cas-switch');
    checkbox.type = 'checkbox';
    checkbox.disabled = true;
    checkbox.setAttribute('aria-label', title);
    toggles[field] = checkbox;
    label.append(copy, checkbox); prefRows.append(label);
    checkbox.addEventListener('change', async () => {
      const desired = checkbox.checked;
      checkbox.disabled = true;
      prefStatus.textContent = 'Saving preferences…';
      try {
        const saved = await apiRequest('/notifications/preferences', {
          method: 'PATCH', body: JSON.stringify({ [field]: desired })
        });
        for (const [key, input] of Object.entries(toggles)) input.checked = Boolean(saved[key]);
        prefStatus.textContent = 'Preferences saved.';
        if (field === 'new_resource_in_app') await loadList();
      } catch (error) {
        checkbox.checked = !desired;
        prefStatus.textContent = `Could not save preferences: ${error.message}`;
      } finally { checkbox.disabled = false; }
    });
  }
  preferences.append(prefRows, prefStatus); content.append(preferences);

  const section = make('section', 'data-panel cas-notification-panel');
  const row = make('div', 'cas-section-head');
  row.append(make('h2', 'panel-heading', 'Latest updates'));
  const reload = make('button', 'btn-quiet', 'Refresh'); reload.type = 'button';
  row.append(reload); section.append(row);
  const summary = make('p', 'cas-muted'); section.append(summary);
  const list = make('div', 'cas-notice-list'); section.append(list);
  const pager = make('div', 'pager'); section.append(pager);
  content.append(section);
  let offset = 0;
  const limit = 10;
  let requestCounter = 0;

  async function loadList() {
    const seq = ++requestCounter;
    list.replaceChildren(); pager.replaceChildren();
    summary.textContent = 'Loading notifications…';
    try {
      const data = await apiRequest(`/notifications?limit=${limit}&offset=${offset}`);
      if (seq !== requestCounter || !content.isConnected) return;
      const items = data.items || [];
      const total = Number(data.total || 0);
      summary.textContent = `${data.unread_count || 0} unread · ${total} total`;
      if (!items.length) list.append(make('p', 'empty-state', 'No notifications here yet. New academic-resource alerts will appear here.'));
      for (const item of items) {
        const article = make('article', `cas-notice ${item.is_read ? 'cas-read' : 'cas-unread'}`);
        const meta = make('div', 'cas-notice-meta');
        meta.append(make('span', 'cas-kicker', item.is_read ? 'Read' : 'New'), make('time', 'cas-muted', prettyDate(item.created_at)));
        article.append(meta, make('h3', '', item.title || 'Library update'));
        if (item.message) article.append(make('p', '', item.message));
        const actions = make('div', 'cas-actions');
        if (item.resource_id) {
          const open = make('button', 'btn-primary-alt', 'View resource'); open.type = 'button';
          open.addEventListener('click', () => onOpenResource(item.resource_id));
          actions.append(open);
        }
        if (!item.is_read) {
          const mark = make('button', 'btn-quiet', 'Mark as read'); mark.type = 'button';
          mark.addEventListener('click', async () => {
            mark.disabled = true; mark.textContent = 'Saving…';
            try {
              await apiRequest(`/notifications/${item.id}/read`, { method: 'PATCH' });
              await loadList(); await updateBadge();
            } catch (error) { mark.disabled = false; mark.textContent = 'Mark as read'; summary.textContent = `Could not update notification: ${error.message}`; }
          }); actions.append(mark);
        }
        article.append(actions); list.append(article);
      }
      const previous = make('button', 'btn-quiet', '← Previous'); previous.type = 'button'; previous.disabled = offset === 0;
      previous.onclick = () => { offset = Math.max(0, offset - limit); loadList(); };
      const next = make('button', 'btn-quiet', 'Next →'); next.type = 'button'; next.disabled = offset + limit >= total;
      next.onclick = () => { offset += limit; loadList(); };
      pager.append(previous, make('span', '', `Page ${Math.floor(offset / limit) + 1}`), next);
      await updateBadge();
    } catch (error) { if (seq === requestCounter) summary.textContent = `Unable to load notifications: ${error.message}`; }
  }
  reload.onclick = () => loadList();
  try {
    const saved = await apiRequest('/notifications/preferences');
    for (const [key, input] of Object.entries(toggles)) { input.checked = Boolean(saved[key]); input.disabled = false; }
  } catch (error) { prefStatus.textContent = `Could not load preferences: ${error.message}`; }
  await loadList();
}
