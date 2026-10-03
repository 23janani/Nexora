/**
 * Enterprise Candidate Requirement Analysis Portal Controller
 * Strict compliance: zero emojis, zero em dashes, rectangular radii, corporate palette
 */

function refreshIcons() {
    try {
        if (typeof window !== 'undefined' && window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
        }
    } catch (e) {
        // Silently continue if icon library is unavailable
    }
}

let allCandidates = [];
let currentFilter = 'all';
let currentSearch = '';
let currentSort = { column: 'fit_score', order: 'desc' };
let currentActiveCandidate = null;
let currentBatchCandidates = [];

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

function initApp() {
    loadStats();
    loadCandidates();
    setupEventListeners();
    setupModeSwitcher();
    setupEmailIngestion();
    setupEmailMonitor();
    setupUserMode();
    setupInterviewCustomizer();
    setupQuestionEditModal();
    setupInterviewScheduling();
    setupCandidateRoadmap();
}

function setupEventListeners() {
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleTheme);
    }

    const searchInput = document.getElementById('candidateSearch');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            currentSearch = e.target.value.toLowerCase();
            renderCandidatesTable();
        });
    }

    document.querySelectorAll('.filter-pill').forEach(pill => {
        pill.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
            e.target.classList.add('active');
            currentFilter = e.target.getAttribute('data-filter');
            renderCandidatesTable();
        });
    });

    setupDropzone();
    setupJDStudio();

    const demoBatchBtn = document.getElementById('loadDemoBatchBtn');
    if (demoBatchBtn) {
        demoBatchBtn.addEventListener('click', loadDemoBatch);
    }

    const domainConfigBtn = document.getElementById('domainConfigBtn');
    if (domainConfigBtn) {
        domainConfigBtn.addEventListener('click', openDomainModal);
    }

    const closeModalBtn = document.getElementById('closeModalBtn');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeCandidateModal);
    }

    const modalOverlay = document.getElementById('candidateModalOverlay');
    if (modalOverlay) {
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) closeCandidateModal();
        });
    }

    document.querySelectorAll('.modal-nav-tabs .modal-tab-btn, .modal-tabs .modal-tab-btn, .modal-tab-btn[data-target]').forEach(tab => {
        tab.addEventListener('click', (e) => {
            const btn = e.target.closest('.modal-tab-btn');
            if (!btn) return;
            const targetId = btn.getAttribute('data-target');
            if (!targetId) return;
            
            const navContainer = btn.closest('.modal-nav-tabs, .modal-tabs') || document;
            navContainer.querySelectorAll('.modal-tab-btn').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.modal-tab-pane').forEach(p => p.style.display = 'none');
            
            btn.classList.add('active');
            const targetPane = document.getElementById(targetId);
            if (targetPane) targetPane.style.display = 'block';
            refreshIcons();
        });
    });

    const closeErrorBtn = document.getElementById('closeErrorModalBtn');
    if (closeErrorBtn) {
        closeErrorBtn.addEventListener('click', () => {
            document.getElementById('errorModalOverlay').classList.remove('active');
        });
    }

    const immediateDismissBtn = document.getElementById('immediateDismissBtn');
    if (immediateDismissBtn) {
        immediateDismissBtn.addEventListener('click', () => {
            const banner = document.getElementById('immediateReportSection');
            if (banner) banner.style.display = 'none';
        });
    }

    const btnSelectMultiple = document.getElementById('btnSelectMultipleFiles');
    const resumeFileInput = document.getElementById('resumeFileInput');
    if (btnSelectMultiple && resumeFileInput) {
        btnSelectMultiple.addEventListener('click', () => resumeFileInput.click());
    }

    const btnLoadBatchSample = document.getElementById('btnLoadBatchSample');
    if (btnLoadBatchSample) {
        btnLoadBatchSample.addEventListener('click', loadDemoBatch);
    }

    const btnToggleAddQuestion = document.getElementById('btnToggleAddQuestion');
    if (btnToggleAddQuestion) {
        btnToggleAddQuestion.addEventListener('click', () => {
            const box = document.getElementById('recruiterQuestionBox');
            if (box) {
                box.style.display = box.style.display === 'none' ? 'block' : 'none';
            }
        });
    }

    const btnSubmitCustomQuestion = document.getElementById('btnSubmitCustomQuestion');
    if (btnSubmitCustomQuestion) {
        btnSubmitCustomQuestion.addEventListener('click', submitCustomQuestion);
    }
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    const icon = document.getElementById('themeIcon');
    if (icon) {
        icon.setAttribute('data-lucide', next === 'dark' ? 'sun' : 'moon');
        refreshIcons();
    }
}

// =========================================================================
// STATS & CANDIDATES LOADING
// =========================================================================

async function loadStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        
        document.getElementById('statProcessedToday').innerText = data.total_resumes_processed;
        document.getElementById('statHighMatches').innerText = data.high_match_count;
        document.getElementById('statAvgFit').innerText = `${data.average_fit_score}%`;
        document.getElementById('statReviewFlags').innerText = data.review_required_count;
        document.getElementById('statDuplicates').innerText = data.duplicate_count;
        document.getElementById('statAiSignals').innerText = data.ai_flag_count;

        if (data.custom_domain) {
            const domainDisp = document.getElementById('navDomainDisplay');
            if (domainDisp) domainDisp.innerText = data.custom_domain;
        }

        if (data.active_jd) {
            document.getElementById('activeJdTitle').innerText = data.active_jd.title;
            document.getElementById('activeJdReqCount').innerText = `(${data.active_jd.must_haves_count} Required : ${data.active_jd.nice_to_haves_count} Preferred)`;
        }
    } catch (e) {
        console.error('Error loading stats:', e);
    }
}

async function loadCandidates() {
    try {
        const res = await fetch('/api/candidates');
        allCandidates = await res.json();
        renderCandidatesTable();
    } catch (e) {
        console.error('Error loading candidates:', e);
    }
}

function renderCandidatesTable() {
    const tbody = document.getElementById('candidatesTableBody');
    if (!tbody) return;

    let filtered = allCandidates.filter(c => {
        if (currentSearch && !c.name.toLowerCase().includes(currentSearch) && !c.filename.toLowerCase().includes(currentSearch)) {
            return false;
        }
        if (currentFilter === 'high_match' && c.fit_score < 80) return false;
        if (currentFilter === 'mid_match' && (c.fit_score < 50 || c.fit_score >= 80)) return false;
        if (currentFilter === 'duplicate' && !c.flags.duplicate) return false;
        if (currentFilter === 'ai_signal' && !c.flags.ai_content) return false;
        if (currentFilter === 'repeated' && !c.flags.repeated_content) return false;
        if (currentFilter === 'flagged' && !(c.flags.duplicate || c.flags.ai_content || c.flags.repeated_content)) return false;
        if (currentFilter === 'clean' && (c.flags.duplicate || c.flags.ai_content || c.flags.repeated_content)) return false;

        return true;
    });

    filtered.sort((a, b) => {
        let valA = a[currentSort.column];
        let valB = b[currentSort.column];
        if (typeof valA === 'string') {
            valA = valA.toLowerCase();
            valB = valB.toLowerCase();
        }
        if (valA < valB) return currentSort.order === 'asc' ? -1 : 1;
        if (valA > valB) return currentSort.order === 'asc' ? 1 : -1;
        return 0;
    });

    document.getElementById('tableCandidateCount').innerText = `${filtered.length} candidates in view`;

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 3rem; color: var(--text-muted);">
                    <div style="font-size: 1rem; font-weight: 600; margin-bottom: 0.35rem;">No candidates match your filter criteria</div>
                    <div style="font-size: 0.8rem;">Adjust search terms or clear active filters.</div>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered.map(c => {
        const scoreClass = c.fit_score >= 80 ? 'score-high' : (c.fit_score >= 50 ? 'score-mid' : 'score-low');
        
        const flagsHtml = [];
        if (c.flags.duplicate) {
            flagsHtml.push(`<span class="flag-badge flag-duplicate" title="Duplicate Content Detected">Duplicate</span>`);
        }
        if (c.flags.ai_content) {
            flagsHtml.push(`<span class="flag-badge flag-ai" title="AI-Content Signal Flagged">AI Signal</span>`);
        }
        if (c.flags.repeated_content) {
            flagsHtml.push(`<span class="flag-badge flag-repeated" title="Repeated / Unusual Content">Repeated Text</span>`);
        }
        if (flagsHtml.length === 0) {
            flagsHtml.push(`<span class="flag-badge flag-clean">Verified Clean</span>`);
        }

        const initials = c.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();

        return `
            <tr>
                <td>
                    <div class="candidate-cell">
                        <div class="candidate-avatar">${initials}</div>
                        <div class="candidate-meta">
                            <span class="candidate-name" onclick="viewCandidateDetail('${c.id}')">${c.name}</span>
                            <span class="candidate-filename">${c.file_type} : ${c.filename}</span>
                        </div>
                    </div>
                </td>
                <td>
                    <div class="score-badge-circle ${scoreClass}">
                        ${c.fit_score}%
                    </div>
                </td>
                <td>
                    <div style="font-weight: 700; font-size: 0.88rem; color: #60A5FA;">
                        ${c.confidence}%
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-muted);">Reliability Index</div>
                </td>
                <td>
                    <div class="matches-pill-group">
                        <span class="pill-count pill-match" title="Direct and Contextual Matches">MATCH: ${c.matches_count}</span>
                        <span class="pill-count pill-partial" title="Partial Matches">PARTIAL: ${c.partial_count}</span>
                        <span class="pill-count pill-gap" title="Missing Requirements">GAP: ${c.gaps_count}</span>
                    </div>
                </td>
                <td>
                    <div class="flags-group">
                        ${flagsHtml.join(' ')}
                    </div>
                </td>
                <td>
                    <span style="font-size: 0.72rem; font-weight: 600; padding: 0.2rem 0.5rem; border-radius: var(--radius-sm); background: rgba(22, 163, 74, 0.1); color: var(--color-match);">
                        ${c.status}
                    </span>
                </td>
                <td style="text-align: right;">
                    <div style="display: flex; align-items: center; justify-content: flex-end; gap: 0.4rem;">
                        <button class="btn btn-secondary" style="padding: 0.35rem 0.7rem; font-size: 0.76rem;" onclick="viewCandidateDetail('${c.id}')">
                            <i data-lucide="scan-eye" style="width: 13px; height: 13px;"></i> Assess
                        </button>
                        <a href="/api/export-dossier/${c.id}" class="btn btn-secondary" style="padding: 0.35rem 0.6rem;" title="Download Dossier PDF">
                            <i data-lucide="download" style="width: 13px; height: 13px;"></i>
                        </a>
                    </div>
                </td>
            </tr>
        `;
    }).join('');

    refreshIcons();
}

function sortTable(column) {
    if (currentSort.column === column) {
        currentSort.order = currentSort.order === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = column;
        currentSort.order = 'desc';
    }
    renderCandidatesTable();
}

// =========================================================================
// UPLOAD DROPZONE
// =========================================================================

function setupDropzone() {
    const dropzone = document.getElementById('resumeDropzone');
    const fileInput = document.getElementById('resumeFileInput');
    if (!dropzone || !fileInput) return;

    ['dragenter', 'dragover'].forEach(name => {
        dropzone.addEventListener(name, (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(name => {
        dropzone.addEventListener(name, (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) handleFileUpload(files);
    });

    dropzone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) handleFileUpload(fileInput.files);
    });
}

async function handleFileUpload(files) {
    const queueList = document.getElementById('uploadQueueList');
    const formData = new FormData();

    for (let i = 0; i < files.length; i++) {
        formData.append('resumes', files[i]);
    }

    if (queueList) {
        queueList.innerHTML = Array.from(files).map(f => `
            <div class="queue-item">
                <div class="queue-info">
                    <span class="format-badge">${f.name.split('.').pop().toUpperCase()}</span>
                    <span>${f.name} (${(f.size/1024).toFixed(1)} KB)</span>
                </div>
                <span style="color: var(--color-accent); font-size: 0.74rem;">Extracting text and running OCR...</span>
            </div>
        `).join('');
    }

    try {
        const res = await fetch('/api/upload-resumes', {
            method: 'POST',
            body: formData
        });
        const result = await res.json();

        if (result.unreadable_errors && result.unreadable_errors.length > 0) {
            showReadabilityErrors(result.unreadable_errors);
        }

        await loadStats();
        await loadCandidates();

        currentBatchCandidates = result.candidates || [];

        if (currentBatchCandidates.length > 0) {
            // Sort batch candidates with highest fit_score first
            currentBatchCandidates.sort((a, b) => b.fit_score - a.fit_score);
            const topCand = currentBatchCandidates[0];

            // Render batch navigation bar if multiple resumes were uploaded
            const batchNav = document.getElementById('immediateBatchNav');
            const batchChips = document.getElementById('immediateBatchChips');
            const batchBadge = document.getElementById('immediateBatchCountBadge');

            if (batchNav && batchChips) {
                if (currentBatchCandidates.length > 1) {
                    batchNav.style.display = 'flex';
                    if (batchBadge) batchBadge.innerText = `Batch Ingestion (${currentBatchCandidates.length} Resumes Evaluated)`;
                    batchChips.innerHTML = currentBatchCandidates.map(c => `
                        <button class="batch-chip ${c.id === topCand.id ? 'active' : ''}" id="batchChip-${c.id}" onclick="switchImmediateBatchCandidate('${c.id}')">
                            ${escapeHtml(c.name)} (${c.fit_score}%)
                        </button>
                    `).join('');
                } else {
                    batchNav.style.display = 'none';
                }
            }

            renderImmediateReport(topCand);
            viewCandidateDetail(topCand.id);
        }

        if (queueList) {
            if (currentBatchCandidates.length > 1) {
                queueList.innerHTML = `
                    <div style="padding: 0.65rem 0.85rem; background: rgba(22, 163, 74, 0.1); border: 1px solid var(--color-match); border-radius: var(--radius-sm); color: var(--color-match); font-size: 0.78rem;">
                        <b>Batch Ingestion Complete:</b> Successfully processed and scored ${currentBatchCandidates.length} resumes. Use the candidate switcher chips above to inspect individual scorecards.
                    </div>
                `;
            } else if (currentBatchCandidates.length === 1) {
                const c = currentBatchCandidates[0];
                queueList.innerHTML = `
                    <div style="padding: 0.65rem 0.85rem; background: rgba(22, 163, 74, 0.1); border: 1px solid var(--color-match); border-radius: var(--radius-sm); color: var(--color-match); font-size: 0.78rem; display: flex; justify-content: space-between; align-items: center;">
                        <span>Evaluated <b>${escapeHtml(c.name)}</b>: <b>${c.fit_score}% Fit Score</b> (${c.matches_count} Matches, ${c.gaps_count} Gaps)</span>
                        <button class="btn btn-secondary" style="padding: 0.2rem 0.55rem; font-size: 0.72rem;" onclick="viewCandidateDetail('${c.id}')">View Dossier</button>
                    </div>
                `;
            } else {
                queueList.innerHTML = `
                    <div style="padding: 0.65rem 0.85rem; background: rgba(22, 163, 74, 0.1); border: 1px solid var(--color-match); border-radius: var(--radius-sm); color: var(--color-match); font-size: 0.78rem;">
                        Processed ${result.processed_count} resume file(s). Structured extraction and semantic scoring complete.
                    </div>
                `;
            }
        }
    } catch (e) {
        console.error('Upload failed:', e);
        alert('Upload failed. Check file format or server status.');
    }
}

function switchImmediateBatchCandidate(candId) {
    const cand = currentBatchCandidates.find(c => c.id === candId);
    if (!cand) return;

    document.querySelectorAll('.batch-chip').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById(`batchChip-${candId}`);
    if (activeBtn) activeBtn.classList.add('active');

    renderImmediateReport(cand);
}

function renderImmediateReport(cand) {
    const section = document.getElementById('immediateReportSection');
    if (!section || !cand) return;

    section.style.display = 'block';

    const nameEl = document.getElementById('immediateCandidateName');
    if (nameEl) nameEl.innerText = cand.name || 'Candidate Assessment';

    const fileEl = document.getElementById('immediateFilename');
    if (fileEl) fileEl.innerText = cand.filename || '';

    const dossierLink = document.getElementById('immediateDossierLink');
    if (dossierLink) dossierLink.href = `/api/export-dossier/${cand.id}`;

    const openModalBtn = document.getElementById('immediateOpenModalBtn');
    if (openModalBtn) {
        openModalBtn.onclick = () => viewCandidateDetail(cand.id);
    }

    const scoreNum = document.getElementById('immediateScoreNumber');
    const scoreBox = document.getElementById('immediateScoreBox');
    const score = cand.fit_score !== undefined ? cand.fit_score : 0;
    if (scoreNum) scoreNum.innerText = `${score}%`;

    if (scoreBox) {
        scoreBox.className = 'immediate-score-box';
        if (score >= 80) scoreBox.classList.add('score-high');
        else if (score >= 50) scoreBox.classList.add('score-mid');
        else scoreBox.classList.add('score-low');
    }

    const confVal = document.getElementById('immediateConfidenceVal');
    if (confVal) confVal.innerText = `${cand.confidence || 0}%`;

    const confText = document.getElementById('immediateConfidenceText');
    if (confText) confText.innerText = cand.confidence_disclaimer || 'High Document Fidelity';

    const mCount = document.getElementById('immediateMatchCount');
    if (mCount) mCount.innerText = `MATCH: ${cand.matches_count || 0}`;

    const pCount = document.getElementById('immediatePartialCount');
    if (pCount) pCount.innerText = `PARTIAL: ${cand.partial_count || 0}`;

    const gCount = document.getElementById('immediateGapCount');
    if (gCount) gCount.innerText = `GAP: ${cand.gaps_count || 0}`;

    const sumText = document.getElementById('immediateSummaryText');
    if (sumText) sumText.innerText = cand.summary || 'Candidate evaluation complete.';

    const matchesList = document.getElementById('immediateMatchesList');
    if (matchesList) {
        const matches = cand.top_matches || [];
        if (matches.length > 0) {
            matchesList.innerHTML = matches.slice(0, 3).map(m => `
                <div class="immediate-tag-item immediate-tag-match">
                    ${escapeHtml(m)}
                </div>
            `).join('');
        } else {
            matchesList.innerHTML = '<span style="font-size: 0.74rem; color: var(--text-muted);">No direct matches recorded</span>';
        }
    }

    const gapsList = document.getElementById('immediateGapsList');
    if (gapsList) {
        const gaps = cand.top_gaps || [];
        if (gaps.length > 0) {
            gapsList.innerHTML = gaps.slice(0, 3).map(g => `
                <div class="immediate-tag-item immediate-tag-gap">
                    ${escapeHtml(g)}
                </div>
            `).join('');
        } else {
            gapsList.innerHTML = '<span style="font-size: 0.74rem; color: var(--text-muted);">No critical gaps recorded</span>';
        }
    }

    const formulaEl = document.getElementById('immediateFormulaText');
    if (formulaEl && cand.fit_score_details && cand.fit_score_details.calculation_formula) {
        formulaEl.innerHTML = `<b>Formula:</b> ${cand.fit_score_details.calculation_formula}`;
    }

    refreshIcons();

    section.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function showReadabilityErrors(errors) {
    const modal = document.getElementById('errorModalOverlay');
    const list = document.getElementById('errorModalList');
    if (!modal || !list) return;

    list.innerHTML = errors.map(err => `
        <div style="background: rgba(0,0,0,0.25); border: 1px solid var(--color-gap-border); padding: 0.85rem; border-radius: var(--radius-sm); margin-bottom: 0.65rem; text-align: left;">
            <div style="font-weight: 700; color: var(--color-gap); margin-bottom: 0.2rem; font-size: 0.82rem;">
                Notice: ${err.filename} : ${err.status}
            </div>
            <div style="font-size: 0.78rem; color: #FCA5A5; margin-bottom: 0.35rem;">
                <b>Identified Issue:</b> ${err.issue}
            </div>
            <div style="font-size: 0.76rem; color: var(--text-secondary);">
                <b>Recommended Action:</b> ${err.suggestion}
            </div>
        </div>
    `).join('');

    modal.classList.add('active');
}

// =========================================================================
// JOB DESCRIPTION STUDIO
// =========================================================================

function setupJDStudio() {
    const textTab = document.getElementById('jdTabPaste');
    const fileTab = document.getElementById('jdTabFile');
    const textSection = document.getElementById('jdTextSection');
    const fileSection = document.getElementById('jdFileSection');

    if (textTab && fileTab) {
        textTab.addEventListener('click', () => {
            textTab.classList.add('active');
            fileTab.classList.remove('active');
            textSection.style.display = 'block';
            fileSection.style.display = 'none';
        });

        fileTab.addEventListener('click', () => {
            fileTab.classList.add('active');
            textTab.classList.remove('active');
            textSection.style.display = 'none';
            fileSection.style.display = 'block';
        });
    }

    const processBtn = document.getElementById('processJdBtn');
    if (processBtn) {
        processBtn.addEventListener('click', submitJD);
    }

    const presets = {
        'senior_ds': `Job Title: Senior Data Scientist - GenAI & MLOps
Requirements (Must-Have):
• 4+ years of professional industry experience in data science, predictive modeling, or machine learning engineering.
• Advanced proficiency in Python, including deep familiarity with scientific libraries such as Pandas, NumPy, and Scikit-learn.
• Proven track record of machine learning model development, validation, and evaluation in production environments.
• Experience with SQL and relational databases (PostgreSQL, Snowflake, or BigQuery) for complex data extraction and feature engineering.
• Hands-on experience with cloud infrastructure, specifically AWS (EC2, S3, SageMaker, or Lambda) for model training and deployment.
Preferred Qualifications (Nice-to-Have):
• Experience with Deep Learning frameworks (PyTorch or TensorFlow) and LLM orchestration (LangChain, Hugging Face).
• Working knowledge of MLOps best practices, Docker containerization, Kubernetes, and automated CI/CD pipelines.
• Master's or Ph.D. degree in Computer Science, Statistics, Mathematics, Data Science, or related quantitative field.`,
        'ml_infra': `Job Title: Machine Learning Platform Engineer
Requirements (Must-Have):
• 3+ years engineering scalable cloud pipelines on AWS or GCP.
• Deep expertise with Docker containerization and Kubernetes cluster management.
• High proficiency in Python and Go or C++.
• Demonstrated experience with MLOps frameworks like Kubeflow or MLflow.
Preferred Qualifications:
• Experience optimizing deep learning inference engines (TensorRT, ONNX).
• BS/MS in Computer Science.`,
        'analyst': `Job Title: Business Intelligence and Data Analyst
Requirements (Must-Have):
• 2+ years experience building executive BI dashboards in Tableau or Power BI.
• Advanced SQL skills (window functions, subqueries, CTEs, performance tuning).
• Python data manipulation skills using Pandas and NumPy.
Preferred Qualifications:
• Bachelor's degree in Economics, Business Analytics, or Statistics.`
    };

    document.querySelectorAll('.preset-chip').forEach(chip => {
        chip.addEventListener('click', (e) => {
            const key = e.target.getAttribute('data-preset');
            const textarea = document.getElementById('jdTextarea');
            if (textarea && presets[key]) {
                textarea.value = presets[key];
            }
        });
    });
}

async function submitJD() {
    const textarea = document.getElementById('jdTextarea');
    const fileInput = document.getElementById('jdFileInput');
    const statusBox = document.getElementById('jdStatusMsg');

    const formData = new FormData();
    if (fileInput && fileInput.files.length > 0) {
        formData.append('file', fileInput.files[0]);
    } else if (textarea && textarea.value.trim().length > 0) {
        formData.append('text', textarea.value.trim());
    } else {
        alert('Please paste job description text or select a file to upload.');
        return;
    }

    if (statusBox) statusBox.innerHTML = '<span style="color: var(--color-accent);">Extracting structured requirements and re-evaluating candidate pool...</span>';

    try {
        const res = await fetch('/api/process-jd', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (res.ok) {
            if (statusBox) {
                statusBox.innerHTML = `
                    <span style="color: var(--color-match); font-weight: 600;">
                        Active job criteria updated: "${data.job_title}". Re-evaluated ${data.re_analyzed_candidates_count} candidates.
                    </span>
                `;
            }
            await loadStats();
            await loadCandidates();

            if (allCandidates && allCandidates.length > 0) {
                const top = [...allCandidates].sort((a, b) => b.fit_score - a.fit_score)[0];
                if (top) {
                    try {
                        const candRes = await fetch(`/api/candidate/${top.id}`);
                        const candData = await candRes.json();
                        renderImmediateReport({
                            id: top.id,
                            name: top.name,
                            filename: top.filename,
                            fit_score: top.fit_score,
                            confidence: top.confidence,
                            confidence_disclaimer: candData.analysis?.confidence?.disclaimer,
                            matches_count: top.matches_count,
                            partial_count: top.partial_count,
                            gaps_count: top.gaps_count,
                            summary: candData.analysis?.summary,
                            top_matches: (candData.analysis?.matches || []).map(m => m.requirement),
                            top_gaps: (candData.analysis?.gaps || []).map(g => g.requirement),
                            fit_score_details: candData.analysis?.fit_score_details
                        });
                    } catch (err) {
                        console.error('Failed to update immediate report for top candidate:', err);
                    }
                }
            }
        } else {
            if (statusBox) statusBox.innerHTML = `<span style="color: var(--color-gap);">${data.error}</span>`;
        }
    } catch (e) {
        console.error('JD submit failed:', e);
        if (statusBox) statusBox.innerHTML = `<span style="color: var(--color-gap);">Failed to process job description.</span>`;
    }
}

// =========================================================================
// CANDIDATE DETAIL DEEP-DIVE MODAL
// =========================================================================

async function viewCandidateDetail(candidateId) {
    try {
        const res = await fetch(`/api/candidate/${candidateId}`);
        if (!res.ok) {
            throw new Error(`Failed to load candidate (Status: ${res.status})`);
        }
        const cand = await res.json();
        currentActiveCandidate = cand;

        const modal = document.getElementById('candidateModalOverlay');
        if (!modal) return;

        // Open modal first so candidate dashboard is immediately visible
        modal.classList.add('active');

        const sr = cand.structured_resume || {};
        const pers = sr.personal || {};

        const nameEl = document.getElementById('modalCandidateName');
        if (nameEl) nameEl.innerText = cand.name || 'Candidate';
        
        const emailEl = document.getElementById('modalCandidateEmail');
        if (emailEl) emailEl.innerText = pers.email || cand.email || 'Email on file';
        
        const phoneEl = document.getElementById('modalCandidatePhone');
        if (phoneEl) phoneEl.innerText = pers.phone || 'Phone on file';
        
        const locEl = document.getElementById('modalCandidateLocation');
        if (locEl) locEl.innerText = pers.location || 'Location on file';
        
        const dossierEl = document.getElementById('modalDossierLink');
        if (dossierEl) dossierEl.href = `/api/export-dossier/${cand.id}`;

        const analysis = cand.analysis || {};
        const fitScore = typeof analysis.fit_score === 'number' ? analysis.fit_score : 0;
        const scoreRing = document.getElementById('modalHeroScoreRing');
        const scoreClass = fitScore >= 80 ? 'score-high' : (fitScore >= 50 ? 'score-mid' : 'score-low');
        if (scoreRing) scoreRing.className = `hero-score-ring ${scoreClass}`;
        
        const scoreNumEl = document.getElementById('modalHeroScoreNumber');
        if (scoreNumEl) scoreNumEl.innerText = `${fitScore}%`;

        const conf = analysis.confidence || {};
        const confScore = typeof conf === 'number' ? conf : (conf.confidence_score || 85);
        const heroConf = document.getElementById('modalHeroConfidence');
        if (heroConf) heroConf.innerText = `${confScore}%`;
        
        const confExp = document.getElementById('modalConfidenceExplanation');
        if (confExp) confExp.innerText = (typeof conf === 'object' && conf.disclaimer) ? conf.disclaimer : 'Algorithmically evaluated based on technical requirements';

        const fitDetails = analysis.fit_score_details || {};
        const breakdown = fitDetails.category_breakdown || {};
        const breakdownContainer = document.getElementById('modalBreakdownBars');
        if (breakdownContainer) {
            breakdownContainer.innerHTML = Object.entries(breakdown).map(([cat, val]) => {
                const barColor = val >= 75 ? 'var(--color-match)' : (val >= 50 ? 'var(--color-partial)' : 'var(--color-gap)');
                return `
                    <div class="breakdown-row">
                        <span class="breakdown-label">${cat}</span>
                        <div class="progress-track">
                            <div class="progress-fill" style="width: ${val}%; background: ${barColor};"></div>
                        </div>
                        <span class="progress-val" style="color: ${barColor};">${val}%</span>
                    </div>
                `;
            }).join('');
        }

        const formulaText = document.getElementById('modalFormulaText');
        if (formulaText) {
            const formFormula = fitDetails.calculation_formula || '70% Must-Have Requirements + 30% Preferred Qualifications';
            const formExpl = fitDetails.explanation || 'Evaluated across NLP extraction and semantic similarity scores.';
            formulaText.innerHTML = `
                <b>Calculation Transparency:</b> ${formFormula}.<br/>
                <span style="color: var(--text-secondary);">${formExpl}</span>
            `;
        }

        const flagsBox = document.getElementById('modalFlagsBanner');
        if (flagsBox) {
            const flags = cand.flags || {};
            const flagItems = [];

            if (flags.duplicate && flags.duplicate.is_duplicate) {
                flagItems.push(`
                    <div style="color: #F87171; font-weight: 600; font-size: 0.8rem;">
                        Notice: Duplicate Content Detected: ${flags.duplicate.details || 'Duplicate submission detected'}
                    </div>
                `);
            }
            if (flags.ai_content && flags.ai_content.is_flagged) {
                flagItems.push(`
                    <div style="color: #93C5FD; font-weight: 600; font-size: 0.8rem;">
                        AI-Content Analysis Signal: ${flags.ai_content.display_text || 'Elevated AI marker patterns'}.
                        <span style="font-weight: 400; font-size: 0.74rem; display: block; color: var(--text-muted); margin-top: 0.2rem;">
                            ${flags.ai_content.disclaimer || 'Probabilistic signal only.'}
                        </span>
                    </div>
                `);
            }
            if (flags.repeated_content && flags.repeated_content.is_flagged) {
                const issues = Array.isArray(flags.repeated_content.issues) ? flags.repeated_content.issues.join(' : ') : 'Repetitive keywords identified';
                flagItems.push(`
                    <div style="color: var(--color-flag); font-weight: 600; font-size: 0.8rem;">
                        Repeated Content Alert: ${issues}
                    </div>
                `);
            }

            if (flagItems.length > 0) {
                flagsBox.className = 'flags-banner-box flagged';
                flagsBox.innerHTML = `
                    <div style="font-size: 0.72rem; text-transform: uppercase; font-weight: 700; letter-spacing: 0.04em; color: var(--color-flag);">
                        Integrity Review Flags (Informational Signals : Human Review Mandatory)
                    </div>
                    ${flagItems.join('')}
                `;
            } else {
                flagsBox.className = 'flags-banner-box clean';
                flagsBox.innerHTML = `
                    <div style="color: var(--color-match); font-weight: 600; font-size: 0.8rem;">
                        Integrity Audit: No duplication, textual repetition loops, or synthetic formatting signals detected.
                    </div>
                `;
            }
        }

        try { renderRequirementsMatrix(analysis.comparisons || []); } catch(err) { console.error('Matrix error:', err); }
        try { renderStructuredProfile(sr); } catch(err) { console.error('Profile error:', err); }

        const summaryEl = document.getElementById('modalExecutiveSummary');
        if (summaryEl) summaryEl.innerText = analysis.summary || 'Summary pending analysis.';
        
        const recsContainer = document.getElementById('modalRecommendationsList');
        if (recsContainer && Array.isArray(analysis.recommendations)) {
            recsContainer.innerHTML = analysis.recommendations.map(rec => `
                <div class="rec-item">
                    <i data-lucide="info" class="rec-icon" style="width: 14px; height: 14px;"></i>
                    <span>${rec}</span>
                </div>
            `).join('');
        }

        try { renderMockInterview(analysis.mock_interview || []); } catch(err) { console.error('Interview error:', err); }
        try { checkCandidateScheduledInterview(cand.id); } catch(err) { console.error('Interview status error:', err); }

        refreshIcons();

    } catch (e) {
        console.error('Failed to load candidate detail:', e);
        const modal = document.getElementById('candidateModalOverlay');
        if (modal) modal.classList.add('active');
        refreshIcons();
    }
}

function closeCandidateModal() {
    const modal = document.getElementById('candidateModalOverlay');
    if (modal) modal.classList.remove('active');
}

// =========================================================================
// TAB 1: REQUIREMENT-BY-REQUIREMENT MATRIX
// =========================================================================

function renderRequirementsMatrix(comparisons) {
    const container = document.getElementById('modalReqMatrixList');
    if (!container) return;

    container.innerHTML = comparisons.map(item => {
        let statusBadge = '';
        let borderColor = 'var(--border-subtle)';

        if (item.status === 'MATCH') {
            statusBadge = `<span class="pill-count pill-match">[MATCH]</span>`;
            borderColor = 'var(--color-match-border)';
        } else if (item.status === 'PARTIAL') {
            statusBadge = `<span class="pill-count pill-partial">[PARTIAL MATCH]</span>`;
            borderColor = 'var(--color-partial-border)';
        } else {
            statusBadge = `<span class="pill-count pill-gap">[MISSING REQUIREMENT]</span>`;
            borderColor = 'var(--color-gap-border)';
        }

        const importanceBadge = item.is_must_have ? 
            `<span style="font-size: 0.68rem; font-weight: 700; padding: 0.15rem 0.45rem; border-radius: var(--radius-sm); background: rgba(220, 38, 38, 0.15); color: #F87171;">MUST-HAVE</span>` : 
            `<span style="font-size: 0.68rem; font-weight: 700; padding: 0.15rem 0.45rem; border-radius: var(--radius-sm); background: rgba(37, 99, 235, 0.15); color: #60A5FA;">NICE-TO-HAVE</span>`;

        return `
            <div class="req-item-card" style="border-left: 3px solid ${borderColor};">
                <div class="req-item-header">
                    <div style="display: flex; align-items: center; gap: 0.55rem; flex-wrap: wrap;">
                        <span class="req-text-title">${item.requirement}</span>
                        ${importanceBadge}
                        <span style="font-size: 0.72rem; color: var(--text-muted);">[${item.category}]</span>
                    </div>
                    <div>${statusBadge}</div>
                </div>
                <div class="req-evidence-quote">
                    <b>Candidate Evidence:</b> "${item.candidate_evidence}"
                </div>
                <div class="req-reason-text">
                    <b>Analysis Rationale:</b> ${item.reason}
                </div>
            </div>
        `;
    }).join('');
}

// =========================================================================
// TAB 2: STRUCTURED PROFILE
// =========================================================================

function renderStructuredProfile(profile) {
    const bucketsContainer = document.getElementById('modalSkillBuckets');
    if (bucketsContainer && profile.skills) {
        const bucketLabels = {
            'programming_languages': 'Programming Languages',
            'frameworks': 'Frameworks',
            'libraries': 'Data Science Libraries',
            'databases': 'Databases and Warehouses',
            'cloud_technologies': 'Cloud Infrastructure',
            'ai_ml_skills': 'AI and Machine Learning',
            'tools': 'DevOps and Tooling',
            'soft_skills': 'Leadership and Communication'
        };

        bucketsContainer.innerHTML = Object.entries(profile.skills).map(([key, list]) => {
            const title = bucketLabels[key] || key.replace('_', ' ').toUpperCase();
            const tags = (list && list.length > 0) ? 
                list.map(s => `<span class="skill-tag">${s}</span>`).join('') :
                `<span style="font-size: 0.72rem; color: var(--text-muted); font-style: italic;">None identified</span>`;

            return `
                <div class="skill-bucket-card">
                    <div class="bucket-title">${title}</div>
                    <div class="bucket-tags">${tags}</div>
                </div>
            `;
        }).join('');
    }

    const edContainer = document.getElementById('modalEducationList');
    if (edContainer && profile.education) {
        edContainer.innerHTML = profile.education.map(ed => `
            <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-subtle); padding: 0.75rem; border-radius: var(--radius-sm); margin-bottom: 0.4rem;">
                <div style="font-weight: 700; font-size: 0.85rem;">${ed.degree} in ${ed.field_of_study}</div>
                <div style="font-size: 0.75rem; color: var(--text-secondary);">${ed.institution} : ${ed.graduation_year}</div>
            </div>
        `).join('');
    }

    const expContainer = document.getElementById('modalExperienceList');
    if (expContainer && profile.experience) {
        expContainer.innerHTML = profile.experience.map(exp => `
            <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-subtle); padding: 0.75rem; border-radius: var(--radius-sm); margin-bottom: 0.4rem;">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <span style="font-weight: 700; font-size: 0.85rem;">${exp.title}</span>
                    <span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">${exp.duration}</span>
                </div>
                <div style="font-size: 0.78rem; color: #60A5FA; margin-bottom: 0.35rem;">${exp.company}</div>
                <ul style="padding-left: 1.2rem; font-size: 0.76rem; color: var(--text-secondary);">
                    ${(exp.responsibilities || []).map(r => `<li>${r}</li>`).join('')}
                </ul>
            </div>
        `).join('');
    }
}

// =========================================================================
// TAB 4: TARGETED INTERVIEW QUESTIONS
// =========================================================================

function renderMockInterview(questions) {
    const container = document.getElementById('modalInterviewList');
    if (!container) return;
    if (!Array.isArray(questions)) questions = [];

    const heading = document.getElementById('modalInterviewHeading');
    if (heading) {
        heading.innerText = `Targeted Interview Questions (${questions.length} Questions)`;
    }

    container.innerHTML = questions.map((q, idx) => {
        const qId = q.id;
        const candId = currentActiveCandidate ? currentActiveCandidate.id : '';
        const isCustom = q.is_custom || q.source === 'recruiter_custom' || q.source === 'builtin_ai_custom';
        const customBadge = isCustom ? 
            `<span class="badge-customized">[CUSTOMIZED]</span>` : '';
        const diffBadge = q.difficulty ? 
            `<span class="nav-portal-badge" style="background: rgba(37,99,235,0.08); border-color: rgba(37,99,235,0.25); color: #93C5FD; font-size: 0.65rem;">${escapeHtml(q.difficulty)}</span>` : '';

        const escapedQ = escapeHtml(q.question || '').replace(/'/g, "\\'");
        const escapedCat = escapeHtml(q.category || '').replace(/'/g, "\\'");
        const escapedDiff = (q.difficulty || 'Senior').replace(/'/g, "\\'");
        const escapedHint = escapeHtml(q.evaluation_hint || '').replace(/'/g, "\\'");
        const escapedCoach = escapeHtml(q.candidate_coaching || '').replace(/'/g, "\\'");
        const gapFocus = encodeURIComponent(q.missing_skill || q.missing_skill_focus || q.target_concept || '');

        return `
            <div class="interview-card" id="interviewCard-${qId}">
                <div class="interview-card-header">
                    <div style="display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap;">
                        <span class="interview-cat-tag">Q${idx+1}: ${escapeHtml(q.category)}</span>
                        ${diffBadge}
                        ${customBadge}
                    </div>
                    <div class="q-action-toolbar">
                        <button type="button" class="q-action-btn btn-ai-action" id="btnRegen-${qId}" onclick="triggerRegenerateQuestion('${qId}', '${gapFocus}', '${encodeURIComponent(q.category || '')}', false)" title="Regenerate this question using Built-in AI">
                            <i data-lucide="sparkles" style="width: 11px; height: 11px;"></i> AI Regen
                        </button>
                        <button type="button" class="q-action-btn" onclick="openEditQuestionModal('${qId}', '${candId}')" title="Edit question text and criteria">
                            <i data-lucide="edit-3" style="width: 11px; height: 11px;"></i> Edit
                        </button>
                        <button type="button" class="q-action-btn btn-danger-action" onclick="deleteInterviewQuestion('${qId}', '${candId}')" title="Delete question">
                            <i data-lucide="trash-2" style="width: 11px; height: 11px;"></i> Delete
                        </button>
                        <button type="button" class="q-action-btn" onclick="copyInterviewQuestion('${encodeURIComponent(q.question)}')">
                            <i data-lucide="copy" style="width: 11px; height: 11px;"></i> Copy
                        </button>
                    </div>
                </div>
                <div class="interview-question-text" id="qTextDisplay-${qId}">
                    "${escapeHtml(q.question)}"
                </div>
                <div class="interview-context-text">
                    <b>Rationale:</b> ${escapeHtml(q.context || 'Anchored in candidate missing technical skills.')}
                </div>
                <div class="interview-hint-box">
                    <b>Candidate Evaluation Criteria:</b> ${escapeHtml(q.evaluation_hint || 'Listen for structured design and problem solving.')}
                </div>
            </div>
        `;
    }).join('');

    refreshIcons();
}

async function submitCustomQuestion() {
    if (!currentActiveCandidate) return;

    const inputQ = document.getElementById('inputCustomQuestionText');
    const selectCat = document.getElementById('selectCustomQuestionCategory');
    const inputHint = document.getElementById('inputCustomQuestionHint');

    const questionText = inputQ ? inputQ.value.trim() : '';
    const category = selectCat ? selectCat.value : 'Recruiter Custom Question';
    const hint = inputHint ? inputHint.value.trim() : 'Evaluate problem-solving depth and methodology.';

    if (questionText.length < 5) {
        alert('Please enter an interview question of at least 5 characters.');
        return;
    }

    try {
        const res = await fetch(`/api/v1/interview/questions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                candidate_id: currentActiveCandidate.id,
                question_text: questionText,
                category: category,
                difficulty: 'Senior',
                evaluation_hint: hint,
                candidate_coaching: 'Frame response using STAR format.'
            })
        });
        const data = await res.json();
        if (data.success) {
            currentActiveCandidate.analysis.mock_interview = currentActiveCandidate.analysis.mock_interview || [];
            currentActiveCandidate.analysis.mock_interview.push(data.question);
            renderMockInterview(currentActiveCandidate.analysis.mock_interview);
            if (inputQ) inputQ.value = '';
            if (inputHint) inputHint.value = '';
            const box = document.getElementById('recruiterQuestionBox');
            if (box) box.style.display = 'none';
        } else {
            alert(data.error || 'Failed to add question.');
        }
    } catch (e) {
        console.error('Error adding custom question:', e);
        alert('Failed to connect to server.');
    }
}

async function deleteInterviewQuestion(questionId, candidateId) {
    if (!confirm('Are you sure you want to remove this interview question?')) return;

    try {
        const res = await fetch(`/api/v1/interview/questions/${questionId}?candidate_id=${encodeURIComponent(candidateId || '')}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.success) {
            if (currentActiveCandidate && currentActiveCandidate.analysis) {
                currentActiveCandidate.analysis.mock_interview = (currentActiveCandidate.analysis.mock_interview || []).filter(
                    q => String(q.id) !== String(questionId) && String(q.id) !== String(questionId.replace('q_', ''))
                );
                renderMockInterview(currentActiveCandidate.analysis.mock_interview);
            }
        }
    } catch (e) {
        console.error('Error deleting question:', e);
    }
}

async function triggerRegenerateQuestion(questionId, encodedGapText, encodedCategory, isUserMode) {
    const btn = document.getElementById(`btnRegen-${questionId}`);
    const originalText = btn ? btn.innerHTML : '';
    if (btn) btn.innerHTML = '<i data-lucide="loader" style="width: 11px; height: 11px;"></i> Generating...';

    const gapText = decodeURIComponent(encodedGapText || '');
    const category = decodeURIComponent(encodedCategory || '');
    const candidateId = isUserMode ? 'candidate_self' : (currentActiveCandidate ? currentActiveCandidate.id : '');

    try {
        const res = await fetch(`/api/v1/interview/questions/${questionId}/regenerate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                candidate_id: candidateId,
                gap_text: gapText,
                category: category,
                difficulty: 'Senior'
            })
        });
        const data = await res.json();
        if (data.success && data.question) {
            if (!isUserMode && currentActiveCandidate && currentActiveCandidate.analysis) {
                const list = currentActiveCandidate.analysis.mock_interview || [];
                const idx = list.findIndex(q => String(q.id) === String(questionId) || String(q.id) === String(questionId.replace('q_', '')));
                if (idx !== -1) {
                    list[idx] = data.question;
                }
                renderMockInterview(list);
            } else if (isUserMode && currentUserAnalysisData) {
                const list = currentUserAnalysisData.questions || [];
                const idx = list.findIndex(q => String(q.id) === String(questionId) || String(q.id) === String(questionId.replace('q_', '')));
                if (idx !== -1) {
                    list[idx] = data.question;
                }
                renderUserInterviewQuestions(list);
            }
        } else {
            alert(data.error || 'Failed to regenerate question.');
        }
    } catch (e) {
        console.error('Error regenerating question:', e);
    } finally {
        if (btn) btn.innerHTML = originalText;
        refreshIcons();
    }
}

function copyInterviewQuestion(encodedText) {
    const text = decodeURIComponent(encodedText);
    navigator.clipboard.writeText(text).then(() => {
        alert('Question copied to clipboard.');
    });
}

// =========================================================================
// CUSTOM DOMAIN CONFIGURATION
// =========================================================================

function openDomainModal() {
    const modal = document.getElementById('domainModalOverlay');
    if (modal) modal.classList.add('active');
}

function closeDomainModal() {
    const modal = document.getElementById('domainModalOverlay');
    if (modal) modal.classList.remove('active');
}

async function saveDomainConfig() {
    const input = document.getElementById('customDomainInput');
    if (!input || !input.value.trim()) return;

    const domain = input.value.trim();
    try {
        const res = await fetch('/api/domain-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ domain: domain })
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById('navDomainDisplay').innerText = domain;
            closeDomainModal();
            alert(`Custom domain updated to: ${domain}`);
        } else {
            alert(data.error || 'Failed to update domain.');
        }
    } catch (e) {
        console.error('Domain update error:', e);
    }
}

// =========================================================================
// LOAD STANDARD BATCH
// =========================================================================

async function loadDemoBatch() {
    const btn = document.getElementById('loadDemoBatchBtn');
    if (btn) btn.innerHTML = 'Loading Dataset...';
    try {
        const res = await fetch('/api/load-samples', { method: 'POST' });
        const data = await res.json();
        await loadStats();
        await loadCandidates();
    } catch (e) {
        console.error('Failed to load demo batch:', e);
    } finally {
        if (btn) btn.innerHTML = '<i data-lucide="database" style="width: 14px; height: 14px;"></i> Load Standard Dataset';
        refreshIcons();
    }
}

// =========================================================================
// MODE SWITCHER (RECRUITER vs USER / CANDIDATE MODE)
// =========================================================================

function setupModeSwitcher() {
    const btnRecruiter = document.getElementById('btnModeRecruiter');
    const btnUser = document.getElementById('btnModeUser');
    if (btnRecruiter && btnUser) {
        btnRecruiter.addEventListener('click', () => switchAppMode('recruiter'));
        btnUser.addEventListener('click', () => switchAppMode('user'));
    }

    // Auto-apply initial mode from session if specified
    if (window.INITIAL_APP_MODE && window.INITIAL_APP_MODE === 'user') {
        switchAppMode('user');
    } else {
        switchAppMode('recruiter');
    }
}

function switchAppMode(mode) {
    const btnRecruiter = document.getElementById('btnModeRecruiter');
    const btnUser = document.getElementById('btnModeUser');
    const recruiterWs = document.getElementById('recruiterWorkspace');
    const userWs = document.getElementById('userModeWorkspace');
    const hrActions = document.getElementById('hrNavActionGroup');
    const candidateActions = document.getElementById('candidateNavActionGroup');
    const portalBadge = document.getElementById('navPortalBadge');

    if (mode === 'user') {
        if (btnRecruiter) btnRecruiter.classList.remove('active');
        if (btnUser) btnUser.classList.add('active');
        if (recruiterWs) recruiterWs.style.display = 'none';
        if (userWs) userWs.style.display = 'block';
        if (hrActions) hrActions.style.display = 'none';
        if (candidateActions) candidateActions.style.display = 'flex';

        if (portalBadge) {
            portalBadge.className = 'nav-portal-badge nav-portal-candidate';
            portalBadge.innerHTML = '<i data-lucide="user" style="width: 12px; height: 12px;"></i> <span id="navPortalBadgeText">Candidate Portal</span>';
        }
    } else {
        if (btnUser) btnUser.classList.remove('active');
        if (btnRecruiter) btnRecruiter.classList.add('active');
        if (userWs) userWs.style.display = 'none';
        if (recruiterWs) recruiterWs.style.display = 'block';
        if (candidateActions) candidateActions.style.display = 'none';
        if (hrActions) hrActions.style.display = 'flex';

        if (portalBadge) {
            portalBadge.className = 'nav-portal-badge nav-portal-hr';
            portalBadge.innerHTML = '<i data-lucide="shield-check" style="width: 12px; height: 12px;"></i> <span id="navPortalBadgeText">HR Recruiter Portal</span>';
        }
    }
    refreshIcons();
}

// =========================================================================
// HR EMAIL APPLICATION INGESTION STUDIO
// =========================================================================

function setupEmailIngestion() {
    const btnOpen = document.getElementById('btnOpenEmailIngestModal');
    const modal = document.getElementById('emailIngestModalOverlay');
    const btnClose = document.getElementById('btnCloseEmailIngestModal');
    const btnCancel = document.getElementById('btnCancelEmailIngest');
    const btnSubmit = document.getElementById('btnSubmitEmailApplication');

    if (btnOpen && modal) {
        btnOpen.addEventListener('click', () => {
            modal.classList.add('active');
            const statusBox = document.getElementById('emailIngestStatus');
            if (statusBox) statusBox.style.display = 'none';
        });
    }

    const closeModal = () => {
        if (modal) modal.classList.remove('active');
    };

    if (btnClose) btnClose.addEventListener('click', closeModal);
    if (btnCancel) btnCancel.addEventListener('click', closeModal);
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });
    }

    // Quick Test Email Presets
    const presetElena = document.getElementById('presetEmailElena');
    const presetDavid = document.getElementById('presetEmailDavid');
    const presetSophie = document.getElementById('presetEmailSophie');

    if (presetElena) {
        presetElena.addEventListener('click', () => {
            document.getElementById('emailSenderInput').value = 'Elena Vance <elena.vance@techcorp.com>';
            document.getElementById('emailSubjectInput').value = 'Application: Senior Data Scientist - GenAI & MLOps';
            document.getElementById('emailJobSelect').value = 'senior_ds_genai';
            document.getElementById('emailBodyTextarea').value = 
`Dear Hiring Team,

I am writing to express my strong interest in the Senior Data Scientist position at your organization. With over 6 years of experience in data science, predictive modeling, and deep learning, I have designed and deployed transformer-based NLP systems, automated ML pipelines with PyTorch, and optimized real-time scoring models.

Core Competencies:
- Deep Learning & NLP: PyTorch, HuggingFace transformers, BERT, LLM prompt pipelines, spaCy, NLTK
- Statistical Modeling & Analytics: Scikit-learn, XGBoost, Pandas, NumPy, statistical hypothesis testing
- Data Architecture: Distributed processing with Apache Spark/PySpark, PostgreSQL, SQL queries
- Education: M.S. in Computer Science with concentration in Machine Learning

I look forward to discussing how my experience will contribute to scaling your generative AI solutions.

Sincerely,
Elena Vance`;
        });
    }

    if (presetDavid) {
        presetDavid.addEventListener('click', () => {
            document.getElementById('emailSenderInput').value = 'David Kim <david.kim@infra-cloud.io>';
            document.getElementById('emailSubjectInput').value = 'Application: ML Platform Lead';
            document.getElementById('emailJobSelect').value = 'ml_platform_lead';
            document.getElementById('emailBodyTextarea').value = 
`Dear Technical Recruitment Team,

Please review my credentials for the ML Platform Engineer role. I bring 5+ years specializing in enterprise MLOps, containerization, and infrastructure reliability.

Technical Highlights:
- Infrastructure & Orchestration: Docker, Kubernetes, Kubeflow, MLflow, CI/CD with GitHub Actions
- Cloud Platforms: AWS (EKS, S3, IAM, CloudWatch) and GCP
- Model Serving: Triton Inference Server, FastAPI, model monitoring for data drift
- Programming: Python, Bash scripting, Go

Thank you for your consideration.

David Kim`;
        });
    }

    if (presetSophie) {
        presetSophie.addEventListener('click', () => {
            document.getElementById('emailSenderInput').value = 'Sophie Taylor <sophie.taylor@data-analytics.org>';
            document.getElementById('emailSubjectInput').value = 'Application: BI & Data Analyst';
            document.getElementById('emailJobSelect').value = 'bi_analytics_lead';
            document.getElementById('emailBodyTextarea').value = 
`Hello Recruitment Team,

I am applying for the BI and Data Analyst position. I have 3.5 years of experience delivering executive dashboards and analytical reports.

Core Skills:
- Advanced SQL, Snowflake, BigQuery, PostgreSQL
- Dashboarding & Viz: Tableau Desktop Certified, Power BI, Metabase
- Data Modeling: Dimensional modeling, star schema, dbt
- Analytics: Python (Pandas, Seaborn), exploratory data analysis, A/B testing

Best regards,
Sophie Taylor`;
        });
    }

    if (btnSubmit) {
        btnSubmit.addEventListener('click', async () => {
            const sender = document.getElementById('emailSenderInput').value.trim();
            const subject = document.getElementById('emailSubjectInput').value.trim();
            const jobId = document.getElementById('emailJobSelect').value;
            const body = document.getElementById('emailBodyTextarea').value.trim();
            const fileInput = document.getElementById('emailResumeFileInput');
            const statusBox = document.getElementById('emailIngestStatus');

            if (!body && (!fileInput || !fileInput.files || fileInput.files.length === 0)) {
                alert('Please provide an email message, resume text, or attach a resume file.');
                return;
            }

            let effectiveSender = sender;
            if (!effectiveSender && body) {
                const emailMatch = body.match(/[\w\.-]+@[\w\.-]+\.\w+/);
                effectiveSender = emailMatch ? emailMatch[0] : 'applicant@auto-detected.internal';
            }

            btnSubmit.disabled = true;
            btnSubmit.innerHTML = '<span class="pulse-dot"></span> Ingesting & Analyzing...';
            if (statusBox) {
                statusBox.style.display = 'block';
                statusBox.style.color = '#60A5FA';
                statusBox.innerText = 'Extracting resume details and matching against target job criteria...';
            }

            try {
                const formData = new FormData();
                formData.append('sender', effectiveSender);
                formData.append('subject', subject);
                formData.append('job_id', jobId);
                formData.append('body', body);

                if (fileInput && fileInput.files && fileInput.files.length > 0) {
                    formData.append('resume', fileInput.files[0]);
                }

                const res = await fetch('/api/incoming-email', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();

                if (!res.ok || !data.success) {
                    throw new Error(data.error || 'Failed to process email application.');
                }

                closeModal();
                await loadStats();
                await loadCandidates();

                const cand = data.candidate;
                if (cand) {
                    showImmediateReport(cand);
                    viewCandidateDetail(cand.id);
                }
            } catch (err) {
                if (statusBox) {
                    statusBox.style.display = 'block';
                    statusBox.style.color = 'var(--color-gap)';
                    statusBox.innerText = `Ingestion Notice: ${err.message}`;
                } else {
                    alert(`Ingestion error: ${err.message}`);
                }
            } finally {
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = '<i data-lucide="check" style="width: 14px; height: 14px;"></i> Ingest & Automatically Analyze';
                refreshIcons();
            }
        });
    }
}

// =========================================================================
// CANDIDATE / USER MODE LOGIC
// =========================================================================

let currentUserAnalysisData = null;

const STANDARD_JD_TEXTS = {
    senior_ds_genai: `Senior Data Scientist - GenAI & MLOps
Requirements (Must-Have):
• 4+ years of professional industry experience in data science, predictive modeling, or machine learning engineering.
• Advanced proficiency in Python, including deep familiarity with scientific libraries such as Pandas, NumPy, and Scikit-learn.
• Deep practical expertise in Natural Language Processing (NLP) or Deep Learning using PyTorch, TensorFlow, Transformers, or Hugging Face.
• Hands-on production experience deploying models into production environments utilizing Docker, Kubernetes, or modern MLOps frameworks.
• Demonstrated competence with Cloud infrastructure platforms, specifically AWS (SageMaker, S3, EC2, Lambda) or GCP.
• Strong relational database querying and data modeling proficiency in SQL (PostgreSQL, Snowflake, or BigQuery).
• Master's or Ph.D. degree in Computer Science, Statistics, Mathematics, Data Science, or a related quantitative discipline.

Preferred Qualifications (Nice-to-Have):
• Experience with Large Language Model (LLM) fine-tuning, retrieval-augmented generation (RAG), and prompt orchestration frameworks (LangChain, LlamaIndex).
• Experience with distributed data processing systems like Apache Spark, PySpark, or Ray.
• Familiarity with workflow orchestration tools such as Apache Airflow, Kubeflow, or Prefect.
• Track record of published machine learning research, patents, or significant contributions to open-source data science tools.`,

    ml_platform_lead: `ML Platform Engineer
Requirements (Must-Have):
• 3+ years designing and running Kubernetes clusters and containerized microservices for ML workloads.
• Proficiency in Python and Go or Bash scripting for automated infrastructure tooling.
• Production hands-on experience with MLflow, Kubeflow, or Triton Inference Server.
• Strong CI/CD pipeline automation experience with GitHub Actions, GitLab CI, or Argo Workflows.
• Experience managing AWS cloud resources (IAM, VPC, EKS, CloudWatch) using Infrastructure as Code (Terraform).
• Solid understanding of model monitoring, latency profiling, and data drift detection in production.

Preferred Qualifications (Nice-to-Have):
• Experience with GPU acceleration (CUDA, TensorRT) for high-throughput model inference.
• Experience with feature stores such as Feast or Hopsworks.
• Knowledge of Apache Kafka or streaming event pipelines.`,

    bi_analytics_lead: `BI and Data Analyst
Requirements (Must-Have):
• 3+ years experience as a Data Analyst or Business Intelligence Specialist.
• Expert-level SQL skills: complex joins, window functions, CTEs, and query performance optimization.
• Proven proficiency creating enterprise dashboards using Tableau, Power BI, or Looker.
• Experience with modern cloud data warehouses: Snowflake, Google BigQuery, or Amazon Redshift.
• Strong analytical mindset with experience conducting A/B test analysis and defining business KPI metrics.
• Bachelor's degree in Economics, Mathematics, Statistics, Computer Science, or Business.

Preferred Qualifications (Nice-to-Have):
• Working knowledge of Python (Pandas) for data wrangling and automation.
• Experience with dbt (data build tool) for data transformation.
• Experience translating complex analytical findings into executive-level presentations.`
};

function setupUserMode() {
    const userJdTextarea = document.getElementById('userJdTextarea');
    if (userJdTextarea && !userJdTextarea.value.trim()) {
        userJdTextarea.value = STANDARD_JD_TEXTS.senior_ds_genai;
    }

    document.querySelectorAll('[data-user-role]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('[data-user-role]').forEach(b => b.classList.remove('active'));
            const targetBtn = e.currentTarget;
            targetBtn.classList.add('active');
            const roleKey = targetBtn.getAttribute('data-user-role');
            if (userJdTextarea && STANDARD_JD_TEXTS[roleKey]) {
                userJdTextarea.value = STANDARD_JD_TEXTS[roleKey];
            }
        });
    });

    const btnSampleMarcus = document.getElementById('btnUserSampleMarcus');
    const btnSampleElena = document.getElementById('btnUserSampleElena');
    const userResumeTextarea = document.getElementById('userResumeTextarea');

    if (btnSampleMarcus) {
        btnSampleMarcus.addEventListener('click', () => {
            if (userResumeTextarea) {
                userResumeTextarea.value = 
`MARCUS CHEN
San Francisco, CA | marcus.chen@email.com | (555) 234-5678

PROFESSIONAL SUMMARY
Results-driven Data Scientist with 4 years of industry experience developing statistical models, data analytics pipelines, and machine learning solutions using Python, SQL, and AWS. Proven track record in customer segmentation, churn prediction, and revenue forecasting.

TECHNICAL SKILLS
- Languages: Python, SQL (PostgreSQL, MySQL), R, Bash
- Frameworks & Libraries: Scikit-learn, Pandas, NumPy, XGBoost, LightGBM, Statsmodels, Matplotlib, Seaborn
- Machine Learning: Linear/Logistic Regression, Random Forests, Gradient Boosting, Clustering (K-Means, DBSCAN), Dimensionality Reduction (PCA), Time Series Forecasting (ARIMA)
- Cloud & Infrastructure: AWS (S3, EC2, Athena), Docker basics, Git, GitHub
- Databases: PostgreSQL, MySQL, Redis, SQLite

PROFESSIONAL EXPERIENCE
Data Scientist | Nexa Analytics, San Francisco, CA | 2022 - Present
- Built and deployed predictive churn models reducing customer turnover by 14%.
- Developed end-to-end data pipelines in Python and SQL processing 2M+ records daily.
- Created interactive dashboards for executive leadership tracking churn KPIs.

Junior Data Analyst | DataWave Solutions, Oakland, CA | 2020 - 2022
- Conducted exploratory data analysis and statistical hypothesis testing on marketing campaigns.
- Authored complex SQL queries and automated reporting schedules.

EDUCATION
B.S. in Statistics | University of California, Berkeley | 2016 - 2020`;
                const label = document.getElementById('userResumeDropzoneLabel');
                if (label) label.innerText = 'Sample Resume: Marcus Chen (Loaded in text)';
            }
        });
    }

    if (btnSampleElena) {
        btnSampleElena.addEventListener('click', () => {
            if (userResumeTextarea) {
                userResumeTextarea.value = 
`ELENA VANCE, M.S.
Seattle, WA | elena.vance@example.com | (555) 987-6543

PROFESSIONAL SUMMARY
Senior Data Scientist with 6+ years of production experience in generative AI, deep learning, and Natural Language Processing. Proven track record deploying PyTorch transformers and scalable inference microservices on AWS and Kubernetes.

TECHNICAL COMPETENCIES
- Machine Learning & Deep Learning: PyTorch, Hugging Face, Transformers, Scikit-learn, XGBoost, TensorFlow
- NLP: Named Entity Recognition, Embeddings, LLM Fine-Tuning, LangChain, spaCy, NLTK
- Cloud & MLOps: AWS (SageMaker, S3, EC2, Lambda), Docker, Kubernetes, MLflow, CI/CD Actions
- Databases: PostgreSQL, Snowflake, BigQuery, Vector Databases (Pinecone, ChromaDB)
- Programming: Python, SQL, C++, Bash

PROFESSIONAL EXPERIENCE
Lead Data Scientist | CloudScale Technologies | 2021 - Present
- Architected enterprise generative AI query assistant utilizing PyTorch, LangChain, and AWS SageMaker.
- Deployed real-time inference containers on Kubernetes handling 4,000 requests per minute with <120ms latency.
- Led data science team of 5 engineers across ML lifecycle from exploratory data analysis to production monitoring.

Machine Learning Engineer | Apex AI Labs | 2018 - 2021
- Built transformer-based document classification pipelines with 94.2% accuracy.
- Automated training pipelines using Docker containers and PostgreSQL feature storage.

EDUCATION
M.S. in Computer Science (Machine Learning Concentration) | University of Washington
B.S. in Applied Mathematics | University of Washington`;
                const label = document.getElementById('userResumeDropzoneLabel');
                if (label) label.innerText = 'Sample Resume: Elena Vance (Loaded in text)';
            }
        });
    }

    const dropzone = document.getElementById('userResumeDropzone');
    const fileInput = document.getElementById('userResumeFileInput');
    const btnSelectFile = document.getElementById('btnUserSelectFile');
    const dropzoneLabel = document.getElementById('userResumeDropzoneLabel');

    if (btnSelectFile && fileInput) {
        btnSelectFile.addEventListener('click', () => fileInput.click());
    }

    if (dropzone && fileInput) {
        dropzone.addEventListener('click', () => fileInput.click());

        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.style.borderColor = 'var(--color-accent)';
        });
        dropzone.addEventListener('dragleave', () => {
            dropzone.style.borderColor = 'var(--border-subtle)';
        });
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.style.borderColor = 'var(--border-subtle)';
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                if (dropzoneLabel) dropzoneLabel.innerText = `Selected: ${fileInput.files[0].name}`;
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files && fileInput.files.length > 0 && dropzoneLabel) {
                dropzoneLabel.innerText = `Selected: ${fileInput.files[0].name}`;
            }
        });
    }

    const jdFileInput = document.getElementById('userJdFileInput');
    const btnBrowseJd = document.getElementById('btnUserBrowseJdFile');
    if (btnBrowseJd && jdFileInput) {
        btnBrowseJd.addEventListener('click', () => jdFileInput.click());
        jdFileInput.addEventListener('change', () => {
            if (jdFileInput.files && jdFileInput.files.length > 0) {
                btnBrowseJd.innerText = `Selected: ${jdFileInput.files[0].name}`;
            }
        });
    }

    const btnRun = document.getElementById('btnRunUserAnalysis');
    if (btnRun) {
        btnRun.addEventListener('click', runUserAnalysis);
    }

    const btnDownloadPdf1 = document.getElementById('btnDownloadUserPrepPdf');
    const btnDownloadPdf2 = document.getElementById('btnExportPrepFromQuestions');
    if (btnDownloadPdf1) btnDownloadPdf1.addEventListener('click', exportUserPrepPdf);
    if (btnDownloadPdf2) btnDownloadPdf2.addEventListener('click', exportUserPrepPdf);
}

async function runUserAnalysis() {
    const resumeFileInput = document.getElementById('userResumeFileInput');
    const resumeTextarea = document.getElementById('userResumeTextarea');
    const jdFileInput = document.getElementById('userJdFileInput');
    const jdTextarea = document.getElementById('userJdTextarea');
    const loading = document.getElementById('userAnalysisLoading');
    const btnRun = document.getElementById('btnRunUserAnalysis');

    const hasResumeFile = resumeFileInput && resumeFileInput.files && resumeFileInput.files.length > 0;
    const resumeText = resumeTextarea ? resumeTextarea.value.trim() : '';

    if (!hasResumeFile && !resumeText) {
        alert('Please upload a resume file or paste your resume text to begin analysis.');
        return;
    }

    const hasJdFile = jdFileInput && jdFileInput.files && jdFileInput.files.length > 0;
    const jdText = jdTextarea ? jdTextarea.value.trim() : '';

    if (!hasJdFile && !jdText) {
        alert('Please provide target job requirements by selecting a role or pasting the job description.');
        return;
    }

    if (btnRun) btnRun.disabled = true;
    if (loading) loading.style.display = 'block';

    try {
        const formData = new FormData();
        if (hasResumeFile) {
            formData.append('resume', resumeFileInput.files[0]);
        } else {
            formData.append('resume_text', resumeText);
        }

        if (hasJdFile) {
            formData.append('jd_file', jdFileInput.files[0]);
        } else {
            formData.append('jd_text', jdText);
        }

        const savedKey = localStorage.getItem('gemini_api_key');
        if (savedKey) {
            formData.append('api_key', savedKey);
        }

        const res = await fetch('/api/user-analyze', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (!res.ok || !data.success) {
            throw new Error(data.error || 'Failed to complete qualification analysis.');
        }

        currentUserAnalysisData = data;
        renderUserAnalysis(data);

        const resultsArea = document.getElementById('userResultsArea');
        if (resultsArea) {
            resultsArea.style.display = 'flex';
            resultsArea.scrollIntoView({ behavior: 'smooth' });
        }
    } catch (err) {
        alert(`Analysis Notice: ${err.message}`);
    } finally {
        if (btnRun) btnRun.disabled = false;
        if (loading) loading.style.display = 'none';
        refreshIcons();
    }
}

function renderUserAnalysis(data) {
    const fitVal = document.getElementById('userFitScoreVal');
    if (fitVal) fitVal.innerText = `${data.fit_score}%`;

    const circle = document.getElementById('userScoreCircle');
    if (circle) {
        if (data.fit_score >= 80) {
            circle.style.borderColor = 'var(--color-match)';
            circle.style.background = 'rgba(22, 163, 74, 0.08)';
            if (fitVal) fitVal.style.color = 'var(--color-match)';
        } else if (data.fit_score >= 50) {
            circle.style.borderColor = 'var(--color-partial)';
            circle.style.background = 'rgba(217, 119, 6, 0.08)';
            if (fitVal) fitVal.style.color = 'var(--color-partial)';
        } else {
            circle.style.borderColor = 'var(--color-gap)';
            circle.style.background = 'rgba(220, 38, 38, 0.08)';
            if (fitVal) fitVal.style.color = 'var(--color-gap)';
        }
    }

    const candName = document.getElementById('userCandidateNameDisplay');
    if (candName) candName.innerText = data.candidate_name;

    const targetRole = document.getElementById('userTargetRoleDisplay');
    if (targetRole) targetRole.innerText = `Evaluated against: ${data.job_title}`;

    const confVal = document.getElementById('userConfidenceScoreVal');
    if (confVal) {
        const cScore = data.confidence ? data.confidence.confidence_score : 88;
        confVal.innerText = `${cScore}%`;
    }

    const summaryText = document.getElementById('userExecutiveSummaryText');
    if (summaryText) summaryText.innerText = data.summary;

    const matchCount = document.getElementById('userMatchCount');
    if (matchCount) matchCount.innerText = data.matches ? data.matches.length : 0;

    const partialCount = document.getElementById('userPartialCount');
    if (partialCount) partialCount.innerText = data.partial_matches ? data.partial_matches.length : 0;

    const gapCount = document.getElementById('userGapCount');
    if (gapCount) gapCount.innerText = data.gaps ? data.gaps.length : 0;

    const matchesList = document.getElementById('userMatchesEvidenceList');
    if (matchesList) {
        if (!data.matches || data.matches.length === 0) {
            matchesList.innerHTML = '<div style="font-size: 0.76rem; color: var(--text-muted);">No verified matches found.</div>';
        } else {
            matchesList.innerHTML = data.matches.map(m => `
                <div class="user-evidence-item match">
                    <div style="font-weight: 700; color: var(--text-primary); margin-bottom: 0.2rem;">
                        [MATCH] ${escapeHtml(m.requirement)}
                    </div>
                    <div style="color: var(--text-secondary); font-size: 0.72rem;">
                        <b>Your Evidence:</b> "${escapeHtml(m.candidate_evidence)}"
                    </div>
                </div>
            `).join('');
        }
    }

    const gapsList = document.getElementById('userGapsEvidenceList');
    if (gapsList) {
        if (!data.gaps || data.gaps.length === 0) {
            gapsList.innerHTML = '<div style="font-size: 0.76rem; color: var(--color-match); font-weight: 600;">Outstanding: Zero critical requirement gaps identified.</div>';
        } else {
            gapsList.innerHTML = data.gaps.map(g => `
                <div class="user-evidence-item gap">
                    <div style="font-weight: 700; color: var(--color-gap); margin-bottom: 0.2rem;">
                        [GAP] ${escapeHtml(g.requirement)}
                    </div>
                    <div style="color: var(--text-secondary); font-size: 0.72rem;">
                        <b>Status:</b> ${escapeHtml(g.reason || 'No verifiable evidence detected in submitted resume.')}
                    </div>
                </div>
            `).join('');
        }
    }

    // Populate Tab 2 Full Matches List
    const fullMatchesList = document.getElementById('userFullMatchesList');
    if (fullMatchesList) {
        if (!data.matches || data.matches.length === 0) {
            fullMatchesList.innerHTML = '<div style="font-size: 0.78rem; color: var(--text-muted);">No verified matches detected.</div>';
        } else {
            fullMatchesList.innerHTML = data.matches.map(m => `
                <div class="user-evidence-item match" style="margin-bottom: 0.75rem;">
                    <div style="font-weight: 700; color: var(--text-primary); margin-bottom: 0.25rem;">
                        [MATCH] ${escapeHtml(m.requirement)}
                    </div>
                    <div style="color: var(--text-secondary); font-size: 0.75rem; line-height: 1.45;">
                        <b>Verified Sentence Quote:</b> "${escapeHtml(m.candidate_evidence)}"
                    </div>
                </div>
            `).join('');
        }
    }

    // Populate Tab 3 Full Gaps List
    const fullGapsList = document.getElementById('userFullGapsList');
    if (fullGapsList) {
        if (!data.gaps || data.gaps.length === 0) {
            fullGapsList.innerHTML = '<div style="font-size: 0.78rem; color: var(--color-match); font-weight: 600;">Outstanding: Zero critical requirement gaps identified.</div>';
        } else {
            fullGapsList.innerHTML = data.gaps.map(g => `
                <div class="user-evidence-item gap" style="margin-bottom: 0.75rem;">
                    <div style="font-weight: 700; color: var(--color-gap); margin-bottom: 0.25rem;">
                        [GAP] ${escapeHtml(g.requirement)}
                    </div>
                    <div style="color: var(--text-secondary); font-size: 0.75rem; line-height: 1.45;">
                        <b>Target Deficiency:</b> ${escapeHtml(g.reason || 'No verifiable production evidence identified in resume text.')}
                    </div>
                </div>
            `).join('');
        }
    }

    // Populate Simulator Dropdown
    const selectSimSkill = document.getElementById('selectSimulateSkill');
    if (selectSimSkill) {
        const gapOptions = (data.gaps || []).map(g => `<option value="${escapeHtml(g.requirement)}">${escapeHtml(g.requirement)}</option>`).join('');
        selectSimSkill.innerHTML = '<option value="">Select a missing skill to simulate...</option>' + gapOptions;
    }

    const questionsList = document.getElementById('userInterviewCardsList');
    const heading = document.getElementById('userInterviewHeading');
    const questions = data.questions || [];

    if (heading) {
        heading.innerText = `Tailored Mock Interview Questions (${questions.length} Questions Formulated from Missing Skills)`;
    }

    if (questionsList) {
        if (questions.length === 0) {
            questionsList.innerHTML = '<div style="font-size: 0.8rem; color: var(--text-muted);">No interview questions generated.</div>';
        } else {
            questionsList.innerHTML = questions.map((q, idx) => {
                const qNum = idx + 1;
                const focus = q.missing_skill_focus || q.target_concept || q.missing_skill || 'Technical Competency';
                const cat = q.category || 'Missing Skill Probe';
                const coaching = q.candidate_coaching || 'Acknowledge the gap directly, articulate foundational knowledge, and demonstrate relevant transferable workflows.';
                const qId = q.id || `q_cand_${idx+1}`;
                const escapedQ = escapeHtml(q.question || '').replace(/'/g, "\\'");
                const escapedCat = escapeHtml(cat).replace(/'/g, "\\'");
                const escapedDiff = (q.difficulty || 'Senior').replace(/'/g, "\\'");
                const escapedHint = escapeHtml(q.evaluation_hint || '').replace(/'/g, "\\'");
                const escapedCoach = escapeHtml(coaching).replace(/'/g, "\\'");
                const gapFocus = encodeURIComponent(focus);

                return `
                    <div class="interview-card" id="interviewCard-${qId}" style="border-left: 3px solid #2563EB;">
                        <div class="interview-card-header">
                            <div style="display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap;">
                                <span class="interview-badge" style="background: rgba(37, 99, 235, 0.15); color: #93C5FD; border: 1px solid rgba(37, 99, 235, 0.35);">
                                    [Q${qNum}] ${escapeHtml(cat)}
                                </span>
                            </div>
                            <div class="q-action-toolbar">
                                <button type="button" class="q-action-btn btn-ai-action" id="btnRegen-${qId}" onclick="triggerRegenerateQuestion('${qId}', '${gapFocus}', '${encodeURIComponent(cat)}', true)" title="Regenerate this question with Built-in AI">
                                    <i data-lucide="sparkles" style="width: 11px; height: 11px;"></i> AI Regen
                                </button>
                                <button type="button" class="q-action-btn" onclick="openEditQuestionModal('${qId}', 'candidate_self')" title="Edit Question">
                                    <i data-lucide="edit-3" style="width: 11px; height: 11px;"></i> Edit
                                </button>
                                <button type="button" class="q-action-btn" onclick="copyInterviewQuestion('${encodeURIComponent(q.question)}')">
                                    <i data-lucide="copy" style="width: 11px; height: 11px;"></i> Copy
                                </button>
                            </div>
                        </div>
                        <div class="interview-question-text" id="qTextDisplay-${qId}" style="font-size: 0.84rem; font-weight: 600; line-height: 1.45; color: var(--text-primary); margin: 0.5rem 0;">
                            ${escapeHtml(q.question)}
                        </div>
                        <div style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.5rem;">
                            <b>What Interviewers Probe:</b> ${escapeHtml(q.evaluation_hint || '')}
                        </div>
                        <div class="coaching-callout-box">
                            <div class="coaching-callout-title">
                                <i data-lucide="compass" style="width: 13px; height: 13px;"></i>
                                Candidate Answer Strategy & Coaching Advice
                            </div>
                            <div>${escapeHtml(coaching)}</div>
                        </div>
                    </div>
                `;
            }).join('');
        }
    }

    try { loadOrGenerateCandidateRoadmap(data); } catch(e) { console.error('Roadmap trigger error:', e); }
    try { loadRoleBenchmarks(data.job_title, data.fit_score); } catch(e) { console.error('Benchmark trigger error:', e); }
    try { switchUserTab('overview'); } catch(e) { console.error('Tab switch error:', e); }
}

function switchUserTab(tabName) {
    const tabs = [
        { id: 'overview', btn: 'btnUserTabOverview', pane: 'userPaneOverview' },
        { id: 'matches', btn: 'btnUserTabMatches', pane: 'userPaneMatches' },
        { id: 'gaps', btn: 'btnUserTabGaps', pane: 'userPaneGaps' },
        { id: 'questions', btn: 'btnUserTabQuestions', pane: 'userPaneQuestions' },
        { id: 'roadmap', btn: 'btnUserTabRoadmap', pane: 'userPaneRoadmap' }
    ];

    tabs.forEach(t => {
        const btn = document.getElementById(t.btn);
        const pane = document.getElementById(t.pane);
        if (btn) {
            if (t.id === tabName) btn.classList.add('active');
            else btn.classList.remove('active');
        }
        if (pane) {
            if (t.id === tabName) pane.style.display = 'block';
            else pane.style.display = 'none';
        }
    });

    refreshIcons();
}

async function exportUserPrepPdf() {
    if (!currentUserAnalysisData) {
        alert('Please run a candidate analysis before exporting the preparation guide.');
        return;
    }

    try {
        const res = await fetch('/api/export-user-prep', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentUserAnalysisData)
        });

        if (!res.ok) throw new Error('PDF generation failed on server.');

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const cleanName = (currentUserAnalysisData.candidate_name || 'Candidate').replace(/[^a-zA-Z0-9]/g, '_');
        a.download = `Interview_Prep_${cleanName}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (err) {
        alert(`Export notice: ${err.message}`);
    }
}

// =========================================================================
// AI INTERVIEW PLAN CUSTOMIZER MODAL CONTROLLER
// =========================================================================

function setupInterviewCustomizer() {
    const btnOpenRecruiter = document.getElementById('btnOpenAiCustomizerModal');
    const btnOpenUser = document.getElementById('btnOpenUserAiCustomizer');
    const modal = document.getElementById('aiCustomizerModalOverlay');
    const btnClose = document.getElementById('closeAiCustomizerBtn');
    const btnCancel = document.getElementById('btnCancelAiCustomizer');
    const btnSubmit = document.getElementById('btnSubmitAiCustomizer');

    const openCustomizer = (candId) => {
        if (!modal) return;
        const hiddenId = document.getElementById('customizerCandidateId');
        if (hiddenId) hiddenId.value = candId;
        const statusBox = document.getElementById('customizerStatus');
        if (statusBox) statusBox.style.display = 'none';

        // Preload saved API key from localStorage
        const keyInput = document.getElementById('customizerApiKey');
        const savedKey = localStorage.getItem('gemini_api_key');
        if (keyInput && savedKey && !keyInput.value) {
            keyInput.value = savedKey;
        }

        modal.classList.add('active');
        refreshIcons();
    };

    if (btnOpenRecruiter) {
        btnOpenRecruiter.addEventListener('click', () => {
            const candId = currentActiveCandidate ? currentActiveCandidate.id : '';
            openCustomizer(candId);
        });
    }

    if (btnOpenUser) {
        btnOpenUser.addEventListener('click', () => {
            openCustomizer('candidate_self');
        });
    }

    const closeModal = () => {
        if (modal) modal.classList.remove('active');
    };

    if (btnClose) btnClose.addEventListener('click', closeModal);
    if (btnCancel) btnCancel.addEventListener('click', closeModal);

    if (btnSubmit) {
        btnSubmit.addEventListener('click', async () => {
            const candId = document.getElementById('customizerCandidateId')?.value || '';
            const difficulty = document.getElementById('customizerDifficulty')?.value || 'Senior';
            const count = parseInt(document.getElementById('customizerCount')?.value || '10');
            const directives = document.getElementById('customizerDirectives')?.value || '';
            const apiKey = document.getElementById('customizerApiKey')?.value || '';

            // Persist API key locally and sync with backend
            if (apiKey) {
                localStorage.setItem('gemini_api_key', apiKey);
                fetch('/api/v1/config/gemini-key', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ api_key: apiKey })
                }).catch(e => console.log('API key sync notice:', e));
            }

            const statusBox = document.getElementById('customizerStatus');
            if (statusBox) {
                statusBox.style.display = 'block';
                statusBox.style.color = '#93C5FD';
                statusBox.innerText = apiKey ? 'Synthesizing questions via Google Gemini AI...' : 'Synthesizing customized questions with Built-in AI...';
            }

            const targetCandidateId = (candId === 'candidate_self') ? 
                (currentActiveCandidate ? currentActiveCandidate.id : 'cand-elena') : candId;

            try {
                const res = await fetch('/api/v1/interview/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        candidate_id: targetCandidateId,
                        difficulty: difficulty,
                        count: count,
                        custom_directives: directives,
                        api_key: apiKey
                    })
                });
                const data = await res.json();
                if (data.success && data.questions) {
                    if (candId === 'candidate_self') {
                        if (currentUserAnalysisData) {
                            currentUserAnalysisData.questions = data.questions;
                            renderUserInterviewQuestions(currentUserAnalysisData);
                        }
                    } else if (currentActiveCandidate && currentActiveCandidate.analysis) {
                        currentActiveCandidate.analysis.mock_interview = data.questions;
                        renderMockInterview(data.questions);
                    }
                    closeModal();
                } else {
                    if (statusBox) {
                        statusBox.style.color = 'var(--color-gap)';
                        statusBox.innerText = data.error || 'Failed to synthesize questions.';
                    }
                }
            } catch (err) {
                console.error('Customizer error:', err);
                if (statusBox) {
                    statusBox.style.color = 'var(--color-gap)';
                    statusBox.innerText = 'Connection error communicating with server.';
                }
            }
        });
    }
}

// =========================================================================
// IN-PLACE QUESTION EDIT MODAL CONTROLLER
// =========================================================================

function setupQuestionEditModal() {
    const modal = document.getElementById('editQuestionModalOverlay');
    const btnClose = document.getElementById('closeEditQuestionBtn');
    const btnCancel = document.getElementById('btnCancelEditQuestion');
    const btnSave = document.getElementById('btnSaveEditQuestion');

    const closeModal = () => {
        if (modal) modal.classList.remove('active');
    };

    if (btnClose) btnClose.addEventListener('click', closeModal);
    if (btnCancel) btnCancel.addEventListener('click', closeModal);

    if (btnSave) {
        btnSave.addEventListener('click', async () => {
            const qId = document.getElementById('editQuestionId')?.value || '';
            const candId = document.getElementById('editQuestionCandidateId')?.value || '';
            const text = document.getElementById('editQuestionText')?.value || '';
            const cat = document.getElementById('editQuestionCategory')?.value || '';
            const diff = document.getElementById('editQuestionDifficulty')?.value || 'Senior';
            const hint = document.getElementById('editQuestionHint')?.value || '';
            const coach = document.getElementById('editQuestionCoaching')?.value || '';

            if (text.trim().length < 5) {
                alert('Question text must be at least 5 characters.');
                return;
            }

            try {
                const res = await fetch(`/api/v1/interview/questions/${qId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        candidate_id: candId,
                        question_text: text,
                        category: cat,
                        difficulty: diff,
                        evaluation_hint: hint,
                        candidate_coaching: coach
                    })
                });
                const data = await res.json();
                if (data.success) {
                    // Update DOM element directly or re-render
                    if (candId === 'candidate_self' && currentUserAnalysisData) {
                        const qObj = (currentUserAnalysisData.questions || []).find(q => String(q.id) === String(qId));
                        if (qObj) {
                            qObj.question = text;
                            qObj.category = cat;
                            qObj.difficulty = diff;
                            qObj.evaluation_hint = hint;
                            qObj.candidate_coaching = coach;
                            qObj.is_custom = 1;
                        }
                        renderUserInterviewQuestions(currentUserAnalysisData);
                    } else if (currentActiveCandidate && currentActiveCandidate.analysis) {
                        const qObj = (currentActiveCandidate.analysis.mock_interview || []).find(q => String(q.id) === String(qId) || String(q.id) === String(qId.replace('q_', '')));
                        if (qObj) {
                            qObj.question = text;
                            qObj.category = cat;
                            qObj.difficulty = diff;
                            qObj.evaluation_hint = hint;
                            qObj.candidate_coaching = coach;
                            qObj.is_custom = 1;
                        }
                        renderMockInterview(currentActiveCandidate.analysis.mock_interview);
                    }
                    closeModal();
                } else {
                    alert(data.error || 'Failed to save question.');
                }
            } catch (err) {
                console.error('Error saving question edit:', err);
                alert('Failed to connect to server.');
            }
        });
    }
}

function openEditQuestionModal(qId, candId, text, cat, diff, hint, coach) {
    const modal = document.getElementById('editQuestionModalOverlay');
    if (!modal) return;

    let qObj = null;
    if (currentActiveCandidate && currentActiveCandidate.analysis && currentActiveCandidate.analysis.mock_interview) {
        qObj = currentActiveCandidate.analysis.mock_interview.find(q => String(q.id) === String(qId) || String(q.id) === String(qId.replace('q_', '')));
    }
    if (!qObj && currentUserAnalysisData && currentUserAnalysisData.questions) {
        qObj = currentUserAnalysisData.questions.find(q => String(q.id) === String(qId) || String(q.id) === String(qId.replace('q_', '')));
    }

    document.getElementById('editQuestionId').value = qId || '';
    document.getElementById('editQuestionCandidateId').value = candId || (currentActiveCandidate ? currentActiveCandidate.id : 'candidate_self');
    document.getElementById('editQuestionText').value = (qObj ? (qObj.question || qObj.question_text) : text) || '';
    document.getElementById('editQuestionCategory').value = (qObj ? qObj.category : cat) || '';
    document.getElementById('editQuestionDifficulty').value = (qObj ? qObj.difficulty : diff) || 'Senior';
    document.getElementById('editQuestionHint').value = (qObj ? qObj.evaluation_hint : hint) || '';
    document.getElementById('editQuestionCoaching').value = (qObj ? qObj.candidate_coaching : coach) || '';

    modal.classList.add('active');
    refreshIcons();
}

// =========================================================================
// FEATURE 1: SMART INTERVIEW SCHEDULING (GOOGLE CALENDAR / MEET)
// =========================================================================

let currentActiveInterview = null;
let selectedInterviewSlotIso = '';

function setupInterviewScheduling() {
    const btnOpenModal = document.getElementById('btnOpenScheduleInterviewModal');
    const modal = document.getElementById('modalScheduleInterview');
    const btnClose = document.getElementById('closeScheduleInterviewBtn');
    const btnCancel = document.getElementById('btnCancelScheduleInterview');
    const btnConfirm = document.getElementById('btnConfirmScheduleInterview');
    const dateInput = document.getElementById('scheduleInterviewDate');
    const durationSelect = document.getElementById('scheduleInterviewDuration');
    const btnRefreshSlots = document.getElementById('btnRefreshSlots');

    if (btnOpenModal) {
        btnOpenModal.addEventListener('click', () => {
            if (!currentActiveCandidate) {
                alert('Please select a candidate to schedule an interview.');
                return;
            }
            openScheduleInterviewModal(currentActiveCandidate);
        });
    }

    const closeModal = () => {
        if (modal) modal.classList.remove('active');
    };

    if (btnClose) btnClose.addEventListener('click', closeModal);
    if (btnCancel) btnCancel.addEventListener('click', closeModal);

    if (dateInput) {
        dateInput.addEventListener('change', () => {
            fetchAndRenderAvailableSlots();
        });
    }

    if (durationSelect) {
        durationSelect.addEventListener('change', () => {
            fetchAndRenderAvailableSlots();
        });
    }

    if (btnRefreshSlots) {
        btnRefreshSlots.addEventListener('click', () => {
            fetchAndRenderAvailableSlots();
        });
    }

    if (btnConfirm) {
        btnConfirm.addEventListener('click', async () => {
            const candId = document.getElementById('scheduleCandidateId')?.value || '';
            const selectedIso = document.getElementById('scheduleSelectedIso')?.value || selectedInterviewSlotIso;
            const duration = parseInt(document.getElementById('scheduleInterviewDuration')?.value || '45');
            const notes = document.getElementById('scheduleNotes')?.value || '';

            if (!candId) {
                alert('Candidate ID is missing.');
                return;
            }

            if (!selectedIso) {
                alert('Please select an available interview slot time before confirming.');
                return;
            }

            btnConfirm.disabled = true;
            btnConfirm.innerHTML = '<i data-lucide="loader" style="width: 14px; height: 14px;"></i> Scheduling Event...';
            refreshIcons();

            try {
                const res = await fetch('/api/v1/interviews', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        candidate_id: candId,
                        scheduled_at: selectedIso,
                        duration_minutes: duration,
                        notes: notes,
                        include_ai_questions: true
                    })
                });

                const data = await res.json();
                if (!res.ok || !data.success) {
                    throw new Error(data.error || 'Failed to schedule interview.');
                }

                alert(`Interview scheduled successfully!\n\nGoogle Meet Link: ${data.interview.meeting_link}\nGoogle Calendar Event ID: ${data.interview.calendar_event_id}\n\nCandidate-specific AI questions and rubrics have been automatically embedded in the calendar invite.`);
                closeModal();
                checkCandidateScheduledInterview(candId);
            } catch (err) {
                console.error('Scheduling error:', err);
                alert(`Scheduling Notice: ${err.message}`);
            } finally {
                btnConfirm.disabled = false;
                btnConfirm.innerHTML = '<i data-lucide="calendar-check" style="width: 14px; height: 14px;"></i> Confirm & Schedule Interview';
                refreshIcons();
            }
        });
    }

    setupFeedbackModal();
    setupBannerActionButtons();
}

function openScheduleInterviewModal(candidate) {
    const modal = document.getElementById('modalScheduleInterview');
    if (!modal) return;

    document.getElementById('scheduleCandidateId').value = candidate.id;
    const nameEl = document.getElementById('scheduleCandidateNameDisplay');
    if (nameEl) nameEl.innerText = candidate.name || 'Candidate';

    const jobEl = document.getElementById('scheduleJobTitleDisplay');
    const jobTitle = (candidate.analysis && candidate.analysis.job_title) ? candidate.analysis.job_title : 'Senior Technical Role';
    if (jobEl) jobEl.innerText = `Target Role: ${jobTitle}`;

    // Set default date to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const dateStr = tomorrow.toISOString().split('T')[0];
    const dateInput = document.getElementById('scheduleInterviewDate');
    if (dateInput) dateInput.value = dateStr;

    // Reset selected slot
    selectedInterviewSlotIso = '';
    const hiddenIso = document.getElementById('scheduleSelectedIso');
    if (hiddenIso) hiddenIso.value = '';

    modal.classList.add('active');
    refreshIcons();

    checkCalendarStatusAndFetchSlots();
}

async function checkCalendarStatusAndFetchSlots() {
    const badge = document.getElementById('calendarIntegrationBadge');
    try {
        const res = await fetch('/api/v1/calendar/status');
        const data = await res.json();

        if (data.connected) {
            if (badge) {
                badge.className = 'match-pill match';
                badge.innerHTML = `<i data-lucide="check" style="width: 10px; height: 10px;"></i> Google Calendar Connected (${escapeHtml(data.email || 'Recruiter')})`;
            }
        } else {
            const connRes = await fetch('/api/v1/calendar/sandbox-connect', { method: 'POST' });
            const connData = await connRes.json();
            if (connData.success && badge) {
                badge.className = 'match-pill match';
                badge.innerHTML = `<i data-lucide="check" style="width: 10px; height: 10px;"></i> Google Calendar Connected (${escapeHtml(connData.email)})`;
            }
        }
    } catch (err) {
        console.error('Calendar status error:', err);
    }

    fetchAndRenderAvailableSlots();
}

async function fetchAndRenderAvailableSlots() {
    const slotsList = document.getElementById('scheduleSlotsList');
    const dateInput = document.getElementById('scheduleInterviewDate');
    const durationSelect = document.getElementById('scheduleInterviewDuration');
    const meetPreview = document.getElementById('scheduleMeetPreviewText');

    if (!slotsList) return;

    const targetDate = dateInput ? dateInput.value : '';
    const duration = durationSelect ? durationSelect.value : '45';

    if (!targetDate) {
        slotsList.innerHTML = '<span style="font-size: 0.75rem; color: var(--text-muted);">Please select a valid date.</span>';
        return;
    }

    slotsList.innerHTML = '<span style="font-size: 0.75rem; color: var(--text-muted);">Scanning recruiter calendar for available openings...</span>';

    try {
        const res = await fetch(`/api/v1/interviews/available-slots?date=${targetDate}&duration=${duration}`);
        const data = await res.json();

        if (!data.success || !data.slots || data.slots.length === 0) {
            slotsList.innerHTML = '<span style="font-size: 0.75rem; color: var(--color-gap);">No open slots found on this date. Please try another day.</span>';
            return;
        }

        slotsList.innerHTML = data.slots.map((slot, idx) => {
            const isFirst = idx === 0;
            return `
                <div class="slot-chip ${isFirst ? 'active' : ''}" data-iso="${slot.start_iso}" onclick="selectInterviewSlot(this, '${slot.start_iso}', '${slot.meet_preview || ''}')">
                    <i data-lucide="clock" style="width: 11px; height: 11px;"></i>
                    <span>${slot.formatted_time}</span>
                </div>
            `;
        }).join('');

        if (data.slots.length > 0) {
            const first = data.slots[0];
            selectedInterviewSlotIso = first.start_iso;
            const hiddenIso = document.getElementById('scheduleSelectedIso');
            if (hiddenIso) hiddenIso.value = first.start_iso;

            if (meetPreview) {
                meetPreview.innerText = first.meet_preview || 'https://meet.google.com/hlo-recr-mtg';
            }
        }

        refreshIcons();
    } catch (err) {
        console.error('Fetch slots error:', err);
        slotsList.innerHTML = '<span style="font-size: 0.75rem; color: var(--color-gap);">Failed to query calendar slots.</span>';
    }
}

function selectInterviewSlot(el, isoString, meetUrl) {
    document.querySelectorAll('#scheduleSlotsList .slot-chip').forEach(c => c.classList.remove('active'));
    el.classList.add('active');
    selectedInterviewSlotIso = isoString;
    const hiddenIso = document.getElementById('scheduleSelectedIso');
    if (hiddenIso) hiddenIso.value = isoString;

    const meetPreview = document.getElementById('scheduleMeetPreviewText');
    if (meetPreview && meetUrl) {
        meetPreview.innerText = meetUrl;
    }
}

async function checkCandidateScheduledInterview(candId) {
    const banner = document.getElementById('candidateInterviewScheduleBanner');
    if (!banner) return;

    try {
        const res = await fetch(`/api/v1/interviews?candidate_id=${candId}`);
        if (!res.ok) {
            banner.style.display = 'none';
            return;
        }
        const data = await res.json();

        if (data.success && data.interviews && data.interviews.length > 0) {
            const interview = data.interviews[0];
            currentActiveInterview = interview;

            banner.style.display = 'block';

            const badge = document.getElementById('bannerInterviewStatusBadge');
            if (badge) {
                badge.innerText = interview.status.toUpperCase();
                if (interview.status === 'scheduled' || interview.status === 'rescheduled') {
                    badge.className = 'match-pill match';
                } else if (interview.status === 'completed') {
                    badge.className = 'match-pill';
                    badge.style.background = 'rgba(37, 99, 235, 0.2)';
                    badge.style.color = '#93C5FD';
                } else {
                    badge.className = 'match-pill gap';
                }
            }

            const timeText = document.getElementById('bannerInterviewTimeText');
            if (timeText) {
                let formattedTime = interview.scheduled_at;
                try {
                    const d = new Date(interview.scheduled_at);
                    formattedTime = d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' }) + ' at ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
                } catch(e) {}
                timeText.innerHTML = `<b>${formattedTime}</b> (${interview.duration_minutes} mins) &bull; Interviewer: ${escapeHtml(interview.interviewer_email || 'HR Assessor')}`;
            }

            const meetBtn = document.getElementById('bannerBtnJoinMeet');
            if (meetBtn) {
                meetBtn.href = interview.meeting_link || '#';
            }

            const summaryArea = document.getElementById('bannerFeedbackSummaryArea');
            const summaryContent = document.getElementById('bannerFeedbackSummaryContent');
            if (summaryArea && summaryContent) {
                if (interview.ai_summary) {
                    summaryArea.style.display = 'block';
                    summaryContent.innerText = interview.ai_summary;
                } else if (interview.rating) {
                    summaryArea.style.display = 'block';
                    summaryContent.innerText = `Assessor Rating: ${interview.rating} / 5.0\nNotes: ${interview.notes || 'No detailed notes provided.'}`;
                } else {
                    summaryArea.style.display = 'none';
                }
            }
        } else {
            currentActiveInterview = null;
            banner.style.display = 'none';
        }
    } catch (err) {
        console.error('Error checking interview status:', err);
    }
}

function setupBannerActionButtons() {
    const btnReminder = document.getElementById('bannerBtnSendReminder');
    const btnReschedule = document.getElementById('bannerBtnReschedule');
    const btnFeedback = document.getElementById('bannerBtnFeedback');
    const btnCancel = document.getElementById('bannerBtnCancel');

    if (btnReminder) {
        btnReminder.addEventListener('click', async () => {
            if (!currentActiveInterview) return;
            try {
                const res = await fetch(`/api/v1/interviews/${currentActiveInterview.id}/reminder`, { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    alert(`Candidate notification dispatched!\n\nEmail: ${data.notification.recipient}\nReminder Count: ${data.notification.reminder_count}\nCalendar Event: ${data.notification.calendar_event_id}`);
                } else {
                    alert(`Failed to send reminder: ${data.error}`);
                }
            } catch (err) {
                alert(`Error: ${err.message}`);
            }
        });
    }

    if (btnReschedule) {
        btnReschedule.addEventListener('click', () => {
            if (!currentActiveInterview || !currentActiveCandidate) return;
            openScheduleInterviewModal(currentActiveCandidate);
        });
    }

    if (btnCancel) {
        btnCancel.addEventListener('click', async () => {
            if (!currentActiveInterview) return;
            const confirmCancel = confirm('Are you sure you want to cancel this scheduled interview? This will update the status and notify all attendees.');
            if (!confirmCancel) return;

            const reason = prompt('Optional reason for cancellation:', 'Scheduling conflict');
            try {
                const res = await fetch(`/api/v1/interviews/${currentActiveInterview.id}/cancel`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ reason: reason || 'Cancelled by recruiter' })
                });
                const data = await res.json();
                if (data.success) {
                    alert('Interview has been cancelled.');
                    if (currentActiveCandidate) checkCandidateScheduledInterview(currentActiveCandidate.id);
                } else {
                    alert(`Cancel failed: ${data.error}`);
                }
            } catch (err) {
                alert(`Error: ${err.message}`);
            }
        });
    }

    if (btnFeedback) {
        btnFeedback.addEventListener('click', () => {
            if (!currentActiveInterview) return;
            openFeedbackModal(currentActiveInterview);
        });
    }
}

function setupFeedbackModal() {
    const modal = document.getElementById('modalInterviewFeedback');
    const btnClose = document.getElementById('closeFeedbackModalBtn');
    const btnCancel = document.getElementById('btnCancelFeedback');
    const btnSubmit = document.getElementById('btnSubmitFeedbackConfirm');

    const closeModal = () => {
        if (modal) modal.classList.remove('active');
    };

    if (btnClose) btnClose.addEventListener('click', closeModal);
    if (btnCancel) btnCancel.addEventListener('click', closeModal);

    if (btnSubmit) {
        btnSubmit.addEventListener('click', async () => {
            const intId = document.getElementById('feedbackInterviewId')?.value || (currentActiveInterview ? currentActiveInterview.id : '');
            const rating = parseFloat(document.getElementById('feedbackRatingSelect')?.value || '4.0');
            const notes = document.getElementById('feedbackNotesText')?.value || '';

            if (!intId) {
                alert('No active interview identified for evaluation.');
                return;
            }

            btnSubmit.disabled = true;
            btnSubmit.innerHTML = '<i data-lucide="loader" style="width: 14px; height: 14px;"></i> Formulating AI Summary...';
            refreshIcons();

            try {
                const res = await fetch(`/api/v1/interviews/${intId}/feedback`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ rating: rating, notes: notes })
                });
                const data = await res.json();

                if (!res.ok || !data.success) {
                    throw new Error(data.error || 'Failed to submit feedback.');
                }

                alert(`Interview feedback saved successfully!\n\nAI Executive Summary:\n${data.ai_summary}`);
                closeModal();
                if (currentActiveCandidate) checkCandidateScheduledInterview(currentActiveCandidate.id);
            } catch (err) {
                console.error('Feedback error:', err);
                alert(`Feedback Submission Notice: ${err.message}`);
            } finally {
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = '<i data-lucide="sparkles" style="width: 14px; height: 14px;"></i> Submit & Formulate AI Summary';
                refreshIcons();
            }
        });
    }
}

function openFeedbackModal(interview) {
    const modal = document.getElementById('modalInterviewFeedback');
    if (!modal) return;

    document.getElementById('feedbackInterviewId').value = interview.id;
    if (interview.rating) {
        document.getElementById('feedbackRatingSelect').value = String(interview.rating);
    }
    if (interview.notes) {
        document.getElementById('feedbackNotesText').value = interview.notes;
    }

    modal.classList.add('active');
    refreshIcons();
}

// =========================================================================
// FEATURE 2: AI CAREER ROADMAP & ROLE BENCHMARKS
// =========================================================================

let currentCandidateRoadmap = null;
let currentCandidateRoadmapItems = [];

function setupCandidateRoadmap() {
    const btnReassess = document.getElementById('btnReassessRoadmap');
    if (btnReassess) {
        btnReassess.addEventListener('click', () => {
            if (!currentUserAnalysisData) {
                alert('Please run a candidate self-assessment first.');
                return;
            }
            btnReassess.disabled = true;
            btnReassess.innerHTML = '<i data-lucide="refresh-cw" style="width: 13px; height: 13px;"></i> Re-Assessing...';
            refreshIcons();
            loadOrGenerateCandidateRoadmap(currentUserAnalysisData, true).finally(() => {
                btnReassess.disabled = false;
                btnReassess.innerHTML = '<i data-lucide="refresh-cw" style="width: 13px; height: 13px;"></i> Re-Assess Plan';
                refreshIcons();
            });
        });
    }

    const btnSimulate = document.getElementById('btnRunSkillSimulation');
    if (btnSimulate) {
        btnSimulate.addEventListener('click', runSkillSimulation);
    }

    const btnExportFromQuestions = document.getElementById('btnExportPrepFromQuestions');
    if (btnExportFromQuestions) {
        btnExportFromQuestions.addEventListener('click', exportUserPrepPdf);
    }
}

async function loadOrGenerateCandidateRoadmap(analysisData, forceRegenerate = false) {
    if (!analysisData) return;

    const candName = analysisData.candidate_name || 'candidate';
    const cleanCandId = 'cand_self_' + candName.toLowerCase().replace(/[^a-z0-9]/g, '_');

    try {
        const res = await fetch('/api/v1/roadmaps/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                candidate_id: cleanCandId,
                candidate_name: candName,
                job_title: analysisData.job_title || 'Technical Role',
                fit_score: analysisData.fit_score || 0,
                gaps: analysisData.gaps || [],
                partial_matches: analysisData.partial_matches || []
            })
        });

        const data = await res.json();
        if (data.success && data.roadmap && data.items) {
            currentCandidateRoadmap = data.roadmap;
            currentCandidateRoadmapItems = data.items;
            renderRoadmap(data.roadmap, data.items);
        }
    } catch (err) {
        console.error('Error generating roadmap:', err);
    }
}

function renderRoadmap(roadmap, items) {
    const baselineEl = document.getElementById('roadmapBaselineVal');
    if (baselineEl) baselineEl.innerText = `${roadmap.baseline_score}%`;

    const readinessEl = document.getElementById('roadmapCurrentReadinessVal');
    if (readinessEl) readinessEl.innerText = `${roadmap.current_readiness}%`;

    const completedItems = items.filter(it => it.is_completed === 1);
    const milestonesEl = document.getElementById('roadmapMilestonesDoneVal');
    if (milestonesEl) milestonesEl.innerText = `${completedItems.length} / ${items.length}`;

    const remainingItems = items.filter(it => it.is_completed === 0);
    const totalRemainingHours = remainingItems.reduce((acc, it) => acc + (it.estimated_hours || 0), 0);
    const hoursEl = document.getElementById('roadmapHoursVal');
    if (hoursEl) hoursEl.innerText = `${totalRemainingHours} hrs`;

    // Progress Bar
    const progressFill = document.getElementById('roadmapProgressBarFill');
    const progressText = document.getElementById('roadmapProgressPctText');
    const completionPct = items.length > 0 ? Math.round((completedItems.length / items.length) * 100) : 0;
    if (progressFill) progressFill.style.width = `${completionPct}%`;
    if (progressText) progressText.innerText = `${completionPct}% Complete (${roadmap.current_readiness}% Projected Readiness)`;

    // Role text
    const roleText = document.getElementById('roadmapTargetRoleText');
    if (roleText) roleText.innerText = `3-Phase progression formulated directly for ${escapeHtml(roadmap.target_role)} to bridge requirement gaps.`;

    // PDF Download Link
    const pdfLink = document.getElementById('btnDownloadRoadmapPdf');
    if (pdfLink) {
        pdfLink.href = `/api/v1/roadmaps/${roadmap.id}/export-pdf`;
        pdfLink.setAttribute('download', `Career_Roadmap_${roadmap.id}.pdf`);
    }

    // Render Phases & Milestones
    const phasesContainer = document.getElementById('roadmapPhasesList');
    if (!phasesContainer) return;

    const phases = [
        {
            num: 1,
            title: 'Phase 1: Foundational Core',
            badgeClass: 'phase-badge-foundational',
            badgeText: 'FOUNDATIONAL CORE (0 - 30 DAYS)',
            desc: 'System fundamentals, language semantics, and architecture prerequisites required for target baseline competency.'
        },
        {
            num: 2,
            title: 'Phase 2: Applied Engineering',
            badgeClass: 'phase-badge-applied',
            badgeText: 'APPLIED ENGINEERING (30 - 60 DAYS)',
            desc: 'Production-grade pipelines, frameworks, cloud orchestration, and end-to-end hands-on project implementation.'
        },
        {
            num: 3,
            title: 'Phase 3: Interview-Ready Mastery',
            badgeClass: 'phase-badge-interview',
            badgeText: 'INTERVIEW-READY MASTERY (60 - 90 DAYS)',
            desc: 'System design trade-offs, edge-case troubleshooting, live coding execution, and technical interview rubrics.'
        }
    ];

    phasesContainer.innerHTML = phases.map(phase => {
        const phaseItems = items.filter(it => it.phase_number === phase.num);
        const phaseHours = phaseItems.reduce((acc, it) => acc + (it.estimated_hours || 0), 0);
        const phaseDone = phaseItems.filter(it => it.is_completed === 1).length;

        return `
            <div class="roadmap-phase-card">
                <div class="roadmap-phase-header">
                    <div>
                        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                            <span class="${phase.badgeClass}">${phase.badgeText}</span>
                            <span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">${phaseDone} / ${phaseItems.length} Done</span>
                        </div>
                        <h4 style="font-size: 0.98rem; font-weight: 700; color: var(--text-primary); margin: 0;">${phase.title}</h4>
                        <div style="font-size: 0.74rem; color: var(--text-muted); margin-top: 0.25rem;">${phase.desc}</div>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 0.72rem; color: var(--text-muted);">Phase Load</span>
                        <div style="font-size: 0.95rem; font-weight: 700; color: #60A5FA;">${phaseHours} hrs</div>
                    </div>
                </div>

                <div class="milestones-list">
                    ${phaseItems.map(it => {
                        const isDone = it.is_completed === 1;
                        let priorityClass = 'priority-pill-medium';
                        if (it.priority === 'CRITICAL') priorityClass = 'priority-pill-critical';
                        else if (it.priority === 'HIGH') priorityClass = 'priority-pill-high';

                        return `
                            <div class="milestone-item-card ${isDone ? 'completed' : ''}" id="milestoneCard-${it.id}">
                                <div style="display: flex; align-items: flex-start; gap: 0.75rem;">
                                    <div style="padding-top: 0.15rem;">
                                        <input type="checkbox" class="milestone-checkbox" id="chkMilestone-${it.id}" ${isDone ? 'checked' : ''} onchange="toggleMilestoneItem(${it.id})">
                                    </div>
                                    <div style="flex: 1;">
                                        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 0.25rem;">
                                            <div style="display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap;">
                                                <span style="font-size: 0.84rem; font-weight: 700; color: ${isDone ? 'var(--color-match)' : 'var(--text-primary)'}; ${isDone ? 'text-decoration: line-through; opacity: 0.85;' : ''}" id="mTitle-${it.id}">
                                                    ${escapeHtml(it.title)}
                                                </span>
                                                <span class="${priorityClass}">[${it.priority}]</span>
                                                <span style="font-size: 0.65rem; color: #93C5FD; background: rgba(37,99,235,0.1); border: 1px solid rgba(37,99,235,0.25); padding: 0.12rem 0.4rem; border-radius: var(--radius-sm);">
                                                    ${escapeHtml(it.resource_type || 'Guided Practice')}
                                                </span>
                                            </div>
                                            <div style="display: flex; align-items: center; gap: 0.6rem; font-size: 0.74rem;">
                                                <span style="color: var(--text-muted); font-family: var(--font-mono);">${it.estimated_hours} hrs</span>
                                                <span style="color: var(--color-match); font-weight: 700;">+${it.readiness_impact_pct}% Readiness</span>
                                            </div>
                                        </div>

                                        <div style="font-size: 0.76rem; color: var(--text-secondary); line-height: 1.45; margin-bottom: 0.4rem;">
                                            ${escapeHtml(it.description || '')}
                                        </div>

                                        ${it.prerequisites ? `
                                            <div style="font-size: 0.7rem; color: var(--text-muted); margin-bottom: 0.35rem;">
                                                <b>Prerequisites:</b> ${escapeHtml(it.prerequisites)}
                                            </div>
                                        ` : ''}

                                        <!-- Expandable Rationale -->
                                        <details class="why-recommendation-details">
                                            <summary>Why this recommendation?</summary>
                                            <p style="margin: 0.35rem 0 0 0; line-height: 1.4;">${escapeHtml(it.rationale || 'Directly addresses identified requirement gap to elevate candidate profile to target proficiency.')}</p>
                                        </details>
                                    </div>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }).join('');

    refreshIcons();
}

async function toggleMilestoneItem(itemId) {
    try {
        const res = await fetch(`/api/v1/roadmaps/items/${itemId}/toggle`, { method: 'PATCH' });
        const data = await res.json();

        if (data.success) {
            const item = currentCandidateRoadmapItems.find(it => it.id === itemId);
            if (item) item.is_completed = data.is_completed;
            if (currentCandidateRoadmap) currentCandidateRoadmap.current_readiness = data.current_readiness;

            const card = document.getElementById(`milestoneCard-${itemId}`);
            const title = document.getElementById(`mTitle-${itemId}`);
            if (card) {
                if (data.is_completed === 1) {
                    card.classList.add('completed');
                    if (title) {
                        title.style.color = 'var(--color-match)';
                        title.style.textDecoration = 'line-through';
                        title.style.opacity = '0.85';
                    }
                } else {
                    card.classList.remove('completed');
                    if (title) {
                        title.style.color = 'var(--text-primary)';
                        title.style.textDecoration = 'none';
                        title.style.opacity = '1';
                    }
                }
            }

            const readinessEl = document.getElementById('roadmapCurrentReadinessVal');
            if (readinessEl) readinessEl.innerText = `${data.current_readiness}%`;

            const completedCount = currentCandidateRoadmapItems.filter(it => it.is_completed === 1).length;
            const milestonesEl = document.getElementById('roadmapMilestonesDoneVal');
            if (milestonesEl) milestonesEl.innerText = `${completedCount} / ${currentCandidateRoadmapItems.length}`;

            const remainingHours = currentCandidateRoadmapItems.filter(it => it.is_completed === 0).reduce((a, b) => a + (b.estimated_hours || 0), 0);
            const hoursEl = document.getElementById('roadmapHoursVal');
            if (hoursEl) hoursEl.innerText = `${remainingHours} hrs`;

            const completionPct = Math.round((completedCount / currentCandidateRoadmapItems.length) * 100);
            const progressFill = document.getElementById('roadmapProgressBarFill');
            const progressText = document.getElementById('roadmapProgressPctText');
            if (progressFill) progressFill.style.width = `${completionPct}%`;
            if (progressText) progressText.innerText = `${completionPct}% Complete (${data.current_readiness}% Projected Readiness)`;
        }
    } catch (err) {
        console.error('Toggle error:', err);
    }
}

async function loadRoleBenchmarks(jobTitle, candidateScore) {
    const container = document.getElementById('benchmarkContentArea');
    if (!container) return;

    container.innerHTML = '<div style="font-size: 0.78rem; color: var(--text-muted);">Evaluating statistical benchmarks...</div>';

    try {
        const res = await fetch(`/api/v1/benchmarks?job_title=${encodeURIComponent(jobTitle)}&candidate_score=${candidateScore}`);
        const data = await res.json();

        if (data.status === 'insufficient_data') {
            container.innerHTML = `
                <div style="background: rgba(217, 119, 6, 0.08); border: 1px solid rgba(217, 119, 6, 0.25); padding: 0.75rem 1rem; border-radius: var(--radius-sm);">
                    <div style="font-size: 0.8rem; font-weight: 700; color: #FBBF24; margin-bottom: 0.2rem; display: flex; align-items: center; gap: 0.4rem;">
                        <i data-lucide="shield-alert" style="width: 14px; height: 14px;"></i> Not enough data (minimum 20 candidates required to calculate anonymized statistical percentiles)
                    </div>
                    <div style="font-size: 0.74rem; color: var(--text-secondary); line-height: 1.45;">
                        Current role cohort size: <b>${data.sample_size} candidates</b> (Threshold: 20). Zero individual candidate identities, scores, or names are exposed to preserve privacy.
                    </div>
                </div>
            `;
        } else if (data.status === 'active') {
            const topPct = 100 - data.percentile;
            container.innerHTML = `
                <div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.85rem; margin-bottom: 0.85rem;">
                        <div style="background: var(--bg-tertiary); padding: 0.65rem 0.85rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                            <div style="font-size: 0.68rem; color: var(--text-muted);">Cohort Pool</div>
                            <div style="font-size: 1.1rem; font-weight: 800; color: var(--text-primary); font-family: var(--font-mono);">N = ${data.sample_size}</div>
                        </div>
                        <div style="background: var(--bg-tertiary); padding: 0.65rem 0.85rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                            <div style="font-size: 0.68rem; color: var(--text-muted);">Candidate Percentile</div>
                            <div style="font-size: 1.1rem; font-weight: 800; color: #60A5FA; font-family: var(--font-mono);">Top ${topPct}%</div>
                        </div>
                        <div style="background: var(--bg-tertiary); padding: 0.65rem 0.85rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                            <div style="font-size: 0.68rem; color: var(--text-muted);">Cohort Median Score</div>
                            <div style="font-size: 1.1rem; font-weight: 800; color: #94A3B8; font-family: var(--font-mono);">${data.median_score}%</div>
                        </div>
                        <div style="background: var(--bg-tertiary); padding: 0.65rem 0.85rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                            <div style="font-size: 0.68rem; color: var(--text-muted);">75th Percentile Bar</div>
                            <div style="font-size: 1.1rem; font-weight: 800; color: var(--color-match); font-family: var(--font-mono);">${data.p75_score}%</div>
                        </div>
                    </div>

                    ${(data.top_in_demand_skills && data.top_in_demand_skills.length > 0) ? `
                        <div style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.35rem;">High-Frequency Verified Skills across Top-Quartile Candidates:</div>
                        <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
                            ${data.top_in_demand_skills.map(s => `
                                <span style="font-size: 0.68rem; font-family: var(--font-mono); background: rgba(37,99,235,0.1); border: 1px solid rgba(37,99,235,0.25); color: #93C5FD; padding: 0.15rem 0.45rem; border-radius: var(--radius-sm);">
                                    ${escapeHtml(s.skill)} (${s.frequency_pct}%)
                                </span>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            `;
        }
        refreshIcons();
    } catch (err) {
        console.error('Benchmark error:', err);
        container.innerHTML = '<div style="font-size: 0.78rem; color: var(--text-muted);">Role benchmark unavailable.</div>';
    }
}

async function runSkillSimulation() {
    const select = document.getElementById('selectSimulateSkill');
    const resultBox = document.getElementById('simulationResultBox');
    const btnSim = document.getElementById('btnRunSkillSimulation');

    if (!select || !resultBox) return;
    const skill = select.value.trim();

    if (!skill) {
        alert('Please choose a missing skill from the dropdown to project its impact.');
        return;
    }

    if (!currentUserAnalysisData) {
        alert('Please run a candidate self-assessment first.');
        return;
    }

    if (btnSim) {
        btnSim.disabled = true;
        btnSim.innerHTML = '<i data-lucide="loader" style="width: 12px; height: 12px;"></i> Projecting...';
        refreshIcons();
    }

    try {
        const res = await fetch('/api/v1/roadmaps/simulate-skill', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                baseline_score: currentUserAnalysisData.fit_score || 0,
                target_skill: skill,
                roadmap_id: currentCandidateRoadmap ? currentCandidateRoadmap.id : null
            })
        });

        const data = await res.json();
        if (data.success) {
            resultBox.style.display = 'block';
            resultBox.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.4rem;">
                    <div style="font-size: 0.82rem; font-weight: 700; color: #93C5FD;">
                        Projected Impact for "${escapeHtml(skill)}":
                    </div>
                    <span style="font-size: 0.7rem; font-weight: 700; color: var(--color-match); background: rgba(22, 163, 74, 0.15); border: 1px solid rgba(22, 163, 74, 0.35); padding: 0.15rem 0.45rem; border-radius: var(--radius-sm);">
                        +${data.readiness_boost}% Readiness Boost
                    </span>
                </div>
                <div style="font-size: 0.78rem; color: var(--text-primary); margin-bottom: 0.35rem;">
                    Projected Match Score: <b>${data.baseline_score}% &rarr; ${data.projected_score}%</b> &bull; Projected Cohort Percentile Boost: <b>+${data.percentile_shift}%</b>
                </div>
                <div style="font-size: 0.74rem; color: var(--text-secondary);">
                    <b>Actionable Next Step:</b> Complete the <i>${escapeHtml(data.recommended_action || 'targeted roadmap milestone')}</i> in your career progression to verify this competency with recruiters.
                </div>
            `;
            refreshIcons();
        } else {
            alert(`Simulation error: ${data.error}`);
        }
    } catch (err) {
        console.error('Simulation error:', err);
        alert(`Error running simulation: ${err.message}`);
    } finally {
        if (btnSim) {
            btnSim.disabled = false;
            btnSim.innerHTML = '<i data-lucide="play" style="width: 13px; height: 13px;"></i> Project Impact';
            refreshIcons();
        }
    }
}

/* ============================================================
   EMAIL AUTO-MONITOR — Full Controller
   Connects to /api/v1/email-monitor/* endpoints
   ============================================================ */
function setupEmailMonitor() {
    const modal         = document.getElementById('emailMonitorModalOverlay');
    const btnOpen       = document.getElementById('btnOpenEmailMonitorModal');
    const btnClose      = document.getElementById('btnCloseEmailMonitorModal');
    const btnCancel     = document.getElementById('btnCancelEmailMonitor');
    const btnSave       = document.getElementById('btnSaveEmailMonitor');
    const btnSync       = document.getElementById('btnSyncEmailNow');
    const statusBanner  = document.getElementById('emailMonitorStatusBanner');
    const statusDot     = document.getElementById('emailMonitorStatusDot');
    const logList       = document.getElementById('emailIngestionLogList');

    if (!modal) return;

    // ── helpers ──────────────────────────────────────────────
    const openModal  = () => { modal.classList.add('active'); loadIngestionLogs(); };
    const closeModal = () => modal.classList.remove('active');

    function showBanner(msg, type) {
        if (!statusBanner) return;
        const styles = {
            success: 'background: rgba(34,197,94,0.12); border: 1px solid rgba(34,197,94,0.35); color: #4ADE80;',
            error:   'background: rgba(239,68,68,0.12);  border: 1px solid rgba(239,68,68,0.35);  color: #F87171;',
            info:    'background: rgba(37,99,235,0.10);  border: 1px solid rgba(37,99,235,0.35);  color: #93C5FD;',
        };
        statusBanner.style.cssText = `display: block; padding: 0.6rem 0.85rem; border-radius: var(--radius-sm); font-size: 0.78rem; font-weight: 600; ${styles[type] || styles.info}`;
        statusBanner.textContent = msg;
    }

    function setStatusDot(active) {
        if (!statusDot) return;
        statusDot.style.background = active ? '#22C55E' : '#4B5563';
        statusDot.title = active ? 'Monitor active — polling inbox' : 'Monitor inactive';
    }

    function renderLogs(logs) {
        if (!logList) return;
        if (!logs || logs.length === 0) {
            logList.innerHTML = '<div style="color: var(--text-muted); padding: 0.5rem; text-align: center;">No emails ingested yet. The system will process new resume emails as they arrive.</div>';
            return;
        }
        logList.innerHTML = logs.map(log => {
            const statusColors = {
                processed: '#4ADE80', failed: '#F87171', duplicate: '#FBBF24', skipped: '#94A3B8'
            };
            const col = statusColors[log.status] || '#94A3B8';
            const ts  = log.received_at ? new Date(log.received_at).toLocaleString() : '—';
            return `
                <div style="display: flex; align-items: flex-start; gap: 0.6rem; background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 0.55rem 0.75rem;">
                    <div style="width: 8px; height: 8px; border-radius: 50%; background: ${col}; margin-top: 0.35rem; flex-shrink: 0;"></div>
                    <div style="flex: 1; min-width: 0;">
                        <div style="font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(log.sender_email || 'Unknown sender')}</div>
                        <div style="color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(log.email_subject || '(no subject)')}</div>
                        <div style="color: var(--text-muted); font-size: 0.68rem; margin-top: 0.1rem;">${ts}</div>
                    </div>
                    <span style="font-size: 0.68rem; font-weight: 700; color: ${col}; text-transform: uppercase; white-space: nowrap;">${log.status}</span>
                </div>`;
        }).join('');
    }

    async function loadIngestionLogs() {
        try {
            const resp = await fetch('/api/v1/email-monitor/logs?limit=15');
            if (resp.ok) {
                const data = await resp.json();
                renderLogs(data.logs || []);
                setStatusDot((data.logs || []).length > 0);
            }
        } catch(e) { console.warn('Could not load ingestion logs:', e); }
    }

    // ── open / close ─────────────────────────────────────────
    if (btnOpen)   btnOpen.addEventListener('click', openModal);
    if (btnClose)  btnClose.addEventListener('click', closeModal);
    if (btnCancel) btnCancel.addEventListener('click', closeModal);
    modal.addEventListener('click', e => { if (e.target === modal) closeModal(); });

    // ── Save / Connect ────────────────────────────────────────
    if (btnSave) {
        btnSave.addEventListener('click', async () => {
            const email    = document.getElementById('emEmail')?.value.trim();
            const password = document.getElementById('emPassword')?.value;
            const imap     = document.getElementById('emImap')?.value.trim();
            const port     = parseInt(document.getElementById('emPort')?.value || '993');
            const folder   = document.getElementById('emFolder')?.value.trim() || 'INBOX';
            const interval = parseInt(document.getElementById('emPollInterval')?.value || '5');

            if (!email || !password || !imap) {
                showBanner('⚠ Please fill in IMAP server, email address, and password.', 'error');
                return;
            }

            btnSave.disabled = true;
            btnSave.innerHTML = '<i data-lucide="loader" style="width:14px;height:14px;"></i> Connecting…';
            refreshIcons();
            showBanner('⏳ Testing connection to your mailbox…', 'info');

            try {
                const resp = await fetch('/api/v1/email-monitor/configure', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        hr_email: email,
                        imap_server: imap,
                        imap_port: port,
                        imap_password: password,
                        monitored_folder: folder,
                        poll_interval_minutes: interval
                    })
                });
                const data = await resp.json();
                if (resp.ok && data.status === 'configured') {
                    showBanner(`✅ Connected! Monitoring ${email} every ${interval} min. New resume emails will be auto-analysed.`, 'success');
                    setStatusDot(true);
                    await loadIngestionLogs();
                    // Schedule background polling refresh inside the modal
                    window._emailMonitorPollId = setInterval(loadIngestionLogs, interval * 60 * 1000);
                } else {
                    showBanner(`❌ ${data.error || data.message || 'Connection failed. Check credentials.'}`, 'error');
                    setStatusDot(false);
                }
            } catch(err) {
                showBanner(`❌ Network error: ${err.message}`, 'error');
                setStatusDot(false);
            } finally {
                btnSave.disabled = false;
                btnSave.innerHTML = '<i data-lucide="wifi" style="width:14px;height:14px;"></i> Connect &amp; Start Monitoring';
                refreshIcons();
            }
        });
    }

    // ── Sync Now ─────────────────────────────────────────────
    if (btnSync) {
        btnSync.addEventListener('click', async () => {
            const origHtml = btnSync.innerHTML;
            btnSync.disabled = true;
            btnSync.innerHTML = '<i data-lucide="loader" style="width:12px;height:12px;"></i> Syncing…';
            refreshIcons();
            showBanner('⏳ Syncing mailbox — scanning for new resume emails…', 'info');

            try {
                const resp = await fetch('/api/v1/email-monitor/sync', { method: 'POST' });
                const data = await resp.json();
                if (resp.ok) {
                    const n = data.processed_count || 0;
                    showBanner(`✅ Sync complete. ${n} new resume email${n !== 1 ? 's' : ''} processed.`, 'success');
                    setStatusDot(true);
                    await loadIngestionLogs();
                } else {
                    showBanner(`❌ Sync failed: ${data.error || 'No active monitor configured.'}`, 'error');
                }
            } catch(err) {
                showBanner(`❌ Sync error: ${err.message}`, 'error');
            } finally {
                btnSync.disabled = false;
                btnSync.innerHTML = origHtml;
                refreshIcons();
            }
        });
    }

    // ── On page load: check if monitor is already active ──────
    (async () => {
        try {
            const resp = await fetch('/api/v1/email-monitor/logs?limit=1');
            if (resp.ok) {
                const data = await resp.json();
                if ((data.logs || []).length > 0) setStatusDot(true);
            }
        } catch(e) { /* silently ignore */ }
    })();
}
