const LocalStorageDetector = {
    isAvailable: false,
    init() {
        try {
            const test = '__localStorage_test__';
            localStorage.setItem(test, test);
            localStorage.removeItem(test);
            this.isAvailable = true;
            this.setupGlobalListener();
        } catch (e) {
            this.isAvailable = false;
            console.warn('localStorage no disponible:', e);
        }
        return this.isAvailable;
    },
    setupGlobalListener() {
        window.addEventListener('storage', (e) => {
            window.dispatchEvent(new CustomEvent('localStorageChange', {
                detail: {
                    key: e.key,
                    oldValue: e.oldValue,
                    newValue: e.newValue,
                    url: e.url
                }
            }));
        });
    },
    getItem(key, defaultValue = null) {
        if (!this.isAvailable) return defaultValue;
        try {
            const item = localStorage.getItem(key);
            if (item === null) return defaultValue;
            try {
                return JSON.parse(item);
            } catch {
                return item;
            }
        } catch {
            return defaultValue;
        }
    },
    setItem(key, value) {
        if (!this.isAvailable) return false;
        try {
            const valueToStore = typeof value === 'object' ? JSON.stringify(value) : value;
            localStorage.setItem(key, valueToStore);
            return true;
        } catch {
            return false;
        }
    },
    removeItem(key) {
        if (!this.isAvailable) return false;
        try {
            localStorage.removeItem(key);
            return true;
        } catch {
            return false;
        }
    },
    clear() {
        if (!this.isAvailable) return false;
        try {
            localStorage.clear();
            return true;
        } catch {
            return false;
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    LocalStorageDetector.init();
});

window.addEventListener('localStorageChange', (e) => {
    const { key, newValue, oldValue } = e.detail;
    
    if (key === 'usuario' || key === 'sessionUser') {
        window.dispatchEvent(new CustomEvent('userSessionChanged', {
            detail: { user: newValue ? JSON.parse(newValue) : null }
        }));
    }
    
    window.dispatchEvent(new CustomEvent('appStorageChanged', {
        detail: { key, newValue, oldValue }
    }));
});

function registrarActividadReciente(tipo, accion, detalle) {
    const actividades = JSON.parse(localStorage.getItem('psyai_actividades_recientes') || '[]');
    const nuevaActividad = {
        id: Date.now(),
        tipo: tipo,
        accion: accion,
        detalle: detalle,
        fecha: new Date().toLocaleString('es-ES'),
        timestamp: Date.now()
    };
    actividades.unshift(nuevaActividad);
    if (actividades.length > 20) actividades.pop();
    localStorage.setItem('psyai_actividades_recientes', JSON.stringify(actividades));
}

function obtenerActividadesRecientes() {
    return JSON.parse(localStorage.getItem('psyai_actividades_recientes') || '[]');
}

window.registrarActividadReciente = registrarActividadReciente;
window.obtenerActividadesRecientes = obtenerActividadesRecientes;
