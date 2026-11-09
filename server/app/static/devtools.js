// Herramientas de alumno: guarda el token en localStorage (a proposito,
// sin HttpOnly, para que sea facil de inspeccionar en DevTools) y lo manda
// como Bearer en cada request. Todos los valores se muestran como texto
// (textContent), nunca como HTML, para no sumar un XSS encima de la
// vulnerabilidad del desafio.

function getToken() {
  return localStorage.getItem('token') || '';
}

function setToken(token) {
  localStorage.setItem('token', token);
  document.getElementById('token').textContent = token || '-';
}

document.getElementById('btnLogin').addEventListener('click', async () => {
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const res = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const data = await res.json();
  if (data.token) setToken(data.token);
  else document.getElementById('token').textContent = JSON.stringify(data);
});

document.getElementById('btnMe').addEventListener('click', async () => {
  const res = await fetch('/me', { headers: { Authorization: `Bearer ${getToken()}` } });
  document.getElementById('perfil').textContent = JSON.stringify(await res.json(), null, 2);
});

document.getElementById('btnComprar').addEventListener('click', async () => {
  const producto = document.getElementById('producto').value;
  const res = await fetch('/tienda/comprar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
    body: JSON.stringify({ producto }),
  });
  document.getElementById('compra').textContent = JSON.stringify(await res.json(), null, 2);
});

document.getElementById('btnUsarForjado').addEventListener('click', () => {
  const t = document.getElementById('tokenForjado').value.trim();
  if (t) setToken(t);
});
