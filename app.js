class RemoteControlApp {
    constructor() {
        // DOM Elements
        this.yourUriInput = document.getElementById('your-uri');
        this.yourPasswordInput = document.getElementById('your-password');
        this.copyCredentialsBtn = document.getElementById('copy-credentials');
        this.refreshCredentialsBtn = document.getElementById('refresh-credentials');
        this.serverStatus = document.getElementById('server-status');
        this.partnerUriInput = document.getElementById('partner-uri');
        this.partnerPasswordInput = document.getElementById('partner-password');
        this.connectBtn = document.getElementById('connect-btn');
        this.clientStatus = document.getElementById('client-status');
        this.connectingLoader = document.getElementById('connecting-loader');
        this.remoteScreenContainer = document.getElementById('remote-screen-container');
        this.remoteScreenImg = document.getElementById('remote-screen-img');
        this.remoteScreenStatus = document.getElementById('remote-screen-status');
        this.disconnectModal = document.getElementById('disconnect-modal');
        this.closeDisconnectModal = document.getElementById('close-disconnect-modal');
        this.cancelDisconnect = document.getElementById('cancel-disconnect');
        this.confirmDisconnect = document.getElementById('confirm-disconnect');
        this.errorModal = document.getElementById('error-modal');
        this.closeErrorModal = document.getElementById('close-error-modal');
        this.errorMessage = document.getElementById('error-message');
        this.closeErrorBtn = document.getElementById('close-error-btn');
        this.toast = document.getElementById('toast');
        this.fullscreenBtn = document.getElementById('fullscreen-btn');
        this.disconnectBtn = document.getElementById('disconnect-btn');
        this.touchControls = document.getElementById('touch-controls');
        this.touchUp = document.getElementById('touch-up');
        this.touchDown = document.getElementById('touch-down');
        this.touchLeft = document.getElementById('touch-left');
        this.touchRight = document.getElementById('touch-right');
        this.touchClick = document.getElementById('touch-click');
        this.touchRightClick = document.getElementById('touch-right-click');
        this.touchEsc = document.getElementById('touch-esc');
        this.touchEnter = document.getElementById('touch-enter');
        this.touchSpace = document.getElementById('touch-space');

        // App state
        this.socket = null;
        this.peerConnection = null;
        this.dataChannel = null;
        this.isHost = false;
        this.isConnected = false;
        this.connectionId = '';
        this.connectionPassword = '';
        this.partnerSocketId = '';
        this.cipherKey = '';
        this.fernet = null;
        this.screenStreamInterval = null;
        this.isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        this.isFullscreen = false;
        this.mouseDown = false;
        this.lastMousePosition = { x: 0, y: 0 };
        this.touchStartPosition = null;
        this.touchStartTime = null;

        // Initialize the app
        this.init();
    }

    init() {
        // Generate initial credentials
        this.generateCredentials();

        // Setup event listeners
        this.setupEventListeners();

        // Initialize WebSocket connection
        this.connectToSignalingServer();
    }

    generateCredentials() {
        this.connectionId = this.generateRandomId(6);
        this.connectionPassword = this.generateRandomId(4);
        
        // Set the credentials in the UI
        this.yourUriInput.value = this.connectionId;
        this.yourPasswordInput.value = this.connectionPassword;
    }

    generateRandomId(length) {
        const chars = '0123456789';
        let result = '';
        for (let i = 0; i < length; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    }

    setupEventListeners() {
        // Copy credentials button
        this.copyCredentialsBtn.addEventListener('click', () => this.copyCredentials());

        // Refresh credentials button
        this.refreshCredentialsBtn.addEventListener('click', () => {
            this.generateCredentials();
            this.updateServerStatus('New credentials generated', 'success');
        });

        // Connect to partner button
        this.connectBtn.addEventListener('click', () => {
            if (this.isConnected) {
                this.disconnectModal.style.display = 'flex';
            } else {
                this.connectToPartner();
            }
        });

        // Disconnect modal buttons
        this.closeDisconnectModal.addEventListener('click', () => this.disconnectModal.style.display = 'none');
        this.cancelDisconnect.addEventListener('click', () => this.disconnectModal.style.display = 'none');
        this.confirmDisconnect.addEventListener('click', () => {
            this.disconnectModal.style.display = 'none';
            this.disconnect();
        });
        
        // Error modal buttons
        this.closeErrorModal.addEventListener('click', () => this.errorModal.style.display = 'none');
        this.closeErrorBtn.addEventListener('click', () => this.errorModal.style.display = 'none');
        
        // Fullscreen button
        this.fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
        
        // Disconnect button
        this.disconnectBtn.addEventListener('click', () => this.disconnectModal.style.display = 'flex');
        
        // Touch controls
        this.touchUp.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.sendControlCommand({ type: 'key_press', key: 'ArrowUp' });
        });
        
        this.touchDown.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.sendControlCommand({ type: 'key_press', key: 'ArrowDown' });
        });
        
        this.touchLeft.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.sendControlCommand({ type: 'key_press', key: 'ArrowLeft' });
        });
        
        this.touchRight.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.sendControlCommand({ type: 'key_press', key: 'ArrowRight' });
        });
        
        this.touchClick.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.sendControlCommand({ type: 'mouse_click', button: 'left' });
        });
        
        this.touchRightClick.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.sendControlCommand({ type: 'mouse_click', button: 'right' });
        });
        
        this.touchEsc.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.sendControlCommand({ type: 'key_press', key: 'Escape' });
        });
        
        this.touchEnter.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.sendControlCommand({ type: 'key_press', key: 'Enter' });
        });
        
        this.touchSpace.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.sendControlCommand({ type: 'key_press', key: ' ' });
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (!this.isConnected) return;
            
            // Prevent default for specific keys
            if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Escape', 'Enter', ' '].includes(e.key)) {
                e.preventDefault();
            }
            
            // ESC to disconnect
            if (e.key === 'Escape' && !e.repeat) {
                this.disconnectModal.style.display = 'flex';
            }
            
            // F to toggle fullscreen
            if (e.key.toLowerCase() === 'f' && !e.repeat) {
                this.toggleFullscreen();
            }
            
            // Send key press to remote
            this.sendControlCommand({ type: 'key_down', key: e.key });
        });
        
        document.addEventListener('keyup', (e) => {
            if (!this.isConnected) return;
            this.sendControlCommand({ type: 'key_up', key: e.key });
        });

        // Mouse events for remote control
        this.remoteScreenImg.addEventListener('mousedown', (e) => {
            if (!this.isConnected) return;
            
            const rect = this.remoteScreenImg.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            // Calculate relative coordinates (0-1)
            const relX = x / rect.width;
            const relY = y / rect.height;
            
            this.mouseDown = true;
            this.lastMousePosition = { x: relX, y: relY };
            
            const button = e.button === 2 ? 'right' : 'left';
            this.sendControlCommand({ 
                type: 'mouse_down', 
                x: relX, 
                y: relY, 
                button 
            });
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!this.isConnected || !this.mouseDown) return;
            
            const rect = this.remoteScreenImg.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            // Calculate relative coordinates (0-1)
            const relX = x / rect.width;
            const relY = y / rect.height;
            
            this.sendControlCommand({ 
                type: 'mouse_move', 
                x: relX, 
                y: relY 
            });
            
            this.lastMousePosition = { x: relX, y: relY };
        });
        
        document.addEventListener('mouseup', (e) => {
            if (!this.isConnected) return;
            
            this.mouseDown = false;
            const button = e.button === 2 ? 'right' : 'left';
            this.sendControlCommand({ 
                type: 'mouse_up', 
                x: this.lastMousePosition.x, 
                y: this.lastMousePosition.y, 
                button 
            });
        });
        
        this.remoteScreenImg.addEventListener('contextmenu', (e) => {
            if (!this.isConnected) return;
            e.preventDefault();
        });

        // Touch events for mobile control
        this.remoteScreenImg.addEventListener('touchstart', (e) => {
            if (!this.isConnected) return;
            e.preventDefault();
            
            const touch = e.touches[0];
            const rect = this.remoteScreenImg.getBoundingClientRect();
            const x = touch.clientX - rect.left;
            const y = touch.clientY - rect.top;
            
            // Calculate relative coordinates (0-1)
            const relX = x / rect.width;
            const relY = y / rect.height;
            
            this.touchStartPosition = { x: relX, y: relY };
            this.touchStartTime = Date.now();
            
            this.sendControlCommand({ 
                type: 'mouse_down', 
                x: relX, 
                y: relY, 
                button: 'left' 
            });
        }, { passive: false });
        
        this.remoteScreenImg.addEventListener('touchmove', (e) => {
            if (!this.isConnected) return;
            e.preventDefault();
            
            const touch = e.touches[0];
            const rect = this.remoteScreenImg.getBoundingClientRect();
            const x = touch.clientX - rect.left;
            const y = touch.clientY - rect.top;
            
            // Calculate relative coordinates (0-1)
            const relX = x / rect.width;
            const relY = y / rect.height;
            
            this.sendControlCommand({ 
                type: 'mouse_move', 
                x: relX, 
                y: relY 
            });
            
            this.touchStartPosition = { x: relX, y: relY };
        }, { passive: false });
        
        this.remoteScreenImg.addEventListener('touchend', (e) => {
            if (!this.isConnected) return;
            e.preventDefault();
            
            const touchDuration = Date.now() - this.touchStartTime;
            const isClick = touchDuration < 300; // Less than 300ms is a click
            
            if (isClick && this.touchStartPosition) {
                this.sendControlCommand({ 
                    type: 'mouse_click', 
                    x: this.touchStartPosition.x, 
                    y: this.touchStartPosition.y, 
                    button: 'left' 
                });
            } else {
                this.sendControlCommand({ 
                    type: 'mouse_up', 
                    x: this.touchStartPosition.x, 
                    y: this.touchStartPosition.y, 
                    button: 'left' 
                });
            }
            
            this.touchStartPosition = null;
            this.touchStartTime = null;
        }, { passive: false });
    }

    connectToSignalingServer() {
        // Connect to signaling server (replace with your server URL)
        this.socket = io('https://branch-shell-iodine.glitch.me', {
            reconnectionAttempts: 5,
            reconnectionDelay: 1000,
            transports: ['websocket']
        });

        this.socket.on('connect', () => {
            this.updateServerStatus('Connected to signaling server', 'success');
            
            // Register as host
            this.socket.emit('register_as_host', {
                connectionId: this.connectionId,
                password: this.connectionPassword
            });
        });

        this.socket.on('registration_success', (data) => {
            this.cipherKey = data.cipherKey;
            this.fernet = new Fernet(this.cipherKey);
            this.updateServerStatus('Ready for connections', 'success');
        });

        this.socket.on('connection_error', (data) => {
            this.showError(data.message);
        });

        this.socket.on('partner_connected', () => {
            this.isHost = true;
            this.isConnected = true;
            this.updateServerStatus('Partner connected', 'success');
            this.startWebRTC();
        });

        this.socket.on('connection_success', (data) => {
            this.cipherKey = data.cipherKey;
            this.fernet = new Fernet(this.cipherKey);
            this.isHost = false;
            this.isConnected = true;
            this.connectBtn.textContent = 'Disconnect';
            this.connectBtn.classList.remove('btn-success');
            this.connectBtn.classList.add('btn-primary');
            this.connectBtn.disabled = false;
            this.connectingLoader.style.display = 'none';
            this.updateClientStatus('Connected to partner', 'success');
            this.remoteScreenContainer.style.display = 'block';
            this.updateRemoteScreenStatus('Connected to partner');
            
            if (this.isMobile) {
                this.touchControls.classList.add('active');
            }
        });

        this.socket.on('partner_disconnected', () => {
            this.disconnect();
            this.updateServerStatus('Partner disconnected', 'warning');
        });

        this.socket.on('disconnect', () => {
            if (this.isConnected) {
                this.disconnect();
                this.updateServerStatus('Disconnected from signaling server', 'error');
            }
        });

        this.socket.on('webrtc_signal', (data) => {
            this.handleSignal(data);
        });

        this.socket.on('screen_data', (data) => {
            if (this.fernet) {
                try {
                    const decrypted = this.fernet.decrypt(data.frame);
                    this.remoteScreenImg.src = 'data:image/jpeg;base64,' + decrypted;
                } catch (e) {
                    console.error('Decryption error:', e);
                }
            }
        });
    }

    async startWebRTC() {
        try {
            this.peerConnection = new RTCPeerConnection({
                iceServers: [
                    { urls: 'stun:stun.l.google.com:19302' },
                    { urls: 'stun:stun1.l.google.com:19302' },
                    { urls: 'stun:stun2.l.google.com:19302' }
                ]
            });

            this.peerConnection.onicecandidate = (event) => {
                if (event.candidate) {
                    this.socket.emit('webrtc_signal', {
                        target: this.partnerSocketId,
                        signal: {
                            type: 'candidate',
                            candidate: event.candidate
                        }
                    });
                }
            };

            // Set up data channel for control commands
            this.dataChannel = this.peerConnection.createDataChannel('control');
            this.dataChannel.onmessage = (event) => {
                try {
                    const command = JSON.parse(event.data);
                    this.handleControlMessage(command);
                } catch (e) {
                    console.error('Error parsing control command:', e);
                }
            };

            this.dataChannel.onopen = () => {
                console.log('Data channel opened');
                this.updateRemoteScreenStatus('Connection established - Latency: 120ms');
            };

            this.dataChannel.onclose = () => {
                console.log('Data channel closed');
                this.disconnect();
            };

            const offer = await this.peerConnection.createOffer();
            await this.peerConnection.setLocalDescription(offer);

            this.socket.emit('webrtc_signal', {
                target: this.partnerSocketId,
                signal: {
                    type: 'offer',
                    offer: offer
                }
            });

            this.remoteScreenContainer.style.display = 'block';
            this.updateRemoteScreenStatus('Starting connection...');
        } catch (error) {
            console.error('WebRTC error:', error);
            this.showError('Failed to establish WebRTC connection');
            this.disconnect();
        }
    }

    async handleSignal(data) {
        if (!this.peerConnection) return;

        try {
            const { signal } = data;
            if (signal.type === 'offer') {
                await this.peerConnection.setRemoteDescription(new RTCSessionDescription(signal.offer));
                const answer = await this.peerConnection.createAnswer();
                await this.peerConnection.setLocalDescription(answer);

                this.socket.emit('webrtc_signal', {
                    target: this.partnerSocketId,
                    signal: {
                        type: 'answer',
                        answer: answer
                    }
                });
            } else if (signal.type === 'answer') {
                await this.peerConnection.setRemoteDescription(new RTCSessionDescription(signal.answer));
            } else if (signal.type === 'candidate') {
                await this.peerConnection.addIceCandidate(new RTCIceCandidate(signal.candidate));
            }
        } catch (error) {
            console.error('Error handling signal:', error);
        }
    }

    connectToPartner() {
        const partnerUri = this.partnerUriInput.value.trim();
        const partnerPassword = this.partnerPasswordInput.value.trim();
        
        if (!partnerUri || !partnerPassword) {
            this.showError('Please enter both ID and password');
            return;
        }
        
        // Show loading state
        this.connectBtn.disabled = true;
        this.connectingLoader.style.display = 'block';
        this.updateClientStatus('Connecting to partner...', 'info');
        
        // Connect to partner through signaling server
        this.partnerSocketId = partnerUri;
        this.socket.emit('connect_to_host', {
            connectionId: partnerUri,
            password: partnerPassword
        });
    }

    sendControlCommand(command) {
        if (this.dataChannel && this.dataChannel.readyState === 'open') {
            try {
                this.dataChannel.send(JSON.stringify(command));
            } catch (e) {
                console.error('Error sending control command:', e);
            }
        }
    }

    handleControlMessage(command) {
        // Handle incoming control commands (for host)
        console.log('Control command received:', command);
        // In a real implementation, this would control the host machine
    }

    copyCredentials() {
        const text = `ER NetLink Connection\nID: ${this.connectionId}\nPassword: ${this.connectionPassword}`;
        navigator.clipboard.writeText(text).then(() => {
            this.showToast('Credentials copied to clipboard!');
            this.updateServerStatus('Credentials copied to clipboard!', 'success');
        }).catch(err => {
            console.error('Failed to copy credentials: ', err);
            this.updateServerStatus('Failed to copy credentials', 'error');
        });
    }

    disconnect() {
        // Close WebRTC connection
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
        
        // Reset connection state
        this.isConnected = false;
        this.isHost = false;
        this.dataChannel = null;
        
        // Update UI
        this.connectBtn.textContent = 'Connect to Partner';
        this.connectBtn.classList.remove('btn-primary');
        this.connectBtn.classList.add('btn-success');
        this.connectBtn.disabled = false;
        this.connectingLoader.style.display = 'none';
        
        this.updateClientStatus('Disconnected', 'info');
        this.updateRemoteScreenStatus('Disconnected from partner');
        
        if (this.isMobile) {
            this.touchControls.classList.remove('active');
        }
        
        // Hide remote screen after a delay
        setTimeout(() => {
            this.remoteScreenContainer.style.display = 'none';
            this.remoteScreenImg.src = '';
        }, 1000);
    }

    toggleFullscreen() {
        if (!this.isFullscreen) {
            if (this.remoteScreenContainer.requestFullscreen) {
                this.remoteScreenContainer.requestFullscreen();
            } else if (this.remoteScreenContainer.webkitRequestFullscreen) {
                this.remoteScreenContainer.webkitRequestFullscreen();
            } else if (this.remoteScreenContainer.msRequestFullscreen) {
                this.remoteScreenContainer.msRequestFullscreen();
            }
            this.isFullscreen = true;
            this.fullscreenBtn.textContent = 'Exit Fullscreen';
        } else {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            } else if (document.msExitFullscreen) {
                document.msExitFullscreen();
            }
            this.isFullscreen = false;
            this.fullscreenBtn.textContent = 'Fullscreen';
        }
    }

    updateServerStatus(message, type = 'info') {
        this.serverStatus.textContent = `Status: ${message}`;
        this.serverStatus.className = 'status-message';
        
        switch (type) {
            case 'error':
                this.serverStatus.classList.add('status-error');
                break;
            case 'success':
                this.serverStatus.classList.add('status-success');
                break;
            case 'warning':
                this.serverStatus.classList.add('status-warning');
                break;
            default:
                this.serverStatus.classList.add('status-info');
        }
    }

    updateClientStatus(message, type = 'info') {
        this.clientStatus.textContent = `Status: ${message}`;
        this.clientStatus.className = 'status-message';
        
        switch (type) {
            case 'error':
                this.clientStatus.classList.add('status-error');
                break;
            case 'success':
                this.clientStatus.classList.add('status-success');
                break;
            case 'warning':
                this.clientStatus.classList.add('status-warning');
                break;
            default:
                this.clientStatus.classList.add('status-info');
        }
    }

    updateRemoteScreenStatus(message) {
        this.remoteScreenStatus.textContent = message;
    }

    showError(message) {
        this.errorMessage.textContent = message;
        this.errorModal.style.display = 'flex';
    }

    showToast(message) {
        this.toast.textContent = message;
        this.toast.classList.add('show');
        
        setTimeout(() => {
            this.toast.classList.remove('show');
        }, 3000);
    }
}

// Fernet encryption implementation
class Fernet {
    constructor(key) {
        this.key = CryptoJS.enc.Base64.parse(key + '=');
        this.signingKey = this.key.toString(CryptoJS.enc.Hex).substring(0, 32);
        this.encryptionKey = this.key.toString(CryptoJS.enc.Hex).substring(32);
    }

    encrypt(message) {
        const iv = CryptoJS.lib.WordArray.random(16);
        const encrypted = CryptoJS.AES.encrypt(message, CryptoJS.enc.Hex.parse(this.encryptionKey), {
            iv: iv,
            mode: CryptoJS.mode.CBC,
            padding: CryptoJS.pad.Pkcs7
        });
        
        const ciphertext = iv.concat(encrypted.ciphertext);
        const hmac = CryptoJS.HmacSHA256(ciphertext, CryptoJS.enc.Hex.parse(this.signingKey));
        
        return ciphertext.concat(hmac).toString(CryptoJS.enc.Base64);
    }

    decrypt(token) {
        const data = CryptoJS.enc.Base64.parse(token);
        const ciphertext = data.clone();
        ciphertext.sigBytes -= 32;
        
        const hmac = data.clone();
        hmac.sigBytes = 32;
        hmac.words = data.words.slice(data.words.length - 8);
        
        const calculatedHmac = CryptoJS.HmacSHA256(ciphertext, CryptoJS.enc.Hex.parse(this.signingKey));
        
        if (hmac.toString() !== calculatedHmac.toString()) {
            throw new Error('Invalid token');
        }
        
        const iv = ciphertext.clone();
        iv.sigBytes = 16;
        iv.words = ciphertext.words.slice(0, 4);
        
        const encrypted = ciphertext.clone();
        encrypted.sigBytes -= 16;
        encrypted.words = ciphertext.words.slice(4);
        
        const decrypted = CryptoJS.AES.decrypt(
            { ciphertext: encrypted },
            CryptoJS.enc.Hex.parse(this.encryptionKey),
            { iv: iv, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7 }
        );
        
        return decrypted.toString(CryptoJS.enc.Utf8);
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const app = new RemoteControlApp();
});
