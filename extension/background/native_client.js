/**
 * Wrapper pour la communication Native Messaging.
 * Gère la connexion persistante et les erreurs.
 */
class NativeClient {
    constructor(appName) {
        this.appName = appName;
        this.port = null;
        this.isConnected = false;
        this._nextRequestId = 1;
        this._pendingRequests = new Map();
    }

    connect() {
        try {
            console.log(`Connecting to Native Host: ${this.appName}`);
            this.port = browser.runtime.connectNative(this.appName);
            
            this.port.onMessage.addListener((response) => {
                this._handleMessage(response);
            });

            this.port.onDisconnect.addListener((p) => {
                const message = p?.error?.message || "Native Host Disconnected";
                if (p && p.error) {
                    console.error(`Native Host Disconnected with error: ${message}`);
                } else {
                    console.log(message);
                }

                // Reject any in-flight requests so UI gets a real error
                for (const [requestId, pending] of this._pendingRequests.entries()) {
                    try {
                        pending.reject(new Error(message));
                    } catch (_) {
                        // ignore
                    }
                    this._pendingRequests.delete(requestId);
                }

                this.isConnected = false;
                this.port = null;
            });

            this.isConnected = true;
        } catch (e) {
            console.error("Failed to connect to Native Host:", e);
            this.isConnected = false;
        }
    }

    sendMessage(message) {
        if (!this.isConnected || !this.port) {
            this.connect();
        }
        
        if (this.isConnected) {
            this.port.postMessage(message);
        } else {
            console.error("Cannot send message: Native Host not connected.");
        }
    }

    sendRequest(message, { timeoutMs = 5000 } = {}) {
        if (!this.isConnected || !this.port) {
            this.connect();
        }

        if (!this.isConnected || !this.port) {
            return Promise.reject(new Error("Native Host not connected"));
        }

        const requestId = String(this._nextRequestId++);
        const messageWithId = { ...message, request_id: requestId };

        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                this._pendingRequests.delete(requestId);
                reject(new Error("Native request timed out"));
            }, timeoutMs);

            this._pendingRequests.set(requestId, {
                resolve: (resp) => {
                    clearTimeout(timeout);
                    resolve(resp);
                },
                reject: (err) => {
                    clearTimeout(timeout);
                    reject(err);
                }
            });

            try {
                this.port.postMessage(messageWithId);
            } catch (e) {
                clearTimeout(timeout);
                this._pendingRequests.delete(requestId);
                reject(e);
            }
        });
    }

    _handleMessage(response) {
        console.log("Received from Native Host:", response);

        // Resolve pending request first (health/test-connection)
        const requestId = response && response.request_id;
        if (requestId && this._pendingRequests.has(String(requestId))) {
            const pending = this._pendingRequests.get(String(requestId));
            this._pendingRequests.delete(String(requestId));
            pending.resolve(response);
            return;
        }

        // Dispatch event for background.js to handle
        const event = new CustomEvent('native-response', { detail: response });
        window.dispatchEvent(event);
    }
}

// Export global pour background.js
window.NativeClient = NativeClient;
