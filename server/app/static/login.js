// Login "normal" de la tienda: guarda el token y pasa a /productos.
// A proposito en localStorage (sin HttpOnly), para que sea facil
// inspeccionarlo despues desde /alumno-devtools.

// Si ya hay un token valido (sesion existente), no hace falta loguearse de
// nuevo: redirige directo a /productos. Si el token quedo invalido/vencido,
// se borra y se queda en el login.
(async () => {
  const token = localStorage.getItem('token');
  if (!token) return;

  const res = await fetch('/me', { headers: { Authorization: `Bearer ${token}` } });
  if (res.ok) {
    window.location.href = '/productos';
  } else {
    localStorage.removeItem('token');
  }
})();

document.getElementById('loginForm').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const errorEl = document.getElementById('error');
  errorEl.textContent = '';

  const res = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const data = await res.json();

  if (!res.ok || !data.token) {
    errorEl.textContent = data.error || 'No se pudo iniciar sesion';
    return;
  }

  localStorage.setItem('token', data.token);
  window.location.href = '/productos';
});
