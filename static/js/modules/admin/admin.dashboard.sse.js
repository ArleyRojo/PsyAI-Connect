class SSEConnection {
    constructor(url, onMessage, onError) {
        this.url = url;
        this.onMessage = onMessage;
        this.onError = onError;
        this.source = null;
        this.reconnectTimer = null;
        this.active = false;
    }

    connect() {
        if (this.source) return;
        this.active = true;
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
