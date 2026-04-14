import { api } from '../api/client.js';
import { banner, escapeHtml, layout, navButton } from '../components/ui.js';

export async function renderStudent(root, state) {
  const dashboard = await api.studentDashboard();
  const nav = [navButton('Dashboard', 'overview', 'overview')].join('');

  root.innerHTML = layout({
    user: state.user,
    title: 'Student Dashboard',
    subtitle: 'Progress, attendance, coin va vazifalaringiz shu yerda.',
    nav,
    content: `
      <section class="grid grid-4">
        <article class="card stat-card"><strong>${dashboard.groups.length}</strong><span>Guruhlar</span></article>
        <article class="card stat-card"><strong>${dashboard.attendance_summary.present}</strong><span>Present kunlar</span></article>
        <article class="card stat-card"><strong>${dashboard.average_mark}</strong><span>O'rtacha baho</span></article>
        <article class="card stat-card"><strong>${dashboard.total_coins}</strong><span>Jami coin</span></article>
      </section>
      <section class="grid grid-2" style="margin-top:18px;">
        <article class="card">
          <h3>Guruhlarim</h3>
          <div class="list">
            ${dashboard.groups.map((group) => `<div class="item"><h4>${escapeHtml(group.name)}</h4><p>${escapeHtml(group.direction.name)} • ${escapeHtml(group.schedule || 'Jadval ko`rsatilmagan')}</p></div>`).join('') || '<div class="empty">Guruh topilmadi</div>'}
          </div>
        </article>
        <article class="card">
          <h3>Attendance summary</h3>
          <div class="list">
            <div class="item"><h4>Present</h4><p>${dashboard.attendance_summary.present}</p></div>
            <div class="item"><h4>Late</h4><p>${dashboard.attendance_summary.late}</p></div>
            <div class="item"><h4>Absent</h4><p>${dashboard.attendance_summary.absent}</p></div>
          </div>
        </article>
      </section>
      <section class="card" style="margin-top:18px;">
        <h3>Pending homework</h3>
        ${banner(state.flashType, state.flashMessage)}
        <div class="list">
          ${dashboard.pending_homeworks.map((homework) => `
            <div class="item">
              <h4>${escapeHtml(homework.title)}</h4>
              <p>${escapeHtml(homework.description)}</p>
              <p>Deadline: ${homework.due_date} • Max ball: ${homework.max_score}</p>
              <form class="form-grid" data-homework-form="${homework.id}">
                <textarea name="content" placeholder="Javobingizni yozing" required></textarea>
                <button class="btn btn-primary">Yuborish</button>
              </form>
            </div>`).join('') || '<div class="empty">Hozircha homework yo`q</div>'}
        </div>
      </section>
    `,
  });

  root.querySelector('[data-action="logout"]').addEventListener('click', state.onLogout);
  root.querySelectorAll('[data-homework-form]').forEach((form) => {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      await state.safeAction(async () => api.submitHomework(form.dataset.homeworkForm, {
        content: formData.get('content'),
      }), 'Homework yuborildi');
    });
  });
}
