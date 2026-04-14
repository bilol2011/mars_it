const TOKEN_KEY = 'mars_it_token';
const USER_KEY = 'mars_it_user';

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? JSON.parse(raw) : null;
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = getToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(path, { ...options, headers });
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || 'So`rov bajarilmadi');
  }
  return data;
}

export const api = {
  getToken,
  getStoredUser,
  setSession,
  clearSession,
  async login(username, password) {
    const form = new URLSearchParams();
    form.append('username', username);
    form.append('password', password);
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form.toString(),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Login muvaffaqiyatsiz');
    }
    setSession(data.access_token, data.user);
    return data;
  },
  me: () => request('/api/auth/me'),
  directions: () => request('/api/meta/directions'),
  adminDashboard: () => request('/api/admin/dashboard'),
  groups: () => request('/api/groups'),
  createGroup: (payload) => request('/api/groups', { method: 'POST', body: JSON.stringify(payload) }),
  updateGroup: (id, payload) => request(`/api/groups/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteGroup: (id) => request(`/api/groups/${id}`, { method: 'DELETE' }),
  students: () => request('/api/students'),
  createStudent: (payload) => request('/api/students', { method: 'POST', body: JSON.stringify(payload) }),
  updateStudent: (id, payload) => request(`/api/students/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteStudent: (id) => request(`/api/students/${id}`, { method: 'DELETE' }),
  teachers: () => request('/api/teachers'),
  assignStudent: (groupId, studentId) => request(`/api/groups/${groupId}/students`, { method: 'POST', body: JSON.stringify({ student_id: Number(studentId) }) }),
  assignTeacher: (groupId, teacherId) => request(`/api/groups/${groupId}/teacher`, { method: 'POST', body: JSON.stringify({ teacher_id: Number(teacherId) }) }),
  teacherDashboard: () => request('/api/teacher/dashboard'),
  teacherGroupDetail: (groupId) => request(`/api/teacher/groups/${groupId}`),
  createAttendance: (groupId, payload) => request(`/api/groups/${groupId}/attendance`, { method: 'POST', body: JSON.stringify(payload) }),
  createMark: (groupId, payload) => request(`/api/groups/${groupId}/marks`, { method: 'POST', body: JSON.stringify(payload) }),
  createCoin: (groupId, payload) => request(`/api/groups/${groupId}/coins`, { method: 'POST', body: JSON.stringify(payload) }),
  createHomework: (groupId, payload) => request(`/api/groups/${groupId}/homeworks`, { method: 'POST', body: JSON.stringify(payload) }),
  homeworkDetail: (homeworkId) => request(`/api/homeworks/${homeworkId}`),
  reviewSubmission: (submissionId, payload) => request(`/api/submissions/${submissionId}/review`, { method: 'POST', body: JSON.stringify(payload) }),
  studentDashboard: () => request('/api/student/dashboard'),
  submitHomework: (homeworkId, payload) => request(`/api/homeworks/${homeworkId}/submit`, { method: 'POST', body: JSON.stringify(payload) }),
};
