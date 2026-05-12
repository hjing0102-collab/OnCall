// SuperOnCallAgent - Frontend App
const API_BASE = '';

let currentSessionId = null;
let currentMode = 'quick';
let isProcessing = false;

const STORE_KEY = 'oncall_chat_sessions';
let sessions = new Map();

function generateSessionId() {
    return 's' + Date.now() + '-' + Math.random().toString(36).substr(2, 6);
}

function saveSessionsToStorage() {
    const data = [];
    sessions.forEach((s, id) => data.push({ id, name: s.name, messages: s.messages }));
    localStorage.setItem(STORE_KEY, JSON.stringify(data));
}

function loadSessionsFromStorage() {
    try {
        const raw = localStorage.getItem(STORE_KEY);
        if (!raw) return;
        JSON.parse(raw).forEach(s => sessions.set(s.id, { name: s.name, messages: s.messages || [] }));
    } catch (e) { console.error('加载会话失败', e); }
}

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const newChatBtn = document.getElementById('newChatBtn');
const modeSelectorBtn = document.getElementById('modeSelectorBtn');
const currentModeText = document.getElementById('currentModeText');
const modeDropdown = document.getElementById('modeDropdown');
const toolsBtn = document.getElementById('toolsBtn');
const toolsMenu = document.getElementById('toolsMenu');
const uploadFileItem = document.getElementById('uploadFileItem');
const fileInput = document.getElementById('fileInput');
const aiOpsBtn = document.getElementById('aiOpsSidebarBtn');
const vectorDbBtn = document.getElementById('vectorDbBtn');
const vectorDbModal = document.getElementById('vectorDbModal');
const vectorDbContent = document.getElementById('vectorDbContent');
const closeModalBtn = document.getElementById('closeModalBtn');
const welcomeGreeting = document.getElementById('welcomeGreeting');
const chatHistoryList = document.getElementById('chatHistoryList');
const alertBanner = document.getElementById('alertBanner');
const alertText = document.getElementById('alertText');
const alertClose = document.getElementById('alertClose');
const cpuStatus = document.getElementById('cpuStatus');
const memStatus = document.getElementById('memStatus');
const diskStatus = document.getElementById('diskStatus');
const procCount = document.getElementById('procCount');

// ==================== 系统监控 ====================

let alertQueue = [];
let activeAlert = null;

function updateStatusDot(el, value, warningThreshold, dangerThreshold) {
    const dot = el.querySelector('.status-dot');
    const val = el.querySelector('.status-val');
    if (val) val.textContent = value;
    if (dot) {
        dot.classList.remove('warning', 'danger');
        if (value >= dangerThreshold) dot.classList.add('danger');
        else if (value >= warningThreshold) dot.classList.add('warning');
    }
}

async function fetchSystemStatus() {
    try {
        const r = await fetch(`${API_BASE}/api/monitor/now`);
        const d = await r.json();
        if (d.code !== 200) return;
        const m = d.data.metrics;
        updateStatusDot(cpuStatus, m.cpu, 50, 80);
        updateStatusDot(memStatus, m.memory, 60, 85);
        updateStatusDot(diskStatus, m.disk, 70, 90);
        const pc = procCount.querySelector('.status-val');
        if (pc) pc.textContent = m.process_count;
    } catch (e) { /* ignore poll errors */ }
}

function showAlert(alert) {
    alertBanner.className = 'alert-banner ' + (alert.level || 'warning');
    alertText.textContent = alert.message;
    alertBanner.style.display = 'flex';
}

function hideAlert() {
    alertBanner.style.display = 'none';
    activeAlert = null;
}

alertClose.addEventListener('click', hideAlert);

function connectMonitorStream() {
    const evtSource = new EventSource(`${API_BASE}/api/monitor/stream`);
    evtSource.onmessage = function(event) {
        try {
            const alert = JSON.parse(event.data);
            if (alert.type === 'error') return;
            showAlert(alert);
            // Auto-hide after 30 seconds
            clearTimeout(window._alertTimeout);
            window._alertTimeout = setTimeout(hideAlert, 30000);
        } catch (e) {}
    };
    evtSource.onerror = function() {
        // Reconnect after 5s
        setTimeout(connectMonitorStream, 5000);
    };
}

// ==================== 初始化 ====================
marked.setOptions({ breaks: true, gfm: true });

// Start system monitoring
fetchSystemStatus();
setInterval(fetchSystemStatus, 5000);
connectMonitorStream();

loadSessionsFromStorage();
if (sessions.size > 0) {
    const lastId = localStorage.getItem('oncall_last_session');
    currentSessionId = (lastId && sessions.has(lastId)) ? lastId : Array.from(sessions.keys())[0];
    renderSessionMessages(currentSessionId);
} else {
    currentSessionId = generateSessionId();
    sessions.set(currentSessionId, { name: '新对话', messages: [] });
    welcomeGreeting.style.display = 'block';
}
renderSidebar();

// ==================== 会话函数 ====================

function saveCurrentSessionMessages() {
    const msgs = [];
    chatMessages.querySelectorAll('.message').forEach(el => {
        const role = el.classList.contains('user') ? 'user' : 'assistant';
        const contentEl = el.querySelector('.message-content');
        if (contentEl) msgs.push({ role, html: contentEl.innerHTML });
    });
    if (msgs.length === 0) return;
    const s = sessions.get(currentSessionId);
    if (!s) return;
    s.messages = msgs;
    const firstUser = msgs.find(m => m.role === 'user');
    if (firstUser) {
        const tmp = document.createElement('div');
        tmp.innerHTML = firstUser.html;
        s.name = (tmp.textContent || '新对话').trim().substring(0, 25);
    }
    saveSessionsToStorage();
    localStorage.setItem('oncall_last_session', currentSessionId);
}

function renderSessionMessages(sid) {
    chatMessages.innerHTML = '';
    welcomeGreeting.style.display = 'none';
    const s = sessions.get(sid);
    if (!s || s.messages.length === 0) { welcomeGreeting.style.display = 'block'; return; }
    s.messages.forEach(msg => {
        const div = document.createElement('div');
        div.className = `message ${msg.role}`;
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = msg.role === 'user' ? '我' : 'AI';
        const body = document.createElement('div');
        body.className = 'message-content';
        body.innerHTML = msg.html;
        div.appendChild(avatar); div.appendChild(body);
        chatMessages.appendChild(div);
    });
    scrollToBottom();
}

function switchToSession(sid) {
    if (sid === currentSessionId) return;
    saveCurrentSessionMessages();
    currentSessionId = sid;
    renderSessionMessages(sid);
    renderSidebar();
    localStorage.setItem('oncall_last_session', sid);
}

function startNewChat() {
    saveCurrentSessionMessages();
    currentSessionId = generateSessionId();
    sessions.set(currentSessionId, { name: '新对话', messages: [] });
    chatMessages.innerHTML = '';
    welcomeGreeting.style.display = 'block';
    renderSidebar();
    saveSessionsToStorage();
}

function renderSidebar() {
    chatHistoryList.innerHTML = '';
    Array.from(sessions.entries()).reverse().forEach(([id, s]) => {
        const item = document.createElement('div');
        item.className = 'chat-history-item' + (id === currentSessionId ? ' active' : '');
        item.textContent = s.name || '新对话';
        item.addEventListener('click', () => switchToSession(id));
        chatHistoryList.appendChild(item);
    });
}

// ==================== 事件监听 ====================
sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
newChatBtn.addEventListener('click', startNewChat);
toolsBtn.addEventListener('click', (e) => {
    e.stopPropagation(); toolsMenu.classList.toggle('show'); modeDropdown.classList.remove('show');
});
uploadFileItem.addEventListener('click', () => { fileInput.click(); toolsMenu.classList.remove('show'); });
fileInput.addEventListener('change', handleFileUpload);
modeSelectorBtn.addEventListener('click', (e) => {
    e.stopPropagation(); modeDropdown.classList.toggle('show'); toolsMenu.classList.remove('show');
});
document.addEventListener('click', () => { toolsMenu.classList.remove('show'); modeDropdown.classList.remove('show'); });
document.querySelectorAll('.dropdown-item').forEach(item => {
    item.addEventListener('click', (e) => {
        currentMode = e.currentTarget.dataset.mode;
        const names = { quick: '快速', stream: '流式' };
        currentModeText.textContent = names[currentMode] || currentMode;
        document.querySelectorAll('.dropdown-item').forEach(el => el.classList.toggle('active', el.dataset.mode === currentMode));
        modeDropdown.classList.remove('show');
    });
});
aiOpsBtn.addEventListener('click', runAIOpsDiagnosis);
vectorDbBtn.addEventListener('click', openVectorDbModal);
closeModalBtn.addEventListener('click', () => vectorDbModal.classList.remove('show'));
vectorDbModal.addEventListener('click', (e) => { if (e.target === vectorDbModal) vectorDbModal.classList.remove('show'); });

// ==================== 消息发送 ====================

async function sendMessage() {
    const question = messageInput.value.trim();
    if (!question || isProcessing) return;
    isProcessing = true; messageInput.value = '';
    welcomeGreeting.style.display = 'none'; sendButton.disabled = true;
    addMessage('user', question);
    if (currentMode === 'stream') await sendStreamMessage(question);
    else await sendQuickMessage(question);
    isProcessing = false; sendButton.disabled = false; messageInput.focus();
    saveCurrentSessionMessages(); renderSidebar();
}

async function sendQuickMessage(question) {
    const aiMsgEl = addMessage('assistant', '');
    const contentEl = aiMsgEl.querySelector('.message-content');
    contentEl.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    try {
        const r = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ Id: currentSessionId, Question: question }),
        });
        const d = await r.json();
        contentEl.innerHTML = marked.parse((d.code === 200 && d.data) ? (d.data.answer || '') : ('**错误**: ' + (d.data?.errorMessage || '未知错误')));
    } catch (e) { contentEl.innerHTML = marked.parse('**网络错误**: ' + e.message); }
    scrollToBottom();
}

async function sendStreamMessage(question) {
    const aiMsgEl = addMessage('assistant', '');
    const contentEl = aiMsgEl.querySelector('.message-content');
    contentEl.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
    let full = '';
    try {
        const r = await fetch(`${API_BASE}/api/chat_stream`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ Id: currentSessionId, Question: question }),
        });
        const reader = r.body.getReader(); const decoder = new TextDecoder(); let buf = '';
        while (true) {
            const { done, value } = await reader.read(); if (done) break;
            buf += decoder.decode(value, { stream: true });
            const lines = buf.split('\n'); buf = lines.pop() || '';
            for (const line of lines) {
                if (!line.trim() || !line.startsWith('data: ')) continue;
                try {
                    const d = JSON.parse(line.slice(6));
                    if (d.type === 'content' && d.data) { full += d.data; contentEl.innerHTML = marked.parse(full); scrollToBottom(); }
                    else if (d.type === 'error') contentEl.innerHTML = marked.parse('**错误**: ' + (d.data || '流式中断'));
                } catch (e) {}
            }
        }
    } catch (e) { contentEl.innerHTML = marked.parse('**网络错误**: ' + e.message); }
    scrollToBottom();
}

// ==================== 文件上传 ====================

async function handleFileUpload(event) {
    const file = event.target.files[0]; if (!file) return;
    const fd = new FormData(); fd.append('file', file);
    try {
        const r = await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: fd });
        const d = await r.json();
        addMessage('assistant', d.code === 200 ? `文件 \`${d.data.filename}\` 上传成功` : `**上传失败**: ${d.message}`);
    } catch (e) { addMessage('assistant', `**上传失败**: ${e.message}`); }
    fileInput.value = '';
    saveCurrentSessionMessages(); renderSidebar();
}

// ==================== 向量库查看 ====================

async function openVectorDbModal() {
    vectorDbModal.classList.add('show');
    vectorDbContent.innerHTML = '<div class="modal-loading">加载中...</div>';

    try {
        const r = await fetch(`${API_BASE}/api/index_status`);
        const d = await r.json();
        if (d.code !== 200 || !d.data) {
            vectorDbContent.innerHTML = '<div class="modal-empty">获取索引状态失败</div>';
            return;
        }
        const stats = d.data;
        if (stats.total_files === 0) {
            vectorDbContent.innerHTML = '<div class="modal-empty">向量库为空，请先上传文档</div>';
            return;
        }

        let html = `
            <div class="modal-stats">
                <div class="modal-stat-card">
                    <div class="stat-value">${stats.total_files}</div>
                    <div class="stat-label">文件数</div>
                </div>
                <div class="modal-stat-card">
                    <div class="stat-value">${stats.total_documents}</div>
                    <div class="stat-label">切片总数</div>
                </div>
            </div>`;

        stats.files.forEach((file, fi) => {
            html += `
            <div class="modal-file-card" id="file-${fi}">
                <div class="modal-file-header" onclick="toggleChunks(this)">
                    <span>${escapeHtml(file.file_name)}</span>
                    <div class="file-header-right">
                        <span class="file-badge">${file.chunk_count} 个切片</span>
                        <button class="file-delete-btn" onclick="deleteVectorFile(event, '${escapeHtml(file.file_name)}', ${fi})" title="删除此文件的全部切片">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14"/></svg>
                        </button>
                    </div>
                </div>
                <div class="modal-chunk-list">`;
            file.chunks.forEach((chunk, ci) => {
                html += `
                    <div class="modal-chunk-item">
                        <div class="chunk-index">切片 #${ci + 1} · ${chunk.content_length} 字符</div>
                        <div class="chunk-preview">${escapeHtml(chunk.content_preview)}${chunk.content_length > 200 ? '...' : ''}</div>
                    </div>`;
            });
            html += `</div></div>`;
        });

        vectorDbContent.innerHTML = html;
    } catch (e) {
        vectorDbContent.innerHTML = `<div class="modal-empty">加载失败: ${e.message}</div>`;
    }
}

async function deleteVectorFile(event, fileName, fileIndex) {
    event.stopPropagation();
    if (!confirm(`确定要从向量库删除 "${fileName}" 的全部切片吗？\n\n注意：这不会删除 uploads/ 中的原始文件，仅移除向量索引。`)) return;

    try {
        const r = await fetch(`${API_BASE}/api/index_file?file_name=${encodeURIComponent(fileName)}`, { method: 'DELETE' });
        const d = await r.json();
        if (d.code === 200) {
            // Remove the file card from the modal
            const card = document.getElementById(`file-${fileIndex}`);
            if (card) card.remove();

            // Update the stats
            const statCards = vectorDbContent.querySelectorAll('.modal-stat-card .stat-value');
            if (statCards.length >= 2) {
                const remainingFiles = vectorDbContent.querySelectorAll('.modal-file-card').length;
                statCards[0].textContent = remainingFiles;
            }
        } else {
            alert(d.message || '删除失败');
        }
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
}

function toggleChunks(header) {
    const list = header.nextElementSibling;
    if (list) list.classList.toggle('open');
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ==================== AIOps 诊断（实时进度） ====================

async function runAIOpsDiagnosis() {
    if (isProcessing) return;
    isProcessing = true; welcomeGreeting.style.display = 'none'; sendButton.disabled = true;
    const progressEl = addMessage('assistant', '');
    const contentEl = progressEl.querySelector('.message-content');
    contentEl.innerHTML = '<div class="aiops-progress"><div class="aiops-status">正在启动诊断...</div><div class="aiops-steps"></div></div>';
    const statusEl = contentEl.querySelector('.aiops-status');
    const stepsEl = contentEl.querySelector('.aiops-steps');
    let reportContent = '';

    try {
        const r = await fetch(`${API_BASE}/api/aiops`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: currentSessionId }),
        });
        const reader = r.body.getReader(); const decoder = new TextDecoder(); let buf = '';
        while (true) {
            const { done, value } = await reader.read(); if (done) break;
            buf += decoder.decode(value, { stream: true });
            const lines = buf.split('\n'); buf = lines.pop() || '';
            for (const line of lines) {
                if (!line.trim() || !line.startsWith('data: ')) continue;
                try {
                    const e = JSON.parse(line.slice(6));
                    if (e.type === 'plan') {
                        statusEl.textContent = e.message;
                        stepsEl.innerHTML = (e.plan || []).map(p => `<div class="aiops-step pending">${p.step}. ${p.description}</div>`).join('');
                    } else if (e.type === 'step_progress') {
                        statusEl.textContent = e.message;
                        const all = stepsEl.querySelectorAll('.aiops-step');
                        if (all[e.current - 1]) { all[e.current - 1].classList.remove('pending'); all[e.current - 1].classList.add('done'); }
                    } else if (e.type === 'report') { reportContent = e.report; statusEl.textContent = e.message; }
                    else if (e.type === 'complete') reportContent = e.response || reportContent;
                } catch (ex) {}
            }
        }
        contentEl.innerHTML = reportContent ? marked.parse(reportContent) : marked.parse('# 运维诊断报告\n\n诊断流程已执行完毕。');
    } catch (e) { contentEl.innerHTML = marked.parse('**AIOps 诊断出错**: ' + e.message); }

    isProcessing = false; sendButton.disabled = false; scrollToBottom();
    saveCurrentSessionMessages(); renderSidebar();
}

// ==================== DOM 工具 ====================

function addMessage(role, content) {
    const div = document.createElement('div'); div.className = `message ${role}`;
    const av = document.createElement('div'); av.className = 'message-avatar';
    av.textContent = role === 'user' ? '我' : 'AI';
    const body = document.createElement('div'); body.className = 'message-content';
    if (role === 'assistant' && content) body.innerHTML = marked.parse(content);
    else body.textContent = content;
    div.appendChild(av); div.appendChild(body);
    chatMessages.appendChild(div);
    scrollToBottom();
    return div;
}

function scrollToBottom() { chatMessages.scrollTop = chatMessages.scrollHeight; }
