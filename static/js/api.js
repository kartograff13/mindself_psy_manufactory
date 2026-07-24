// api.js

async function getCurrentUser() {
    const token = localStorage.getItem('access_token');
    if (!token) return null;
    const resp = await fetch('/api/auth/profile/', {
        headers: {'Authorization': 'Bearer ' + token}
    });
    if (resp.status === 200) return await resp.json();
    return null;
}

function getUserRole() {
    return localStorage.getItem('user_role') || null;
}

async function updateUserRole() {
    const user = await getCurrentUser();
    if (user) {
        localStorage.setItem('user_role', user.role);
        localStorage.setItem('user_id', user.id);
        return user.role;
    }
    localStorage.removeItem('user_role');
    localStorage.removeItem('user_id');
    return null;
}

function isTeacherOrAdmin(role) {
    return role === 'teacher' || role === 'admin';
}

function getUserId() {
    return parseInt(localStorage.getItem('user_id') || '0');
}