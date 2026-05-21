// ============================================================
// js/shared/nombre.usuario.js — Cargar nombre de usuario y avatares por inicial
// ============================================================

document.addEventListener('DOMContentLoaded', async function() {
    await cargarNombreUsuario();
    cargarAvatares();
});

async function cargarNombreUsuario() {
    try {
        const res = await fetch("/api/session", {
            credentials: "include"
        });
        
        if (res.status === 401) {
            return;
        }
        
        const data = await res.json();

        if (data.success && data.usuario) {
            const nombre = data.usuario.nombre || data.usuario.email?.split('@')[0] || 'Usuario';
            const rol = data.usuario.rol || data.usuario.role || '';

            actualizarNombresEnPagina(nombre, rol);
        }
    } catch(err) {
        console.error("Error cargando usuario:", err);
    }
}

function cargarAvatares() {
    const elementos = document.querySelectorAll('[data-avatar="inicial"]');
    const storedUser = localStorage.getItem('usuario') || localStorage.getItem('sessionUser');
    let nombre = 'Usuario';
    
    if (storedUser) {
        try {
            const usuario = JSON.parse(storedUser);
            nombre = usuario.nombre || usuario.email?.split('@')[0] || 'Usuario';
        } catch(e) {}
    }
    
    elementos.forEach(el => {
        const nombreEl = el.dataset.nombre || nombre;
        generarAvatar(nombreEl, el);
    });
}

function generarAvatar(nombre, elemento) {
    const inicial = nombre ? nombre.charAt(0).toUpperCase() : '?';
    
    const colores = {
        'A':'#1D9E75','B':'#378ADD','C':'#D85A30','D':'#534AB7','E':'#BA7517',
        'F':'#639922','G':'#D4537E','H':'#1D9E75','I':'#378ADD','J':'#D85A30',
        'K':'#534AB7','L':'#BA7517','M':'#639922','N':'#D4537E','O':'#1D9E75',
        'P':'#378ADD','Q':'#D85A30','R':'#534AB7','S':'#BA7517','T':'#639922',
        'U':'#D4537E','V':'#1D9E75','W':'#378ADD','X':'#D85A30','Y':'#534AB7',
        'Z':'#BA7517'
    };
    const letra = inicial.toUpperCase();
    const colorFondo = colores[letra] || '#6c757d';
    
    const width = elemento.style.width || elemento.offsetWidth || 40;
    const height = elemento.style.height || elemento.offsetHeight || 40;
    
    const div = document.createElement('div');
    div.style.width = (typeof width === 'string' && width.includes('px') ? width : width + 'px');
    div.style.height = (typeof height === 'string' && height.includes('px') ? height : height + 'px');
    div.style.borderRadius = '50%';
    div.style.backgroundColor = colorFondo;
    div.style.color = 'white';
    div.style.fontWeight = '500';
    div.style.display = 'flex';
    div.style.alignItems = 'center';
    div.style.justifyContent = 'center';
    div.style.fontSize = Math.floor(parseInt(width) * 0.4) + 'px';
    div.textContent = inicial;
    
    elemento.parentNode.replaceChild(div, elemento);
}

function actualizarNombresEnPagina(nombre, rol) {
    const elementos = document.querySelectorAll('#nombrePaciente, #nombreProfesional, #nombrPaciente, .user-info span');
    
    elementos.forEach(el => {
        if (!el) return;
        
        if (el.id === 'nombrePaciente' || el.id === 'nombrPaciente') {
            el.textContent = `Hola, ${nombre}`;
        } else if (el.id === 'nombreProfesional') {
            const prefijo = (rol === 'profesional' || rol === 'professional') ? 'Dr(a). ' : '';
            el.textContent = `Hola, ${prefijo}${nombre}`;
        } else if (el.textContent.includes('Hola')) {
            el.textContent = `Hola, ${nombre}`;
        }
    });

    const headerSpans = document.querySelectorAll('.user-info span');
    headerSpans.forEach(span => {
        if (span.textContent.trim() === '' || span.textContent === 'Hola, ') {
            span.textContent = `Hola, ${nombre}`;
        }
    });
}

function getNombreUsuario() {
    const storedUser = localStorage.getItem('usuario') || localStorage.getItem('sessionUser');
    if (storedUser) {
        try {
            const usuario = JSON.parse(storedUser);
            return usuario.nombre || usuario.email?.split('@')[0] || 'Usuario';
        } catch(e) {
            return 'Usuario';
        }
    }
    return 'Usuario';
}
