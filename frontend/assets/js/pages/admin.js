import { api } from '../api/client.js';
import { banner, escapeHtml, layout, navButton, statusBadge } from '../components/ui.js';

export async function renderAdmin(root, state) {
  const [dashboard, groups, students, teachers, directions] = await Promise.all([
    api.adminDashboard(),
    api.groups(),
    api.students(),
    api.teachers(),
    api.directions(),
  ]);

  const activeView = state.view || 'overview';
  const nav = [
    navButton('Dashboard', 'overview', activeView),
    navButton('Guruhlar', 'groups', activeView),
    navButton('Studentlar', 'students', activeView),
  ].join('');

  const overview = `
    <section class="grid grid-4">
      <article class="card stat-card"><strong>${dashboard.total_students}</strong><span>Jami o'quvchilar</span></article>
      <article class="card stat-card"><strong>${dashboard.total_teachers}</strong><span>Jami o'qituvchilar</span></article>
      <article class="card stat-card"><strong>${dashboard.total_groups}</strong><span>Faol guruhlar</span></article>
      <article class="card stat-card"><strong>${dashboard.attendance_summary.present}</strong><span>Present attendance</span></article>
    </section>
    <section class="grid grid-2" style="margin-top:18px;">
      <article class="card">
        <h3 class="section-title">Attendance holati</h3>
        <div class="chart-bars">
          ${['present','late','absent'].map((key) => {
            const total = Object.values(dashboard.attendance_summary).reduce((sum, value) => sum + value, 0) || 1;
            const width = Math.round((dashboard.attendance_summary[key] / total) * 100);
            return `<div class="chart-row"><span><strong>${key}</strong><em>${dashboard.attendance_summary[key]}</em></span><div class="chart-track"><div class="chart-fill" style="width:${width}%"></div></div></div>`;
          }).join('')}
        </div>
      </article>
      <article class="card">
        <h3 class="section-title">Yo'nalishlar bo'yicha guruhlar</h3>
        <div class="list">
          ${dashboard.direction_breakdown.map((item) => `<div class="item"><h4>${escapeHtml(item.name)}</h4><p>${item.groups} ta guruh</p></div>`).join('')}
        </div>
      </article>
    </section>
  `;

  const groupsView = `
    <section class="grid grid-2">
      <article class="card form-card">
        <h3>Yangi guruh yaratish</h3>
        ${banner(state.flashType, state.flashMessage)}
        <form id="group-form" class="form-grid">
          <input class="input" name="name" placeholder="Masalan: Frontend N2" required />
          <select name="direction_id" required>
            <option value="">Yo'nalishni tanlang</option>
            ${directions.map((direction) => `<option value="${direction.id}">${escapeHtml(direction.name)}</option>`).join('')}
          </select>
          <select name="teacher_id">
            <option value="">Teacher biriktirish</option>
            ${teachers.map((teacher) => `<option value="${teacher.id}">${escapeHtml(teacher.full_name)} - ${escapeHtml(teacher.specialty || '')}</option>`).join('')}
          </select>
          <input class="input" name="classroom" placeholder="Dars xonasi (masalan: A4)" />
          <input class="input" name="lesson_time" placeholder="Dars vaqti (masalan: 18:00 - 20:00)" />
          <input class="input" type="number" name="duration_months" min="1" placeholder="Davomiylik (oy)" />
          <input class="input" name="schedule" placeholder="Dars kunlari (masalan: Mon/Wed/Fri)" />
          <input class="input" type="date" name="starts_on" />
          <button class="btn btn-primary">Saqlash</button>
        </form>
      </article>
      <article class="card">
        <h3>Mavjud guruhlar</h3>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Nomi</th><th>Yo'nalish</th><th>Teacher</th><th>Xona</th><th>Vaqt</th><th>Davom</th><th>Student</th><th>Amal</th></tr></thead>
            <tbody>
              ${groups.map((group) => `
                <tr>
                  <td>${escapeHtml(group.name)}</td>
                  <td>${escapeHtml(group.direction.name)}</td>
                  <td>${escapeHtml(group.teacher?.full_name || 'Biriktirilmagan')}</td>
                  <td>${escapeHtml(group.classroom || '-')}</td>
                  <td>${escapeHtml(group.lesson_time || '-')}</td>
                  <td>${group.duration_months ? `${group.duration_months} oy` : '-'}</td>
                  <td>${group.student_count}</td>
                  <td class="actions">
                    <button class="btn btn-inline btn-muted" data-action="prefill-group" data-id="${group.id}">Tahrirlash</button>
                    <button class="btn btn-inline btn-danger" data-action="delete-group" data-id="${group.id}">O'chirish</button>
                  </td>
                </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </article>
    </section>
    <section class="card" style="margin-top:18px;">
      <h3>Student biriktirish</h3>
      <form id="assign-student-form" class="grid grid-3">
        <select name="group_id" required>
          <option value="">Guruh tanlang</option>
          ${groups.map((group) => `<option value="${group.id}">${escapeHtml(group.name)}</option>`).join('')}
        </select>
        <select name="student_id" required>
          <option value="">Student tanlang</option>
          ${students.map((student) => `<option value="${student.id}">${escapeHtml(student.full_name)}</option>`).join('')}
        </select>
        <button class="btn btn-secondary">Biriktirish</button>
      </form>
    </section>
  `;

  const studentsView = `
    <section class="grid grid-2">
      <article class="card form-card">
        <h3>Yangi student qo'shish</h3>
        ${banner(state.flashType, state.flashMessage)}
        <form id="student-form" class="form-grid">
          <input class="input" name="username" placeholder="student11" required />
          <input class="input" name="full_name" placeholder="To'liq ism" required />
          <input class="input" name="password" placeholder="Parol" required />
          <input class="input" name="phone" placeholder="Telefon" />
          <input class="input" name="parent_phone" placeholder="Ota-ona telefoni" />
          <button class="btn btn-primary">Student yaratish</button>
        </form>
      </article>
      <article class="card">
        <h3>Studentlar ro'yxati</h3>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Ism</th><th>Login</th><th>Telefon</th><th>Guruhlar</th><th>Amal</th></tr></thead>
            <tbody>
              ${students.map((student) => `
                <tr>
                  <td>${escapeHtml(student.full_name)}</td>
                  <td>${escapeHtml(student.username)}</td>
                  <td>${escapeHtml(student.phone || '-')}</td>
                  <td>${student.groups.map((group) => `<span class="badge blue">${escapeHtml(group.name)}</span>`).join(' ') || '-'}</td>
                  <td><button class="btn btn-inline btn-danger" data-action="delete-student" data-id="${student.id}">O'chirish</button></td>
                </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  `;

  const body = activeView === 'groups' ? groupsView : activeView === 'students' ? studentsView : overview;

  root.innerHTML = layout({
    user: state.user,
    title: 'Admin Panel',
    subtitle: 'Markazning umumiy boshqaruvi va operatsion nazorati.',
    nav,
    content: body,
  });

  root.querySelectorAll('[data-view]').forEach((button) => {
    button.addEventListener('click', () => state.onNavigate(button.dataset.view));
  });

  root.querySelector('[data-action="logout"]').addEventListener('click', state.onLogout);

  const groupForm = root.querySelector('#group-form');
  if (groupForm) {
    groupForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(groupForm);
      await state.safeAction(async () => {
        await api.createGroup({
          name: formData.get('name'),
          direction_id: Number(formData.get('direction_id')),
          teacher_id: formData.get('teacher_id') ? Number(formData.get('teacher_id')) : null,
          classroom: formData.get('classroom') || null,
          lesson_time: formData.get('lesson_time') || null,
          duration_months: formData.get('duration_months') ? Number(formData.get('duration_months')) : null,
          schedule: formData.get('schedule') || null,
          starts_on: formData.get('starts_on') || null,
        }, 'Guruh yaratildi');
      });
    });
  }

  const assignForm = root.querySelector('#assign-student-form');
  if (assignForm) {
    assignForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(assignForm);
      await state.safeAction(async () => {
        await api.assignStudent(formData.get('group_id'), formData.get('student_id'));
      }, 'Student guruhga biriktirildi');
    });
  }

  const studentForm = root.querySelector('#student-form');
  if (studentForm) {
    studentForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(studentForm);
      await state.safeAction(async () => {
        await api.createStudent(Object.fromEntries(formData.entries()));
      }, 'Student yaratildi');
    });
  }

  root.querySelectorAll('[data-action="delete-group"]').forEach((button) => {
    button.addEventListener('click', async () => {
      await state.safeAction(async () => api.deleteGroup(button.dataset.id), 'Guruh o\'chirildi');
    });
  });

  root.querySelectorAll('[data-action="prefill-group"]').forEach((button) => {
    button.addEventListener('click', async () => {
      const group = groups.find((item) => item.id === Number(button.dataset.id));
      if (!group) return;
      const name = prompt('Guruh nomi:', group.name);
      if (!name) return;
      const classroom = prompt('Dars xonasi:', group.classroom || '');
      const lessonTime = prompt('Dars vaqti:', group.lesson_time || '');
      const duration = prompt('Davomiylik (oy):', group.duration_months ? String(group.duration_months) : '');
      const schedule = prompt('Dars kunlari:', group.schedule || '');
      await state.safeAction(async () => api.updateGroup(group.id, {
        name,
        classroom: classroom || null,
        lesson_time: lessonTime || null,
        duration_months: duration ? Number(duration) : null,
        schedule: schedule || null,
      }), 'Guruh yangilandi');
    });
  });

  root.querySelectorAll('[data-action="delete-student"]').forEach((button) => {
    button.addEventListener('click', async () => {
      await state.safeAction(async () => api.deleteStudent(button.dataset.id), 'Student o\'chirildi');
    });
  });
}
