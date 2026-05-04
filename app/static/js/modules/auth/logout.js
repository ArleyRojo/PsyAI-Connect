async function cerrarSesion() {
  await fetch('/api/logout', {
    method: 'POST',
    credentials: 'include'
  });
  try {
    localStorage.removeItem('usuario');
    localStorage.removeItem('sessionUser');
  } catch (_) {}
  window.location.href = '../index.html';
}
