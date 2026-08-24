// SafeFruit AI Frontend Logic

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const elements = {
        date: document.getElementById('current-date'),
        time: document.getElementById('current-time'),
        startBtn: document.getElementById('start-btn'),
        stopBtn: document.getElementById('stop-btn'),
        sysStatus: document.getElementById('system-status'),
        sysStatusText: document.getElementById('status-text-val'),
        camStatus: document.getElementById('camera-status'),
        ardStatus: document.getElementById('arduino-status'),
        apiStatus: document.getElementById('api-status'),
        stageText: document.getElementById('stage-text'),
        currentOperation: document.getElementById('current-operation'),
        
        // Sensors
        mq135: document.getElementById('val-mq135'),
        ph: document.getElementById('val-ph'),
        conveyor: document.getElementById('val-conveyor'),
        washing: document.getElementById('val-washing'),
        uv: document.getElementById('val-uv'),
        distance: document.getElementById('val-distance'),
        stage1Door: document.getElementById('val-stage1-door'),
        stage3Door: document.getElementById('val-stage3-door'),
        
        // Results
        resultFruit: document.getElementById('result-fruit'),
        resultStatus: document.getElementById('result-status'),
        resultDefects: document.getElementById('result-defects'),
        resultReason: document.getElementById('result-reason'),
        confidenceFill: document.getElementById('confidence-fill'),
        confidenceText: document.getElementById('result-confidence'),
        resultBox: document.getElementById('result-status-box'),
        
        // Modals
        settingsModal: document.getElementById('settings-modal'),
        saveSettingsBtn: document.getElementById('save-settings-btn'),
        chatModal: document.getElementById('chat-modal'),
        chatMessages: document.getElementById('chat-messages'),
        chatInput: document.getElementById('chat-input-text'),
        sendChatBtn: document.getElementById('send-chat-btn'),
    };

    // Update Date/Time
    function updateDateTime() {
        const now = new Date();
        elements.date.textContent = now.toLocaleDateString();
        elements.time.textContent = now.toLocaleTimeString();
    }
    setInterval(updateDateTime, 1000);
    updateDateTime();

    // Lazy load the video stream so the browser tab finishes its "Loading" state
    setTimeout(() => {
        const videoFeed = document.getElementById('video-feed');
        if (videoFeed && videoFeed.dataset.src) {
            videoFeed.src = videoFeed.dataset.src;
        }
    }, 500);

    // Fetch Telemetry Data
    async function fetchTelemetry() {
        try {
            const response = await fetch('/api/telemetry');
            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();
            
            // Update Hardware Status
            updateStatusTag(elements.camStatus, data.camera_connected, 'Camera Connected', 'Camera Error');
            updateStatusTag(elements.ardStatus, data.arduino_connected, 'Arduino Connected', 'Arduino Error');
            updateStatusTag(elements.apiStatus, data.api_valid, 'API Valid', 'API Invalid');
            
            // Update Sensors
            elements.mq135.textContent = data.sensors.mq135;
            elements.ph.textContent = data.sensors.ph;
            elements.conveyor.textContent = data.sensors.conveyor;
            elements.washing.textContent = data.sensors.washing;
            elements.uv.textContent = data.sensors.uv;
            if (elements.distance) elements.distance.textContent = data.sensors.distance || '--';
            if (elements.stage1Door) elements.stage1Door.textContent = data.sensors.stage1_door || '--';
            if (elements.stage3Door) elements.stage3Door.textContent = data.sensors.stage3_door || '--';
            
            // Update Process State
            elements.stageText.textContent = data.state.stage;
            elements.currentOperation.textContent = data.state.operation;
            
            // Update Results
            if (data.state.result) {
                elements.resultFruit.textContent = data.state.result.fruit || '--';
                elements.resultStatus.textContent = data.state.result.status || '--';
                elements.resultDefects.textContent = data.state.result.defects || 'None';
                elements.resultReason.textContent = data.state.result.reason || '--';
                
                const confidence = data.state.result.confidence || 0;
                elements.confidenceFill.style.width = `${confidence}%`;
                elements.confidenceText.textContent = confidence;
                
                // Color code the result box
                if (data.state.result.status === 'SAFE TO EAT' || data.state.result.status === 'PASS') {
                    elements.resultBox.style.borderColor = 'var(--success)';
                    elements.resultBox.style.boxShadow = '0 0 20px rgba(16, 185, 129, 0.1)';
                } else if (data.state.result.status === 'NOT SAFE TO EAT' || data.state.result.status === 'FAIL') {
                    elements.resultBox.style.borderColor = 'var(--danger)';
                    elements.resultBox.style.boxShadow = '0 0 20px rgba(239, 68, 68, 0.1)';
                } else {
                    elements.resultBox.style.borderColor = 'var(--panel-border)';
                    elements.resultBox.style.boxShadow = 'none';
                }
            }
            
            if (typeof renderLogs === 'function') {
                renderLogs(data.logs);
            }
            
            // Overall Status
            if (data.state.is_running) {
                elements.sysStatusText.textContent = 'INSPECTING';
                elements.sysStatus.style.color = 'var(--warning)';
                elements.sysStatus.style.borderColor = 'rgba(245, 158, 11, 0.2)';
                elements.sysStatus.style.backgroundColor = 'rgba(245, 158, 11, 0.1)';
                elements.sysStatus.querySelector('.status-indicator').style.backgroundColor = 'var(--warning)';
                elements.sysStatus.querySelector('.status-indicator').style.boxShadow = '0 0 10px var(--warning)';
                elements.startBtn.disabled = true;
            } else {
                elements.sysStatusText.textContent = 'READY';
                elements.sysStatus.style.color = 'var(--success)';
                elements.sysStatus.style.borderColor = 'rgba(16, 185, 129, 0.2)';
                elements.sysStatus.style.backgroundColor = 'rgba(16, 185, 129, 0.1)';
                elements.sysStatus.querySelector('.status-indicator').style.backgroundColor = 'var(--success)';
                elements.sysStatus.querySelector('.status-indicator').style.boxShadow = '0 0 10px var(--success)';
                elements.startBtn.disabled = false;
            }

        } catch (error) {
            console.error("Telemetry fetch error:", error);
            elements.sysStatusText.textContent = 'DISCONNECTED';
            elements.sysStatus.style.color = 'var(--danger)';
            elements.sysStatus.querySelector('.status-indicator').style.backgroundColor = 'var(--danger)';
            elements.sysStatus.querySelector('.status-indicator').style.boxShadow = '0 0 10px var(--danger)';
        }
    }
    
    function updateStatusTag(element, isOk, okText, errText) {
        element.textContent = isOk ? okText : errText;
        element.className = `status-tag ${isOk ? 'success' : 'danger'}`;
    }

    // Start polling every second
    setInterval(fetchTelemetry, 1000);

    // Button Listeners
    elements.startBtn.addEventListener('click', async () => {
        try {
            await fetch('/api/start', { method: 'POST' });
        } catch (e) {
            alert('Failed to start inspection: ' + e);
        }
    });

    elements.stopBtn.addEventListener('click', async () => {
        try {
            await fetch('/api/stop', { method: 'POST' });
        } catch (e) {
            console.error(e);
        }
    });

    // New Log Box and Test Buttons
    const logBox = document.getElementById('system-log-box');
    let lastLogCount = 0;

    // Attach to global window so it can be called from fetchTelemetry
    window.renderLogs = function(logs) {
        if (!logs || logs.length === 0) return;
        if (logs.length !== lastLogCount || logs[logs.length-1] !== window.lastLogMsg) {
            logBox.innerHTML = '';
            logs.forEach(msg => {
                const div = document.createElement('div');
                div.className = 'log-entry';
                div.textContent = msg;
                logBox.appendChild(div);
            });
            logBox.scrollTop = logBox.scrollHeight;
            lastLogCount = logs.length;
            window.lastLogMsg = logs[logs.length-1];
        }
    };

    document.getElementById('test-cam-btn').addEventListener('click', async (e) => {
        e.target.textContent = 'Testing...';
        await fetch('/api/test/camera', {method: 'POST'});
        e.target.textContent = 'Test Camera';
    });

    document.getElementById('test-ard-btn').addEventListener('click', async (e) => {
        e.target.textContent = 'Testing...';
        await fetch('/api/test/arduino', {method: 'POST'});
        e.target.textContent = 'Test Arduino';
    });

    document.getElementById('test-api-btn').addEventListener('click', async (e) => {
        e.target.textContent = 'Testing...';
        try {
            const res = await fetch('/api/test/api', {method: 'POST'});
            const data = await res.json();
            document.getElementById('settings-msg').textContent = data.message;
            document.getElementById('settings-msg').style.color = data.success ? '#4ADE80' : '#EF4444';
        } catch(err) {
            document.getElementById('settings-msg').textContent = 'Network Error';
            document.getElementById('settings-msg').style.color = '#EF4444';
        }
        e.target.textContent = 'Test API';
    });

    // Modals
    document.getElementById('tab-settings').addEventListener('click', async () => {
        const res = await fetch('/api/config');
        const cfg = await res.json();
        document.getElementById('input-camera-index').value = cfg.camera_index || 0;
        document.getElementById('input-com-port').value = cfg.com_port || '';
        document.getElementById('input-api-key').value = cfg.api_key || '';
        document.getElementById('settings-msg').textContent = '';
        elements.settingsModal.classList.remove('hidden');
    });

    elements.saveSettingsBtn.addEventListener('click', async () => {
        const payload = {
            camera_index: parseInt(document.getElementById('input-camera-index').value, 10),
            com_port: document.getElementById('input-com-port').value,
            api_key: document.getElementById('input-api-key').value
        };
        try {
            await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            document.getElementById('settings-msg').textContent = '✅ Settings saved successfully';
        } catch(e) {
            document.getElementById('settings-msg').textContent = '❌ Failed to save settings';
        }
    });

    // Show Chat Modal
    document.getElementById('tab-chat').addEventListener('click', () => {
        elements.chatModal.classList.remove('hidden');
    });

    // Send Chat Message Function
    async function sendChatMessage() {
        const text = elements.chatInput.value.trim();
        if (!text) return;

        // Append User bubble
        appendChatBubble(text, 'user');
        elements.chatInput.value = '';

        // Temporary Loading bubble
        const loadingId = 'loading-' + Date.now();
        appendChatBubble('Thinking...', 'ai', loadingId);

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await response.json();
            
            // Remove loading
            const loadingBubble = document.getElementById(loadingId);
            if (loadingBubble) loadingBubble.remove();

            if (data.success) {
                appendChatBubble(data.reply, 'ai');
            } else {
                appendChatBubble('Error: ' + data.error, 'error');
            }
        } catch (err) {
            const loadingBubble = document.getElementById(loadingId);
            if (loadingBubble) loadingBubble.remove();
            appendChatBubble('Failed to communicate with API: ' + err, 'error');
        }
    }

    function appendChatBubble(text, type, id = null) {
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${type}`;
        if (id) bubble.id = id;
        bubble.textContent = text;
        elements.chatMessages.appendChild(bubble);
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    }

    // Attach listeners
    elements.sendChatBtn.addEventListener('click', sendChatMessage);
    elements.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            sendChatMessage();
        }
    });
});
