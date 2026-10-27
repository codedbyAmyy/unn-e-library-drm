import { apiRequest } from './api.js';

const make = (tag, className = '', value = '') => {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = value;
  return element;
};
const fmt = number => Number(number ?? 0).toLocaleString();
const readableRole = role => ({student:'Student',lecturer:'Lecturer',librarian:'Librarian',admin:'Administrator'})[role] || role;
const when = input => {
  if (!input) return '—';
  const date = new Date(input);
  return Number.isNaN(date.valueOf()) ? '—' : date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
};
const link = (label, hash, kind = '') => {
  const a = make('a', `unn-admin-link ${kind}`, label);
  a.href = hash;
  return a;
};
function metric(title, value, detail, icon) {
  const card = make('article', 'unn-admin-metric');
  const line = make('div', 'unn-admin-metric-top');
  line.append(make('span', '', title), make('span', 'unn-admin-metric-icon', icon));
  card.append(line, make('strong', 'unn-admin-value', value), make('p', '', detail));
  return card;
}
async function safeRequest(path) {
  try { return { data: await apiRequest(path) }; }
  catch (error) { return { error }; }
}

export async function showAdminDashboard({ content, user } = {}) {
  if (!content) throw new Error('Admin dashboard container is unavailable.');
  content.replaceChildren();
  const main = make('div', 'unn-admin-dashboard');
  content.append(main);
  const intro = make('header', 'unn-admin-heading');
  const headerText = make('div');
  headerText.append(make('span', 'unn-admin-eyebrow', 'LIBRARY ADMINISTRATION'), make('h1', '', 'Administrator Dashboard'), make('p', '', `Welcome${user?.full_name ? ', ' + user.full_name.split(' ')[0] : ''}. Manage institutional accounts and oversee your digital library.`));
  const actions = make('div', 'unn-admin-heading-actions');
  actions.append(link('Manage Users', '#users', 'primary'), link('Browse Resources', '#library'));
  intro.append(headerText, actions);
  main.append(intro);
  const statGrid = make('section', 'unn-admin-metrics');
  statGrid.setAttribute('aria-label', 'Account and resource summary');
  statGrid.append(metric('Total Accounts', '—', 'Checking user records', '♙'),metric('Active Accounts', '—', 'Checking active accounts', '✓'),metric('Inactive Accounts', '—', 'Checking inactive accounts', '○'),metric('Catalogue Resources', '—', 'Checking visible resources', '▤'));
  main.append(statGrid);
  const layout = make('div', 'unn-admin-two-column');
  const rolePanel = make('section', 'unn-admin-panel');
  rolePanel.append(make('h2', '', 'Accounts by Role'),make('p', 'unn-admin-panel-subtitle', 'Live totals for each registered account type'));
  const rolesRoot = make('div', 'unn-admin-roles');
  rolesRoot.append(make('p', 'unn-admin-muted', 'Loading role breakdown…'));
  rolePanel.append(rolesRoot);
  const quick = make('section', 'unn-admin-panel');
  quick.append(make('h2', '', 'Quick Actions'),make('p', 'unn-admin-panel-subtitle', 'Navigate to your existing administration tools'));
  const quickLinks = make('div', 'unn-admin-quick');
  [ ['User Management','Review account information, roles and access','#users','♙'], ['Resource Catalogue','Browse available academic resources','#library','▤'], ['Notifications','View your in-app notifications','#notifications','♧'], ['Profile & Settings','Review your administrator profile','#profile','◉'] ].forEach(([title,desc,hash,icon]) => {
    const card=link('',hash,'unn-admin-quick-item');
    card.append(make('span','unn-admin-quick-icon',icon));
    const text=make('span','unn-admin-quick-text');
    text.append(make('strong','',title),make('small','',desc));
    card.append(text, make('span','unn-admin-quick-chevron','›'));
    quickLinks.append(card);
  });
  quick.append(quickLinks);
  layout.append(rolePanel,quick);
  main.append(layout);
  const recent = make('section', 'unn-admin-panel unn-admin-recent');
  const recentHeading=make('div','unn-admin-section-header');
  recentHeading.append(make('h2','','Recently Registered Accounts'),link('View all users','#users'));
  recent.append(recentHeading);
  const recentBody=make('div','unn-admin-table-scroll');
  recentBody.append(make('p','unn-admin-muted','Loading recent accounts…'));
  recent.append(recentBody);
  main.append(recent);
  const result = await Promise.all([
    safeRequest('/admin/users?limit=1&offset=0'),
    safeRequest('/admin/users?is_active=true&limit=1&offset=0'),
    safeRequest('/admin/users?is_active=false&limit=1&offset=0'),
    safeRequest('/resources?limit=1&offset=0'),
    ...['student','lecturer','librarian','admin'].map(role=>safeRequest(`/admin/users?role=${role}&limit=1&offset=0`)),
    safeRequest('/admin/users?limit=8&offset=0')
  ]);
  if (!main.isConnected) return;
  const [all,active,inactive,resources,...others]=result;
  const roleResponses=others.slice(0,4);
  const newest=others[4];
  const cards=statGrid.children;
  [
    [all,'Registered accounts'],[active,'Accounts allowed to sign in'],[inactive,'Accounts currently deactivated'],[resources,'Records visible to this account']
  ].forEach(([r,detail],i) => {
    cards[i].querySelector('.unn-admin-value').textContent=r.error?'Unavailable':fmt(r.data?.total);
    cards[i].querySelector('p').textContent=r.error?'Could not load this metric':detail;
  });
  rolesRoot.replaceChildren();
  const totals=roleResponses.map(x=>Number(x.data?.total || 0));
  const max=Math.max(1,...totals);
  ['student','lecturer','librarian','admin'].forEach((role,i)=>{
    const item=make('div','unn-admin-role');
    const labels=make('div','unn-admin-role-label');
    labels.append(make('span','',readableRole(role)),make('strong','',roleResponses[i].error?'Unavailable':fmt(totals[i])));
    const track=make('div','unn-admin-bar');
    const fill=make('div','unn-admin-bar-fill');
    fill.style.width=`${roleResponses[i].error?0:100*totals[i]/max}%`;
    track.append(fill);
    item.append(labels,track);
    rolesRoot.append(item);
  });
  recentBody.replaceChildren();
  if (newest.error) {
    recentBody.append(make('p','unn-admin-error',newest.error.message || 'Unable to load recent accounts.'));
  } else {
    const users=Array.isArray(newest.data?.items)?newest.data.items:[];
    if (!users.length) recentBody.append(make('p','unn-admin-muted','No accounts have been registered yet.'));
    else {
      const table=make('table','unn-admin-table');
      const head=make('thead');const tr=make('tr');
      ['Name','Email','Role','Status','Registered'].forEach(label=>tr.append(make('th','',label)));
      head.append(tr);table.append(head);
      const body=make('tbody');
      users.forEach(account=>{
        const row=make('tr');
        const status=make('span',`unn-admin-status ${account.is_active?'active':'inactive'}`,account.is_active?'Active':'Inactive');
        [account.full_name || '—',account.email || '—',readableRole(account.role)].forEach(v=>row.append(make('td','',v)));
        const td=make('td');td.append(status);row.append(td);
        row.append(make('td','',when(account.created_at)));
        body.append(row);
      });
      table.append(body);recentBody.append(table);
    }
  }
}
