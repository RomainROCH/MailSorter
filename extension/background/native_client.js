/**
 * Wrapper pour la communication Native Messaging.
 * Gère la connexion persistante et les erreurs.
 */
class NativeClient {
    constructor(appName) {
        this.appName = appName;
        this.port = null;
        this.isConnected = false;
    }

    connect() {
        try {
            console.log(`Connecting to Native Host: ${this.appName}`);
            this.port = browser.runtime.connectNative(this.appName);
            
            this.port.onMessage.addListener((response) => {
                this._handleMessage(response);
            });

            this.port.onDisconnect.addListener((p) => {
                if (p.error) {
                    console.error(`Native Host Disconnected with error: ${p.error.message}`);
                } else {
                    console.log("Native Host Disconnected");
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

    _handleMessage(response) {
        console.log("Received from Native Host:", response);
        // Dispatch event for background.js to handle
        const event = new CustomEvent('native-response', { detail: response });
        window.dispatchEvent(event);
    }
}

// Export global pour background.js
window.NativeClient = NativeClient;
