class SecureRemoteControl {
    constructor() {
        // Initialize managers
        this.authManager = new AuthManager();
        this.rtcManager = new RTCManager();
        this.uiManager = new UIManager();
        this.eventManager = new EventManager(this);
        
        // App state
        this.state = {
            isConnected: false,
            isHost: false,
            permissions: {
                mouse: true,
                keyboard: true,
                clipboard: false,
                fileTransfer: false,
                admin: false
            },
            connectionDetails: {
                id: '',
                password: '',
                partnerId: '',
                partnerPassword: ''
            }
        };
        
        // Initialize the app
        this.init();
    }

    init() {
        // Generate initial credentials
        this.generateCredentials();
        
        // Setup UI
        this.uiManager.initUI();
        
        // Setup event listeners
        this.eventManager.setupEventListeners();
        
        // Show consent modal
        this.uiManager.showConsentModal();
    }

    generateCredentials() {
        const credentials = this.authManager.generateCredentials();
        this.state.connectionDetails.id = credentials.id;
        this.state.connectionDetails.password = credentials.password;
        this.uiManager.updateCredentialsDisplay(credentials.id, credentials.password);
    }

    async connectToPartner() {
        try {
            // Validate connection attempt
            this.authManager.validateConnectionAttempt();
            
            // Get partner credentials from UI
            const partnerId = this.uiManager.getPartnerId();
            const partnerPassword = this.uiManager.getPartnerPassword();
            
            // Validate inputs
            if (!this.authManager.validateInputs(partnerId, partnerPassword)) {
                throw new Error('Invalid connection ID or password format');
            }
            
            // Update state
            this.state.connectionDetails.partnerId = partnerId;
            this.state.connectionDetails.partnerPassword = partnerPassword;
            this.state.isHost = false;
            
            // Show connecting state
            this.uiManager.showConnectingState();
            
            // Connect via signaling server
            await this.rtcManager.connectToPartner(
                partnerId, 
                partnerPassword,
                this.handleRTCMessage.bind(this)
            );
            
            // Update connection state
            this.state.isConnected = true;
            this.uiManager.updateConnectionState(true);
            this.authManager.startSessionTimeout(this.disconnect.bind(this));
            
        } catch (error) {
            this.uiManager.showError(error.message);
            this.uiManager.resetConnectionState();
        }
    }

    async startHosting() {
        try {
            // Update state
            this.state.isHost = true;
            
            // Initialize RTC connection
            await this.rtcManager.startHosting(
                this.state.connectionDetails.id,
                this.handleRTCMessage.bind(this)
            );
            
            // Update UI
            this.uiManager.updateConnectionState(true);
            this.authManager.startSessionTimeout(this.disconnect.bind(this));
            
        } catch (error) {
            this.uiManager.showError(error.message);
            this.uiManager.resetConnectionState();
        }
    }

    handleRTCMessage(message) {
        // Handle incoming WebRTC messages
        switch (message.type) {
            case 'screen_data':
                this.uiManager.updateRemoteScreen(message.data);
                break;
            case 'control_command':
                if (this.state.isHost) {
                    this.executeCommand(message.command);
                }
                break;
            case 'status_update':
                this.uiManager.updateRemoteScreenStatus(message.status);
                break;
        }
    }

    executeCommand(command) {
        // Execute command based on permissions
        if (command.type === 'mouse' && !this.state.permissions.mouse) return;
        if (command.type === 'keyboard' && !this.state.permissions.keyboard) return;
        
        // In a real app, this would control the host machine
        console.log('Executing command:', command);
    }

    sendCommand(command) {
        if (this.state.isConnected) {
            this.rtcManager.sendMessage({
                type: 'control_command',
                command: command
            });
        }
    }

    disconnect() {
        // Close RTC connection
        this.rtcManager.disconnect();
        
        // Clear timeout
        this.authManager.clearSessionTimeout();
        
        // Reset state
        this.state.isConnected = false;
        this.state.isHost = false;
        
        // Update UI
        this.uiManager.updateConnectionState(false);
        this.uiManager.resetConnectionState();
    }

    copyCredentials() {
        this.uiManager.copyToClipboard(
            `Connection ID: ${this.state.connectionDetails.id}\nPassword: ${this.state.connectionDetails.password}`
        );
    }

    togglePermission(permission, enabled) {
        if (this.state.permissions.hasOwnProperty(permission)) {
            this.state.permissions[permission] = enabled;
        }
    }
}

class AuthManager {
    constructor() {
        this.connectionAttempts = 0;
        this.lastAttemptTime = 0;
        this.sessionTimeout = null;
    }

    generateCredentials() {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        const crypto = window.crypto || window.msCrypto;
        
        // Generate 12-character alphanumeric ID
        const id = this.generateRandomString(12, chars);
        
        // Generate 16-character complex password
        const password = this.generateRandomString(16, chars + '!@#$%^&*');
        
        return { id, password };
    }

    generateRandomString(length, chars) {
        let result = '';
        const values = new Uint32Array(length);
        crypto.getRandomValues(values);
        
        for (let i = 0; i < length; i++) {
            result += chars[values[i] % chars.length];
        }
        return result;
    }

    validateConnectionAttempt() {
        const now = Date.now();
        if (now - this.lastAttemptTime < 5000) {
            throw new Error('Please wait before attempting another connection');
        }
        
        if (this.connectionAttempts >= 5) {
            throw new Error('Too many failed attempts. Please refresh the page.');
        }
        
        this.connectionAttempts++;
        this.lastAttemptTime = now;
        return true;
    }

    validateInputs(id, password) {
        // Validate connection ID (alphanumeric, 12 chars)
        if (!/^[a-zA-Z0-9]{12}$/.test(id)) {
            throw new Error('Invalid connection ID format');
        }
        
        // Validate password (complex, 8-32 chars)
        if (!/^[a-zA-Z0-9!@#$%^&*]{8,32}$/.test(password)) {
            throw new Error('Invalid password format');
        }
        
        return true;
    }

    startSessionTimeout(callback) {
        this.clearSessionTimeout();
        this.sessionTimeout = setTimeout(callback, 30 * 60 * 1000); // 30 minutes
    }

    clearSessionTimeout() {
        if (this.sessionTimeout) {
            clearTimeout(this.sessionTimeout);
            this.sessionTimeout = null;
        }
    }
}

class RTCManager {
    constructor() {
        this.peerConnection = null;
        this.dataChannel = null;
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 3;
        this.iceServers = [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' },
            { 
                urls: 'turn:your-turn-server.com:3478',
                username: 'your-username',
                credential: 'your-credential' 
            }
        ];
    }

    async connectToSignalingServer() {
        return new Promise((resolve, reject) => {
            this.socket = io('https://branch-shell-iodine.glitch.me', {
                reconnectionAttempts: 5,
                reconnectionDelay: 1000,
                transports: ['websocket']
            });

            this.socket.on('connect', () => resolve());
            this.socket.on('connect_error', (err) => reject(err));
        });
    }

    async connectToPartner(partnerId, partnerPassword, messageHandler) {
        await this.connectToSignalingServer();
        
        return new Promise((resolve, reject) => {
            this.socket.emit('connect_to_host', {
                connectionId: partnerId,
                password: partnerPassword
            });

            this.socket.on('connection_success', async (data) => {
                try {
                    await this.startRTCConnection(false, messageHandler);
                    resolve();
                } catch (err) {
                    reject(err);
                }
            });

            this.socket.on('connection_error', (err) => reject(err));
        });
    }

    async startHosting(connectionId, messageHandler) {
        await this.connectToSignalingServer();
        
        return new Promise((resolve, reject) => {
            this.socket.emit('register_as_host', {
                connectionId: connectionId,
                password: this.generateRandomString(32)
            });

            this.socket.on('registration_success', async () => {
                try {
                    await this.startRTCConnection(true, messageHandler);
                    resolve();
                } catch (err) {
                    reject(err);
                }
            });

            this.socket.on('registration_error', (err) => reject(err));
        });
    }

    async startRTCConnection(isHost, messageHandler) {
        this.peerConnection = new RTCPeerConnection({
            iceServers: this.iceServers,
            iceTransportPolicy: 'relay'
        });

        this.setupICEHandlers();
        this.setupConnectionStateHandlers();

        if (isHost) {
            this.dataChannel = this.peerConnection.createDataChannel('control');
            this.setupDataChannelHandlers(messageHandler);
            
            const offer = await this.peerConnection.createOffer();
            await this.peerConnection.setLocalDescription(offer);
            
            this.socket.emit('webrtc_signal', {
                type: 'offer',
                offer: offer
            });
        } else {
            this.peerConnection.ondatachannel = (event) => {
                this.dataChannel = event.channel;
                this.setupDataChannelHandlers(messageHandler);
            };
        }
    }

    setupICEHandlers() {
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                this.socket.emit('webrtc_signal', {
                    type: 'candidate',
                    candidate: event.candidate
                });
            }
        };
    }

    setupConnectionStateHandlers() {
        this.peerConnection.oniceconnectionstatechange = () => {
            if (this.peerConnection.iceConnectionState === 'failed') {
                this.reconnect();
            }
        };
    }

    setupDataChannelHandlers(messageHandler) {
        this.dataChannel.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                messageHandler(message);
            } catch (err) {
                console.error('Error parsing message:', err);
            }
        };

        this.dataChannel.onopen = () => {
            console.log('Data channel opened');
        };

        this.dataChannel.onclose = () => {
            console.log('Data channel closed');
        };
    }

    async handleSignal(signal) {
        if (!this.peerConnection) return;

        try {
            switch (signal.type) {
                case 'offer':
                    await this.peerConnection.setRemoteDescription(new RTCSessionDescription(signal));
                    const answer = await this.peerConnection.createAnswer();
                    await this.peerConnection.setLocalDescription(answer);
                    this.socket.emit('webrtc_signal', {
                        type: 'answer',
                        answer: answer
                    });
                    break;
                case 'answer':
                    await this.peerConnection.setRemoteDescription(new RTCSessionDescription(signal));
                    break;
                case 'candidate':
                    await this.peerConnection.addIceCandidate(new RTCIceCandidate(signal.candidate));
                    break;
            }
        } catch (err) {
            console.error('Error handling signal:', err);
            throw err;
        }
    }

    sendMessage(message) {
        if (this.dataChannel && this.dataChannel.readyState === 'open') {
            this.dataChannel.send(JSON.stringify(message));
        }
    }

    reconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                this.startRTCConnection(true, this.messageHandler);
            }, 1000 * this.reconnectAttempts);
        } else {
            throw new Error('Failed to reconnect after multiple attempts');
        }
    }

    disconnect() {
        if (this.dataChannel) {
            this.dataChannel.close();
        }
        if (this.peerConnection) {
            this.peerConnection.close();
        }
        if (this.socket) {
            this.socket.disconnect();
        }
        
        this.peerConnection = null;
        this.dataChannel = null;
        this.socket = null;
        this.reconnectAttempts = 0;
    }
}

class UIManager {
    constructor() {
        // Cache DOM elements
        this.elements = {
            connectionIndicator: document.getElementById('connection-indicator'),
            securityBadge: document.getElementById('security-badge'),
            yourUriInput: document.getElementById('your-uri'),
            yourPasswordInput: document.getElementById('your-password'),
            partnerUriInput: document.getElementById('partner-uri'),
            partnerPasswordInput: document.getElementById('partner-password'),
            connectBtn: document.getElementById('connect-btn'),
            serverStatus: document.getElementById('server-status'),
            clientStatus: document.getElementById('client-status'),
            remoteScreenContainer: document.getElementById('remote-screen-container'),
            remoteScreenImg: document.getElementById('remote-screen-img'),
            remoteScreenStatus: document.getElementById('remote-screen-status'),
            consentModal: document.getElementById('consent-modal'),
            understandRisks: document.getElementById('understand-risks'),
            acceptConsent: document.getElementById('accept-consent'),
            declineConsent: document.getElementById('decline-consent'),
            disconnectModal: document.getElementById('disconnect-modal'),
            confirmDisconnect: document.getElementById('confirm-disconnect'),
            cancelDisconnect: document.getElementById('cancel-disconnect'),
            errorModal: document.getElementById('error-modal'),
            errorMessage: document.getElementById('error-message'),
            closeErrorBtn: document.getElementById('close-error-btn'),
            toast: document.getElementById('toast'),
            copyCredentialsBtn: document.getElementById('copy-credentials'),
            refreshCredentialsBtn: document.getElementById('refresh-credentials'),
            fullscreenBtn: document.getElementById('fullscreen-btn'),
            disconnectBtn: document.getElementById('disconnect-btn'),
            permissionMouse: document.getElementById('permission-mouse'),
            permissionKeyboard: document.getElementById('permission-keyboard'),
            permissionClipboard: document.getElementById('permission-clipboard')
        };
    }

    initUI() {
        // Initialize any UI components
    }

    updateCredentialsDisplay(id, password) {
        this.elements.yourUriInput.value = id;
        this.elements.yourPasswordInput.value = password;
    }

    showConnectingState() {
        this.elements.connectBtn.disabled = true;
        // Show loading spinner
    }

    updateConnectionState(connected) {
        this.elements.connectionIndicator.classList.toggle('active', connected);
        this.elements.securityBadge.textContent = connected ? 
            'Connection: Secure (E2E Encrypted)' : 
            'Connection: Not Secure';
        this.elements.securityBadge.style.backgroundColor = connected ? 
            'var(--success-color)' : 'var(--danger-color)';
        
        if (connected) {
            this.elements.connectBtn.textContent = 'Disconnect';
            this.elements.connectBtn.classList.remove('btn-success');
            this.elements.connectBtn.classList.add('btn-primary');
            this.elements.remoteScreenContainer.style.display = 'block';
        } else {
            this.elements.connectBtn.textContent = 'Connect to Partner';
            this.elements.connectBtn.classList.remove('btn-primary');
            this.elements.connectBtn.classList.add('btn-success');
            this.elements.remoteScreenContainer.style.display = 'none';
        }
        
        this.elements.connectBtn.disabled = false;
    }

    resetConnectionState() {
        // Hide loading spinner
    }

    updateRemoteScreen(imageData) {
        this.elements.remoteScreenImg.src = imageData;
    }

    updateRemoteScreenStatus(status) {
        this.elements.remoteScreenStatus.textContent = status;
    }

    showConsentModal() {
        this.elements.consentModal.style.display = 'flex';
    }

    showError(message) {
        this.elements.errorMessage.textContent = message;
        this.elements.errorModal.style.display = 'flex';
    }

    showToast(message) {
        this.elements.toast.textContent = message;
        this.elements.toast.classList.add('show');
        
        setTimeout(() => {
            this.elements.toast.classList.remove('show');
        }, 3000);
    }

    copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showToast('Copied to clipboard!');
        }).catch(err => {
            console.error('Failed to copy:', err);
            this.showError('Failed to copy to clipboard');
        });
    }

    getPartnerId() {
        return this.elements.partnerUriInput.value.trim();
    }

    getPartnerPassword() {
        return this.elements.partnerPasswordInput.value.trim();
    }
}

class EventManager {
    constructor(app) {
        this.app = app;
    }

    setupEventListeners() {
        // Setup all event listeners
        this.setupButtonEvents();
        this.setupConsentEvents();
        this.setupModalEvents();
        this.setupPermissionEvents();
    }

    setupButtonEvents() {
        this.app.uiManager.elements.copyCredentialsBtn.addEventListener('click', () => {
            this.app.copyCredentials();
        });

        this.app.uiManager.elements.refreshCredentialsBtn.addEventListener('click', () => {
            this.app.generateCredentials();
            this.app.uiManager.showToast('New credentials generated');
        });

        this.app.uiManager.elements.connectBtn.addEventListener('click', () => {
            if (this.app.state.isConnected) {
                this.app.uiManager.elements.disconnectModal.style.display = 'flex';
            } else {
                this.app.connectToPartner();
            }
        });

        this.app.uiManager.elements.fullscreenBtn.addEventListener('click', () => {
            this.toggleFullscreen();
        });

        this.app.uiManager.elements.disconnectBtn.addEventListener('click', () => {
            this.app.uiManager.elements.disconnectModal.style.display = 'flex';
        });
    }

    setupConsentEvents() {
        this.app.uiManager.elements.understandRisks.addEventListener('change', (e) => {
            this.app.uiManager.elements.acceptConsent.disabled = !e.target.checked;
        });

        this.app.uiManager.elements.acceptConsent.addEventListener('click', () => {
            this.app.uiManager.elements.consentModal.style.display = 'none';
            // Additional consent handling if needed
        });

        this.app.uiManager.elements.declineConsent.addEventListener('click', () => {
            this.app.uiManager.elements.consentModal.style.display = 'none';
            // Handle declined consent
        });
    }

    setupModalEvents() {
        this.app.uiManager.elements.confirmDisconnect.addEventListener('click', () => {
            this.app.uiManager.elements.disconnectModal.style.display = 'none';
            this.app.disconnect();
        });

        this.app.uiManager.elements.cancelDisconnect.addEventListener('click', () => {
            this.app.uiManager.elements.disconnectModal.style.display = 'none';
        });

        this.app.uiManager.elements.closeErrorBtn.addEventListener('click', () => {
            this.app.uiManager.elements.errorModal.style.display = 'none';
        });
    }

    setupPermissionEvents() {
        this.app.uiManager.elements.permissionMouse.addEventListener('change', (e) => {
            this.app.togglePermission('mouse', e.target.checked);
        });

        this.app.uiManager.elements.permissionKeyboard.addEventListener('change', (e) => {
            this.app.togglePermission('keyboard', e.target.checked);
        });

        this.app.uiManager.elements.permissionClipboard.addEventListener('change', (e) => {
            this.app.togglePermission('clipboard', e.target.checked);
        });
    }

    toggleFullscreen() {
        if (!document.fullscreenElement) {
            this.app.uiManager.elements.remoteScreenContainer.requestFullscreen().catch(err => {
                console.error('Error attempting to enable fullscreen:', err);
            });
        } else {
            document.exitFullscreen();
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const app = new SecureRemoteControl();
});
