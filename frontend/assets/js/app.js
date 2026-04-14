import { api } from './api/client.js';
import { renderAdmin } from './pages/admin.js';
import { renderTeacher } from './pages/teacher.js';
import { renderStudent } from './pages/student.js';
import { banner } from './components/ui.js';

const root = document.getElementById('app');

const state = {
  user: api.getStoredUser(),
  view: 'overview',
  selectedGroupId: null,
  flashMessage: '',
  flashType: 'success',
};

function setFlash(message = '', type = 'success') {
  state.flashMessage = message;
  state.flashType = type;
}

async function safeAction(action, successMessage = 'Saqlandi') {
  try {
    await action();
    setFlash(successMessage, 'success');
    await boot();
  } catch (error) {
    setFlash(error.message, 'error');
    await boot();
  }
}

function renderLogin(errorMessage = '') {
  root.innerHTML = `
    <div class="auth-shell">
      <div class="auth-card">
        <section class="auth-hero">
          <div class="panel-label">MARS IT</div>
          <h1>Education CRM</h1>
          <p>Admin, teacher va student uchun yagona platforma. Davomat, baho, coin va homework boshqaruvi bitta tizimda.</p>
          <div class="auth-stats">
            <div class="auth-stat"><strong>4</strong><span>Yo'nalish</span></div>
            <div class="auth-stat"><strong>3</strong><span>Rollar</span></div>
            <div class="auth-stat"><strong>24/7</strong><span>Nazorat</span></div>
          </div>
        </section>
        <section class="auth-form-wrap">
          <div class="panel-label">Xush kelibsiz</div>
          <h2>Tizimga kirish</h2>
          <p>Default loginlar: admin/admin123, teacher1/teacher123, student1/student123</p>
          ${banner(errorMessage ? 'error' : '', errorMessage)}
          <form id="login-form" class="form-grid">
            <input class="input" name="username" placeholder="Username" required />
            <input class="input" name="password" type="password" placeholder="Password" required />
            <button class="btn btn-primary">Kirish</button>
          </form>
        </section>
      </div>
    </div>
  `;

  root.querySelector('#login-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    try {
      const data = await api.login(formData.get('username'), formData.get('password'));
      state.user = data.user;
      setFlash('');
      await boot();
    } catch (error) {
      renderLogin(error.message);
    }
  });
}

function logout() {
  api.clearSession();
  state.user = null;
  state.selectedGroupId = null;
  setFlash('');
  renderLogin();
}

async function ensureSession() {
  if (!api.getToken()) return false;
  try {
    const me = await api.me();
    state.user = me;
    return true;
  } catch {
    logout();
    return false;
  }
}

async function boot() {
  if (!(await ensureSession())) {
    renderLogin();
    return;
  }

  const shared = {
    user: state.user,
    view: state.view,
    selectedGroupId: state.selectedGroupId,
    flashMessage: state.flashMessage,
    flashType: state.flashType,
    onLogout: logout,
    onNavigate: async (view) => {
      state.view = view;
      await boot();
    },
    onSelectGroup: async (groupId) => {
      state.selectedGroupId = Number(groupId);
      await boot();
    },
    safeAction,
  };

  if (state.user.role === 'admin') {
    await renderAdmin(root, shared);
  } else if (state.user.role === 'teacher') {
    await renderTeacher(root, shared);
  } else {
    await renderStudent(root, shared);
  }
}

boot();
