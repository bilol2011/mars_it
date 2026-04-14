export function escapeHtml(value = '') {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

export function banner(type, message) {
  if (!message) return '';
  return `<div class="${type === 'error' ? 'error-banner' : 'success-banner'}">${escapeHtml(message)}</div>`;
}

export function statusBadge(status) {
  const map = {
    present: 'green',
    late: 'orange',
    absent: 'red',
  };
  return `<span class="badge ${map[status] || 'blue'}">${escapeHtml(status)}</span>`;
}

export function layout({ user, title, subtitle, nav, content }) {
  return `
    <div class="app-shell">
      <aside class="sidebar">
        <div class="brand">
          <div class="panel-label">MARS IT</div>
          <h1>CRM / LMS</h1>
          <p>Ta'lim markazi boshqaruvi, mentor paneli va student kabineti bitta joyda.</p>
        </div>
        <div class="nav-links">
          ${nav}
        </div>
        <button class="btn btn-primary" data-action="logout">Chiqish</button>
      </aside>
      <main class="content">
        <div class="topbar">
          <div>
            <h2>${escapeHtml(title)}</h2>
            <p>${escapeHtml(subtitle)}</p>
          </div>
          <div class="user-pill">
            <strong>${escapeHtml(user.full_name)}</strong><br />
            <span class="subtle">${escapeHtml(user.role)}</span>
          </div>
        </div>
        ${content}
      </main>
    </div>
  `;
}

export function navButton(label, view, activeView) {
  return `<button class="nav-link ${view === activeView ? 'active' : ''}" data-view="${view}">${label}</button>`;
}
