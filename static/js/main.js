// ── EXAMPLE MESSAGES ────────────────────────────────────────────────────────
const EXAMPLES = {
    phishing_en: `URGENT: Your PayPal account has been suspended due to suspicious activity. Your access will be permanently blocked within 24 hours. Click here immediately to verify your identity: http://paypal-secure-verify.xyz/login`,

    phishing_fr: `ALERTE SÉCURITÉ: Votre compte CIH Bank a été temporairement bloqué. Une activité inhabituelle a été détectée. Cliquez immédiatement pour réactiver votre accès: http://cih-bank-secure.verify-now.xyz`,

    phishing_ar: `تنبيه عاجل: تم تعليق حسابك في بنك اتيجاريوافا بسبب نشاط مشبوه. انقر فورًا للتحقق من هويتك وإعادة تفعيل حسابك: http://attijariwafa-secure.verify.ma`,

    legit_en: `Hi! Your Amazon order #274-8821903 has been shipped and is on its way. Estimated delivery: Tuesday, June 12. Track your package at amazon.com/orders. Thank you for shopping with us!`,

    url: `https://paypa1-secure-login.verify-account.xyz/confirm?user=victim&token=abc123`
};

// ── ANALYSIS HISTORY ────────────────────────────────────────────────────────
// Load history from localStorage instead of starting empty
let history = JSON.parse(localStorage.getItem("phishguard_history")) || [];

// ── SVG ICON TEMPLATES ───────────────────────────────────────────────────────
const ICONS = {
    fish: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6.5 12c.94-3.46 4.94-6 8.5-6 3.56 0 6.06 2.54 7 6-.94 3.47-3.44 6-7 6-3.56 0-7.56-2.53-8.5-6z"/><path d="M18 12v.01"/><path d="M2 12c2-2 4-3 6.5-3"/><path d="M2 12c2 2 4 3 6.5 3"/></svg>',
    check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    zap: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    globe: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>',
    target: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
    clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>'
};

// ── NAVIGATION ───────────────────────────────────────────────────────────────
function showSection(name, el) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(s => {
        s.classList.add('hidden');
        s.classList.remove('active');
    });

    // Show target
    const target = document.getElementById(`section-${name}`);
    if (target) {
        target.classList.remove('hidden');
        target.classList.add('active');
    }

    // Update nav
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    if (el) el.classList.add('active');

    return false;
}

// ── LOAD EXAMPLE ─────────────────────────────────────────────────────────────
function loadExample(key) {
    const input = document.getElementById('messageInput');
    input.value = EXAMPLES[key] || '';
    input.focus();
}

// ── CLEAR ─────────────────────────────────────────────────────────────────────
function clearAll() {
    document.getElementById('messageInput').value = '';
    showEmpty();
}

function showEmpty() {
    document.getElementById('emptyState').classList.remove('hidden');
    document.getElementById('loadingState').classList.add('hidden');
    document.getElementById('resultState').classList.add('hidden');
}

// ── LOADING ANIMATION ─────────────────────────────────────────────────────────
function showLoading() {
    document.getElementById('emptyState').classList.add('hidden');
    document.getElementById('resultState').classList.add('hidden');
    document.getElementById('loadingState').classList.remove('hidden');

    // Animate loading steps
    const steps = ['step1', 'step2', 'step3'];
    steps.forEach(s => {
        document.getElementById(s).className = 'loading-step';
    });

    // Step 1 active immediately
    document.getElementById('step1').classList.add('active');

    setTimeout(() => {
        document.getElementById('step1').classList.remove('active');
        document.getElementById('step1').classList.add('done');
        document.getElementById('step2').classList.add('active');
    }, 400);

    setTimeout(() => {
        document.getElementById('step2').classList.remove('active');
        document.getElementById('step2').classList.add('done');
        document.getElementById('step3').classList.add('active');
    }, 800);
}

// ── ANALYZE ───────────────────────────────────────────────────────────────────
async function analyzeMessage() {
    const text = document.getElementById('messageInput').value.trim();

    if (!text) {
        alert('Please enter a message to analyze.');
        return;
    }

    if (text.length < 5) {
        alert('Message is too short to analyze.');
        return;
    }

    showLoading();

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        const result = await response.json();

        if (result.error) {
            showEmpty();
            alert(result.error);
            return;
        }

        showResult(result, text);
        addToHistory(text, result);

    } catch (err) {
        showEmpty();
        alert('Connection error. Make sure the Flask server is running.');
        console.error(err);
    }
}

// ── SHOW RESULT ───────────────────────────────────────────────────────────────
function showResult(result, originalText) {
    document.getElementById('loadingState').classList.add('hidden');
    document.getElementById('resultState').classList.remove('hidden');

    const isPhishing = result.classification === 'phishing';

    // Header
    const header = document.getElementById('resultHeader');
    header.className = `result-header ${result.classification}`;

    document.getElementById('resultVerdict').innerHTML = isPhishing
        ? `<span style="color: var(--danger)">${ICONS.fish}</span> <span style="color: var(--danger)">PHISHING DETECTED</span>`
        : `<span style="color: var(--success)">${ICONS.check}</span> <span style="color: var(--success)">LEGITIMATE MESSAGE</span>`;

    // Risk level badge
    const riskEl = document.getElementById('resultRisk');
    riskEl.className = `result-risk ${result.risk_level}`;
    riskEl.innerHTML = `${ICONS.zap} ${result.risk_level.toUpperCase()}`;

    // Language badge
    document.getElementById('resultLang').innerHTML = `${ICONS.globe} ${result.language}`;

    // Confidence badge
    document.getElementById('resultConfidence').innerHTML = `${ICONS.target} ${result.confidence}% confidence`;

    // Explanation
    document.getElementById('resultExplanation').textContent = result.explanation;

    // Suspicious elements
    const suspList = document.getElementById('suspiciousList');
    const suspSection = document.getElementById('suspiciousSection');
    suspList.innerHTML = '';

    if (result.suspicious_elements && result.suspicious_elements.length > 0) {
        suspSection.classList.remove('hidden');
        result.suspicious_elements.forEach(el => {
            const div = document.createElement('div');
            div.className = 'suspicious-item';
            div.innerHTML = `<span>${ICONS.alert}</span> ${el}`;
            suspList.appendChild(div);
        });
    } else {
        suspSection.classList.add('hidden');
    }

    // Recommendations
    document.getElementById('resultRecommendations').textContent = result.recommendations;

    // Similar cases
    const simList = document.getElementById('similarList');
    const simSection = document.getElementById('similarSection');
    simList.innerHTML = '';

    if (result.similar_cases && result.similar_cases.length > 0) {
        simSection.classList.remove('hidden');
        result.similar_cases.forEach(c => {
            const div = document.createElement('div');
            div.className = 'similar-item';
            div.innerHTML = `
                <div class="similar-text">${c.text.substring(0, 120)}${c.text.length > 120 ? '...' : ''}</div>
                <div class="similar-meta">
                    <span class="tag ${c.label === 'phishing' ? 'tag-phishing' : 'tag-legit'}">${c.label}</span>
                    <span class="tag tag-channel">${c.channel}</span>
                    <span class="tag tag-lang">${c.language}</span>
                    <span class="tag tag-channel">${c.attack_type}</span>
                </div>
            `;
            simList.appendChild(div);
        });
    } else {
        simSection.classList.add('hidden');
    }
}

// ── ADD HISTORY CARD HELPER ───────────────────────────────────────────────────
function addHistoryCard(text, result, timeStr) {
    const historyList = document.getElementById("historyList");
    if (!historyList) return;

    const isPhishing = result.classification === "phishing";

    const item = document.createElement("div");
    item.className = "history-item";

    item.onclick = () => {
        document.getElementById("messageInput").value = text;
        showResult(result, text);
        showSection("analyze", document.querySelector(".nav-item"));
    };

    item.innerHTML = `
        <div class="history-verdict ${result.classification}">
            ${isPhishing ? ICONS.fish : ICONS.check}
        </div>
        <div class="history-content">
            <div class="history-text">
                ${text.substring(0,80)}${text.length>80?'...':''}
            </div>
            <div class="history-meta">
                <span class="tag ${isPhishing?'tag-phishing':'tag-legit'}">
                    ${result.classification}
                </span>
                <span class="tag result-risk ${result.risk_level}">
                    ${result.risk_level}
                </span>
            </div>
        </div>
        <div class="history-time">${timeStr}</div>
    `;

    historyList.appendChild(item);
}

// ── HISTORY ───────────────────────────────────────────────────────────────────
function addToHistory(text, result) {
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    history.unshift({ text, result, time: timeStr });
    
    // Save to localStorage
    localStorage.setItem("phishguard_history", JSON.stringify(history));

    // Update history UI
    const historyList = document.getElementById('historyList');
    const historyEmpty = document.getElementById('historyEmpty');

    if (historyEmpty) historyEmpty.classList.add('hidden');
    
    // Clear existing list and rebuild (to avoid duplicates)
    if (historyList) {
        historyList.innerHTML = '';
        history.forEach(item => {
            addHistoryCard(item.text, item.result, item.time);
        });
    }
}

// ── CLEAR HISTORY FUNCTION ────────────────────────────────────────────────────
function clearHistory() {
    if (!confirm("Delete all analysis history?")) {
        return;
    }

    // Empty the array
    history = [];

    // Remove from browser storage
    localStorage.removeItem("phishguard_history");

    // Clear the UI
    const historyList = document.getElementById("historyList");
    if (historyList) {
        historyList.innerHTML = "";
    }

    // Show empty message
    const historyEmpty = document.getElementById("historyEmpty");
    if (historyEmpty) {
        historyEmpty.classList.remove("hidden");
    }
}

// ── PDF UPLOAD ────────────────────────────────────────────────────────────────
function dragOver(e) {
    e.preventDefault();
    document.getElementById('uploadZone').classList.add('drag-over');
}

function dragLeave(e) {
    document.getElementById('uploadZone').classList.remove('drag-over');
}

function dropFile(e) {
    e.preventDefault();
    document.getElementById('uploadZone').classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) processUpload(file);
}

function uploadPDF(input) {
    const file = input.files[0];
    if (file) processUpload(file);
}

async function processUpload(file) {
    if (!file.name.endsWith('.pdf')) {
        showUploadResult('error', 'Only PDF files are accepted.');
        return;
    }

    showUploadResult('loading', `Uploading ${file.name}...`);

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/upload_pdf', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.error) {
            showUploadResult('error', result.error);
        } else {
            showUploadResult('success',
                `${result.message} (${result.pages_indexed} pages indexed)`
            );

            // Reload PDF list from server to get updated registry
            await loadPDFList();
        }
    } catch (err) {
        showUploadResult('error', 'Upload failed. Check server connection.');
        console.error(err);
    }
}

// ── LOAD PDF LIST FROM SERVER ─────────────────────────────────────────────────
async function loadPDFList() {
    try {
        const response = await fetch('/get_pdfs');
        const result = await response.json();
        
        const kbList = document.querySelector('.kb-list');
        const noExtraPdfs = document.getElementById('noExtraPdfs');
        
        if (!kbList) return;
        
        // Clear existing list
        kbList.innerHTML = '';
        
        if (result.pdfs && result.pdfs.length > 0) {
            if (noExtraPdfs) noExtraPdfs.classList.add('hidden');
            
            result.pdfs.forEach(pdf => {
                const item = document.createElement('div');
                item.className = 'kb-item';
                item.innerHTML = `
                    <div class="kb-icon">${ICONS.file}</div>
                    <div class="kb-info">
                        <div class="kb-name">${escapeHtml(pdf.name)}</div>
                        <div class="kb-meta">${pdf.pages} pages indexed · Added ${pdf.added_date}</div>
                    </div>
                    <span class="badge badge-green">Active</span>
                `;
                kbList.appendChild(item);
            });
        } else {
            if (noExtraPdfs) noExtraPdfs.classList.remove('hidden');
        }
    } catch (err) {
        console.error('Failed to load PDF list:', err);
    }
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showUploadResult(type, message) {
    const el = document.getElementById('uploadResult');
    if (el) {
        el.classList.remove('hidden', 'success', 'error');
        if (type !== 'loading') el.classList.add(type);
        el.textContent = message;
    }
}

// ── KEYBOARD SHORTCUT ─────────────────────────────────────────────────────────
document.addEventListener('keydown', (e) => {
    // Ctrl+Enter to analyze
    if (e.ctrlKey && e.key === 'Enter') {
        analyzeMessage();
    }
});

// ── INIT ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Animate bar chart fills on dashboard load
    document.querySelectorAll('.bar-fill').forEach(bar => {
        const finalWidth = bar.style.width;
        bar.style.width = '0%';
        setTimeout(() => { bar.style.width = finalWidth; }, 300);
    });
    
    // Load history from localStorage and display
    const historyList = document.getElementById("historyList");
    const historyEmpty = document.getElementById("historyEmpty");

    if (history.length > 0 && historyList) {
        if (historyEmpty) historyEmpty.classList.add("hidden");

        history.forEach(item => {
            addHistoryCard(item.text, item.result, item.time);
        });
    }
    
    // Load PDF list from server
    loadPDFList();
    
    // Set up clear history button
    const clearBtn = document.getElementById("clearHistoryBtn");
    if (clearBtn) {
        clearBtn.addEventListener("click", clearHistory);
    }
});