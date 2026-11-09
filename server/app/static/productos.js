// Vista "normal" de la tienda: perfil + catalogo + comprar.
// Toda decision de negocio (saldo, descuento VIP) la toma el SERVIDOR
// con lo que dice el token -- justamente lo que el desafio explota.

function getToken() {
  return localStorage.getItem('token') || '';
}

async function cargarPerfil() {
  const res = await fetch('/me', { headers: { Authorization: `Bearer ${getToken()}` } });
  if (!res.ok) {
    localStorage.removeItem('token');
    window.location.href = '/';
    return;
  }
  // username/balance/isVip vienen del TOKEN, no de la base (ver routes.py):
  // si alguien lo forjo, pueden traer cualquier valor, incluido texto
  // arbitrario en "username". Por eso se insertan como texto (textContent),
  // nunca como HTML, para no sumar un XSS encima de la vulnerabilidad del
  // desafio.
  const perfil = await res.json();
  const barra = document.getElementById('perfilBar');
  barra.textContent = '';

  const saludo = document.createElement('span');
  saludo.append('Hola, ');
  const nombre = document.createElement('strong');
  nombre.textContent = perfil.username;
  saludo.append(nombre, ` · Saldo: $${perfil.balance} `);
  barra.appendChild(saludo);

  if (perfil.isVip) {
    const vip = document.createElement('span');
    vip.className = 'vip';
    vip.textContent = '★ VIP';
    barra.appendChild(vip);
  }
}

async function cargarCatalogo() {
  const res = await fetch('/tienda/catalogo');
  const productos = await res.json();
  const cont = document.getElementById('catalogo');
  cont.textContent = '';

  for (const p of productos) {
    const card = document.createElement('div');
    card.className = 'producto';

    const titulo = document.createElement('h3');
    titulo.textContent = p.producto;

    const precio = document.createElement('div');
    precio.className = 'precio';
    precio.textContent = `$${p.precio}`;

    const boton = document.createElement('button');
    boton.textContent = 'Comprar';

    const resultado = document.createElement('div');
    resultado.className = 'resultado';

    boton.addEventListener('click', () => comprar(p.producto, card));
    card.append(titulo, precio, boton, resultado);
    cont.appendChild(card);
  }
}

async function comprar(producto, card) {
  const resultadoEl = card.querySelector('.resultado');
  resultadoEl.textContent = 'Procesando...';
  resultadoEl.className = 'resultado';

  const res = await fetch('/tienda/comprar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
    body: JSON.stringify({ producto }),
  });
  const data = await res.json();

  if (res.ok && data.ok) {
    resultadoEl.textContent = `✔ ${data.mensaje} (pagaste $${data.precio_final}${data.descuento_vip_aplicado ? ', con descuento VIP' : ''})`;
    resultadoEl.classList.add('ok');
  } else {
    resultadoEl.textContent = `✘ ${data.error || 'no se pudo comprar'}`;
    resultadoEl.classList.add('err');
  }
}

document.getElementById('logout').addEventListener('click', () => {
  localStorage.removeItem('token');
  window.location.href = '/';
});

if (!getToken()) {
  window.location.href = '/';
} else {
  cargarPerfil();
  cargarCatalogo();
}
