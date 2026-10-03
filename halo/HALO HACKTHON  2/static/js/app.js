/**
 * Enterprise Candidate Requirement Analysis Portal Controller
 * Strict compliance: zero emojis, zero em dashes, rectangular radii, corporate palette
 */

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

    document.querySelectorAll('.modal-tab-btn').forEach(tab => {
        tab.addEventListener('click', (e) => {
            document.querySelectorAll('.modal-tab-btn').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.modal-tab-pane').forEach(p => p.style.display = 'none');
            
            const targetId = e.target.getAttribute('data-target');
            e.target.classList.add('active');
            const targetPane = document.getElementById(targetId);
            if (targetPane) targetPane.style.display = 'block';
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
        if (window.lucide) lucide.createIcons();
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

    if (window.lucide) lucide.createIcons();
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

    if (window.lucide) lucide.createIcons();

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
        const cand = await res.json();
        currentActiveCandidate = cand;

        const modal = document.getElementById('candidateModalOverlay');
        if (!modal) return;

        document.getElementById('modalCandidateName').innerText = cand.name;
        document.getElementById('modalCandidateEmail').innerText = cand.structured_resume.personal.email || 'Email on file';
        document.getElementById('modalCandidatePhone').innerText = cand.structured_resume.personal.phone || 'Phone on file';
        document.getElementById('modalCandidateLocation').innerText = cand.structured_resume.personal.location || 'Location on file';
        document.getElementById('modalDossierLink').href = `/api/export-dossier/${cand.id}`;

        const fitScore = cand.analysis.fit_score;
        const scoreRing = document.getElementById('modalHeroScoreRing');
        const scoreClass = fitScore >= 80 ? 'score-high' : (fitScore >= 50 ? 'score-mid' : 'score-low');
        scoreRing.className = `hero-score-ring ${scoreClass}`;
        document.getElementById('modalHeroScoreNumber').innerText = `${fitScore}%`;

        const confScore = cand.analysis.confidence.confidence_score;
        document.getElementById('modalHeroConfidence').innerText = `${confScore}%`;
        document.getElementById('modalConfidenceExplanation').innerText = cand.analysis.confidence.disclaimer;

        const breakdown = cand.analysis.fit_score_details.category_breakdown || {};
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

        document.getElementById('modalFormulaText').innerHTML = `
            <b>Calculation Transparency:</b> ${cand.analysis.fit_score_details.calculation_formula}.<br/>
            <span style="color: var(--text-secondary);">${cand.analysis.fit_score_details.explanation}</span>
        `;

        const flagsBox = document.getElementById('modalFlagsBanner');
        const flags = cand.flags;
        const flagItems = [];

        if (flags.duplicate.is_duplicate) {
            flagItems.push(`
                <div style="color: #F87171; font-weight: 600; font-size: 0.8rem;">
                    Notice: Duplicate Content Detected: ${flags.duplicate.details}
                </div>
            `);
        }
        if (flags.ai_content.is_flagged) {
            flagItems.push(`
                <div style="color: #93C5FD; font-weight: 600; font-size: 0.8rem;">
                    AI-Content Analysis Signal: ${flags.ai_content.display_text}.
                    <span style="font-weight: 400; font-size: 0.74rem; display: block; color: var(--text-muted); margin-top: 0.2rem;">
                        ${flags.ai_content.disclaimer}
                    </span>
                </div>
            `);
        }
        if (flags.repeated_content.is_flagged) {
            flagItems.push(`
                <div style="color: var(--color-flag); font-weight: 600; font-size: 0.8rem;">
                    Repeated Content Alert: ${flags.repeated_content.issues.join(' : ')}
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

        renderRequirementsMatrix(cand.analysis.comparisons);
        renderStructuredProfile(cand.structured_resume);

        document.getElementById('modalExecutiveSummary').innerText = cand.analysis.summary;
        const recsContainer = document.getElementById('modalRecommendationsList');
        if (recsContainer) {
            recsContainer.innerHTML = cand.analysis.recommendations.map(rec => `
                <div class="rec-item">
                    <i data-lucide="info" class="rec-icon" style="width: 14px; height: 14px;"></i>
                    <span>${rec}</span>
                </div>
            `).join('');
        }

        renderMockInterview(cand.analysis.mock_interview);

        modal.classList.add('active');
        if (window.lucide) lucide.createIcons();

    } catch (e) {
        console.error('Failed to load candidate detail:', e);
        alert('Could not load candidate analysis details.');
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

    const heading = document.getElementById('modalInterviewHeading');
    if (heading) {
        heading.innerText = `Targeted Interview Questions (${questions.length} Questions)`;
    }

    container.innerHTML = questions.map((q, idx) => {
        const isCustom = q.source === 'recruiter_custom';
        const customBadge = isCustom ? 
            `<span class="flag-badge flag-partial" style="font-size: 0.65rem; margin-left: 0.4rem;">[RECRUITER CUSTOM]</span>` : '';
        const deleteBtn = isCustom ? 
            `<button class="btn btn-secondary" style="padding: 0.2rem 0.5rem; font-size: 0.7rem; color: var(--color-gap);" onclick="deleteCustomQuestion(${q.id})" title="Delete custom question">
                <i data-lucide="trash-2" style="width: 12px; height: 12px;"></i> Delete
            </button>` : '';

        return `
            <div class="interview-card" id="interviewCard-${q.id}">
                <div class="interview-card-header">
                    <div style="display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap;">
                        <span class="interview-cat-tag">Q${idx+1}: ${escapeHtml(q.category)}</span>
                        ${customBadge}
                    </div>
                    <div style="display: flex; gap: 0.4rem;">
                        ${deleteBtn}
                        <button class="btn btn-secondary" style="padding: 0.25rem 0.55rem; font-size: 0.7rem;" onclick="copyInterviewQuestion('${encodeURIComponent(q.question)}')">
                            <i data-lucide="copy" style="width: 12px; height: 12px;"></i> Copy Question
                        </button>
                    </div>
                </div>
                <div class="interview-question-text">
                    "${escapeHtml(q.question)}"
                </div>
                <div class="interview-context-text">
                    <b>Rationale:</b> ${escapeHtml(q.context)}
                </div>
                <div class="interview-hint-box">
                    <b>Candidate Evaluation Criteria:</b> ${escapeHtml(q.evaluation_hint)}
                </div>
            </div>
        `;
    }).join('');

    if (window.lucide) lucide.createIcons();
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
        const res = await fetch(`/api/candidate/${currentActiveCandidate.id}/add-question`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: questionText,
                category: category,
                evaluation_hint: hint
            })
        });
        const data = await res.json();
        if (data.success) {
            currentActiveCandidate.analysis.mock_interview = data.questions;
            renderMockInterview(data.questions);
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

async function deleteCustomQuestion(questionId) {
    if (!currentActiveCandidate) return;

    try {
        const res = await fetch(`/api/candidate/${currentActiveCandidate.id}/delete-question/${questionId}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.success) {
            currentActiveCandidate.analysis.mock_interview = data.questions;
            renderMockInterview(data.questions);
        }
    } catch (e) {
        console.error('Error deleting question:', e);
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
        if (window.lucide) lucide.createIcons();
    }
}
