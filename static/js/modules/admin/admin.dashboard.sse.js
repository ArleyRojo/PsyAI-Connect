class SSEConnection {
    constructor(url, onMessage, onError) {
        this.url = url;
        this.onMessage = onMessage;
        this.onError = onError;
        this.source = null;
        this.reconnectTimer = null;
        this.active = false;
        this.paused = false;

        // Chrome solo permite 6 conexiones a la vez con el mismo sitio y cada stream
        // abierto ocupa una aunque nadie mire la pestaña. Se pausa al ocultarla.
        document.addEventListener('visibilitychange', () => {
            if (!this.active) return;
            if (document.hidden) {
                this._pause();
            } else if (this.paused) {
                this.paused = false;
                this.connect();
            }
        });
        // Al salir de la página se cierra para que el servidor libere el hilo.
        window.addEventListener('pagehide', () => this.disconnect());
    }

    _pause() {
        this.paused = true;
        clearTimeout(this.reconnectTimer);
        if (this.source) {
            this.source.close();
            this.source = null;
        }
    }

    connect() {
        if (this.source) return;
        this.active = true;
        if (document.hidden) {
            this.paused = true;
            return;
        }
        this.source = new EventSource(this.url, { withCredentials: true });
        this.source.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (this.onMessage) this.onMessage(data);
            } catch (e) {
                console.error('SSE parse error:', e);
            }
        };
        this.source.onerror = () => {
            console.warn('SSE disconnected from', this.url);
            this.source.close();
            this.source = null;
            if (this.active) {
                if (this.onError) this.onError();
                this.reconnectTimer = setTimeout(() => this.connect(), 3000);
            }
        };
    }

    disconnect() {
        this.active = false;
        clearTimeout(this.reconnectTimer);
        if (this.source) {
            this.source.close();
            this.source = null;
        }
    }
}
