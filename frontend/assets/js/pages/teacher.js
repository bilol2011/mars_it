import { api } from '../api/client.js';
import { banner, escapeHtml, layout, navButton, statusBadge } from '../components/ui.js';

export async function renderTeacher(root, state) {
  const dashboard = await api.teacherDashboard();
  const currentGroupId = state.selectedGroupId || dashboard.groups[0]?.id || null;
  const detail = currentGroupId ? await api.teacherGroupDetail(currentGroupId) : null;
  const nav = dashboard.groups.map((group) => navButton(group.name, String(group.id), String(currentGroupId))).join('');

  const overview = `
    <section class="grid grid-4">
      <article class="card stat-card"><strong>${dashboard.groups.length}</strong><span>Biriktirilgan guruhlar</span></article>
      <article class="card stat-card"><strong>${dashboard.coin_summary.used}</strong><span>Tarqatilgan coin</span></article>
      <article class="card stat-card"><strong>${dashboard.coin_summary.capacity}</strong><span>Coin capacity</span></article>
      <article class="card stat-card"><strong>${dashboard.recent_homeworks.length}</strong><span>Yaqin homeworklar</span></article>
    </section>
    ${detail ? `
      <section class="grid grid-2" style="margin-top:18px;">
        <article class="card stack">
          <div>
            <span class="panel-label">Tanlangan guruh</span>
            <h3>${escapeHtml(detail.group.name)}</h3>
            <p class="subtle">${escapeHtml(detail.group.direction.name)} - ${escapeHtml(detail.group.schedule || 'Jadval korsatilmagan')}</p>
            <div class="badge blue">Coin: ${detail.coin_usage.used} / ${detail.coin_usage.limit}</div>
          </div>
          <div class="list">
            ${detail.students.map((student) => `<div class="item"><h4>${escapeHtml(student.full_name)}</h4><p>${escapeHtml(student.username)}</p></div>`).join('') || '<div class="empty">Hozircha student yoq</div>'}
          </div>
        </article>
        <article class="card stack">
          <h3>Tezkor amallar</h3>
          ${banner(state.flashType, state.flashMessage)}
          <form id="attendance-form" class="form-grid">
            <select name="student_id" required>${detail.students.map((student) => `<option value="${student.id}">${escapeHtml(student.full_name)}</option>`).join('')}</select>
            <input class="input" type="date" name="lesson_date" required />
            <select name="status" required>
              <option value="present">Present</option>
              <option value="late">Late</option>
              <option value="absent">Absent</option>
            </select>
            <input class="input" name="notes" placeholder="Izoh" />
            <button class="btn btn-primary">Davomat saqlash</button>
          </form>
          <form id="mark-form" class="form-grid">
            <select name="student_id" required>${detail.students.map((student) => `<option value="${student.id}">${escapeHtml(student.full_name)}</option>`).join('')}</select>
            <input class="input" type="number" name="score" min="0" max="100" placeholder="Ball" required />
            <input class="input" name="notes" placeholder="Izoh" />
            <button class="btn btn-secondary">Baho qoyish</button>
          </form>
          <form id="coin-form" class="form-grid">
            <select name="student_id" required>${detail.students.map((student) => `<option value="${student.id}">${escapeHtml(student.full_name)}</option>`).join('')}</select>
            <input class="input" type="number" name="coins" min="1" max="100" placeholder="Coin" required />
            <input class="input" name="reason" placeholder="Sabab" required />
            <button class="btn btn-secondary">Coin berish</button>
          </form>
          <form id="homework-form" class="form-grid">
            <input class="input" name="title" placeholder="Homework nomi" required />
            <textarea name="description" placeholder="Vazifa tavsifi" required></textarea>
            <input class="input" type="date" name="due_date" required />
            <input class="input" type="number" name="max_score" min="1" max="100" value="100" required />
            <button class="btn btn-secondary">Homework yaratish</button>
          </form>
        </article>
      </section>
      <section class="grid grid-2" style="margin-top:18px;">
        <article class="card">
          <h3>Attendance</h3>
          <div class="list">${detail.attendance.map((row) => `<div class="item"><h4>${escapeHtml(row.student.full_name)}</h4><p>${row.lesson_date} - ${statusBadge(row.status)}</p></div>`).join('') || '<div class="empty">Davomat yoq</div>'}</div>
        </article>
        <article class="card">
          <h3>Marks</h3>
          <div class="list">${detail.marks.map((row) => `<div class="item"><h4>${escapeHtml(row.student.full_name)}</h4><p>${row.score} ball - ${escapeHtml(row.notes || '')}</p></div>`).join('') || '<div class="empty">Baho yoq</div>'}</div>
        </article>
      </section>
      <section class="grid grid-2" style="margin-top:18px;">
        <article class="card">
          <h3>Coin log</h3>
          <div class="list">${detail.coins.map((row) => `<div class="item"><h4>${escapeHtml(row.student.full_name)} - ${row.coins} coin</h4><p>${escapeHtml(row.reason)}</p></div>`).join('') || '<div class="empty">Coin harakati yoq</div>'}</div>
        </article>
        <article class="card">
          <h3>Homeworklar</h3>
          <div class="list">${detail.homeworks.map((row) => `<div class="item"><h4>${escapeHtml(row.title)}</h4><p>Deadline: ${row.due_date}</p><div class="actions"><button class="btn btn-inline btn-muted" data-action="open-homework" data-id="${row.id}">Submissionlar</button></div></div>`).join('') || '<div class="empty">Homework yaratilmagan</div>'}</div>
        </article>
      </section>
    ` : '<div class="card empty">Teacher uchun hali guruh biriktirilmagan.</div>'}
  `;

  root.innerHTML = layout({
    user: state.user,
    title: 'Teacher Workspace',
    subtitle: 'Davomat, baho, coin va homework boshqaruvi bir joyda.',
    nav: nav || '<div class="empty">Guruhlar topilmadi</div>',
    content: overview,
  });

  root.querySelector('[data-action="logout"]').addEventListener('click', state.onLogout);
  root.querySelectorAll('[data-view]').forEach((button) => button.addEventListener('click', () => state.onSelectGroup(button.dataset.view)));

  if (!detail) return;

  root.querySelector('#attendance-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    await state.safeAction(async () => api.createAttendance(currentGroupId, {
      student_id: Number(formData.get('student_id')),
      lesson_date: formData.get('lesson_date'),
      status: formData.get('status'),
      notes: formData.get('notes') || null,
    }), 'Davomat saqlandi');
  });

  root.querySelector('#mark-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    await state.safeAction(async () => api.createMark(currentGroupId, {
      student_id: Number(formData.get('student_id')),
      score: Number(formData.get('score')),
      notes: formData.get('notes') || null,
    }), 'Baho qoyildi');
  });

  root.querySelector('#coin-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    await state.safeAction(async () => api.createCoin(currentGroupId, {
      student_id: Number(formData.get('student_id')),
      coins: Number(formData.get('coins')),
      reason: formData.get('reason'),
    }), 'Coin berildi');
  });

  root.querySelector('#homework-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    await state.safeAction(async () => api.createHomework(currentGroupId, {
      title: formData.get('title'),
      description: formData.get('description'),
      due_date: formData.get('due_date'),
      max_score: Number(formData.get('max_score')),
    }), 'Homework yaratildi');
  });

  root.querySelectorAll('[data-action="open-homework"]').forEach((button) => {
    button.addEventListener('click', async () => {
      const data = await api.homeworkDetail(button.dataset.id);
      const summary = data.submissions.length
        ? data.submissions.map((item) => `#${item.id} - ${item.student.full_name}`).join('\n')
        : 'Submissionlar hozircha yoq';
      const submissionId = prompt(`Submission ID ni kiriting:\n${summary}`);
      if (!submissionId) return;
      const score = prompt('Ball kiriting (0-100):', '90');
      const coins = prompt('Coin kiriting (0-100):', '10');
      const note = prompt('Izoh:', 'Yaxshi bajarilgan');
      await state.safeAction(async () => api.reviewSubmission(Number(submissionId), {
        score: Number(score || 0),
        awarded_coins: Number(coins || 0),
        review_note: note,
      }), 'Submission review qilindi');
    });
  });
}
