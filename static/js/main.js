/**
 * Resume Ranking System - Frontend JavaScript
 * Handles file uploads, form validation, and results interactions
 */

// ========== File Upload Handler ==========

let uploadedFiles = [];

document.addEventListener('DOMContentLoaded', function() {
    const dragZone = document.getElementById('drag_zone');
    const fileInput = document.getElementById('file_input');
    const jobDescription = document.getElementById('job_description');
    const submitBtn = document.getElementById('submit_btn');
    const howToggle = document.getElementById('how-it-works-toggle');
    const howPanel = document.getElementById('how-it-works');

    if (dragZone) {
        // File input click
        dragZone.addEventListener('click', () => fileInput.click());

        // Drag & drop events
        dragZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dragZone.classList.add('dragover');
        });

        dragZone.addEventListener('dragleave', () => {
            dragZone.classList.remove('dragover');
        });

        dragZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dragZone.classList.remove('dragover');
            const files = Array.from(e.dataTransfer.files);
            handleFileSelection(files);
        });

        // File input change
        fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            handleFileSelection(files);
        });
    }

    if (jobDescription) {
        // Character counter
        jobDescription.addEventListener('input', function() {
            const charCount = document.getElementById('char_count');
            if (charCount) {
                charCount.textContent = this.value.length;
            }
            validateForm();
        });
    }

    if (submitBtn) {
        submitBtn.addEventListener('click', handleSubmit);
    }

    if (howToggle && howPanel) {
        howToggle.addEventListener('click', () => {
            const isOpen = howPanel.classList.toggle('open');
            howPanel.setAttribute('aria-hidden', String(!isOpen));
            howToggle.setAttribute('aria-expanded', String(isOpen));
            const icon = howToggle.querySelector('.chevron');
            if (icon) {
                icon.textContent = isOpen ? '▲' : '▼';
            }
        });
    }
});

function handleFileSelection(files) {
    const errorBox = document.getElementById('upload_errors');
    const fileList = document.getElementById('file_list');

    if (!errorBox || !fileList) return;

    uploadedFiles = [];
    errorBox.style.display = 'none';
    errorBox.innerHTML = '';
    fileList.innerHTML = '';

    let hasErrors = false;

    for (const file of files) {
        // Validate PDF
        if (file.type !== 'application/pdf' && !file.name.endsWith('.pdf')) {
            showError(`Invalid file type: ${file.name} (only PDF allowed)`);
            hasErrors = true;
            continue;
        }

        // Validate size (10 MB)
        const maxSize = 10 * 1024 * 1024;
        if (file.size > maxSize) {
            const sizeInMB = (file.size / (1024 * 1024)).toFixed(1);
            showError(`File too large: ${file.name} (${sizeInMB}MB, max 10MB)`);
            hasErrors = true;
            continue;
        }

        uploadedFiles.push(file);
        addFileToList(file);
    }

    validateForm();

    function showError(msg) {
        if (!hasErrors) {
            errorBox.style.display = 'block';
        }
        const p = document.createElement('p');
        p.textContent = msg;
        errorBox.appendChild(p);
        hasErrors = true;
    }
}

function addFileToList(file) {
    const fileList = document.getElementById('file_list');
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';

    const sizeInMB = (file.size / (1024 * 1024)).toFixed(2);
    const fileInfo = document.createElement('div');
    fileInfo.className = 'file-info';
    fileInfo.innerHTML = `
        <div class="file-name">📄 ${file.name}</div>
        <div class="file-size">${sizeInMB} MB</div>
    `;

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'file-remove';
    removeBtn.textContent = '✕';
    removeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        uploadedFiles = uploadedFiles.filter(f => f !== file);
        fileItem.remove();
        validateForm();
    });

    fileItem.appendChild(fileInfo);
    fileItem.appendChild(removeBtn);
    fileList.appendChild(fileItem);
}

function validateForm() {
    const submitBtn = document.getElementById('submit_btn');
    const jobDescription = document.getElementById('job_description');

    if (!submitBtn || !jobDescription) return;

    const hasFiles = uploadedFiles.length > 0;
    const jobDescText = jobDescription.value.trim();
    const wordCount = jobDescText ? jobDescText.split(/\s+/).length : 0;
    const hasJobDescription = jobDescText.length > 50 && wordCount >= 20;

    submitBtn.disabled = !(hasFiles && hasJobDescription);
}

async function handleSubmit(e) {
    e.preventDefault();

    if (uploadedFiles.length === 0) {
        alert('Please select at least one PDF resume');
        return;
    }

    const jobDescription = document.getElementById('job_description').value;
    const jobWordCount = jobDescription.trim().split(/\s+/).filter(Boolean).length;
    if (jobDescription.length < 50 || jobWordCount < 20) {
        alert('Job description must be at least 50 characters and 20 words');
        return;
    }

    // Show loading overlay
    const loadingOverlay = document.getElementById('loading_overlay');
    const loadingText = document.getElementById('loading_text');
    const loadingDetail = document.getElementById('loading_detail');
    const progressFill = document.getElementById('progress_fill');
    const progressPercent = document.getElementById('progress_percent');
    const progressStep = document.getElementById('progress_step');

    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
    }

    try {
        // Step 1: Upload files
        if (loadingText) loadingText.textContent = 'Uploading resumes...';
        if (loadingDetail) loadingDetail.textContent = `Uploading ${uploadedFiles.length} file(s) to server`;
        if (progressFill) {
            progressFill.style.width = '10%';
            progressFill.setAttribute('aria-valuenow', '10');
        }
        if (progressPercent) progressPercent.textContent = '10%';

        const uploadFormData = new FormData();
        uploadedFiles.forEach(file => {
            uploadFormData.append('resumes', file);
        });
        uploadFormData.append('job_description', jobDescription);

        const uploadResponse = await fetch('/upload', {
            method: 'POST',
            body: uploadFormData
        });

        if (!uploadResponse.ok) {
            const error = await uploadResponse.json();
            throw new Error(error.error || 'Upload failed');
        }

        const uploadData = await uploadResponse.json();
        const sessionId = uploadData.session_id;

        // Step 2: Start analysis
        if (loadingText) loadingText.textContent = 'Starting analysis...';
        if (loadingDetail) loadingDetail.textContent = 'Initializing AI-powered resume analysis';
        if (progressFill) {
            progressFill.style.width = '20%';
            progressFill.setAttribute('aria-valuenow', '20');
        }
        if (progressPercent) progressPercent.textContent = '20%';

        const analyzeResponse = await fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: sessionId,
                job_description: jobDescription
            })
        });

        if (!analyzeResponse.ok) {
            const error = await analyzeResponse.json();
            throw new Error(error.error || 'Analysis failed');
        }

        // Step 3: Poll progress
        let progressComplete = false;
        while (!progressComplete) {
            const progressResponse = await fetch(`/progress/${sessionId}`);
            const progressData = await progressResponse.json();

            if (loadingText) {
                loadingText.textContent = progressData.step || 'Processing...';
            }
            if (loadingDetail) {
                loadingDetail.textContent = 'AI is analyzing skills, experience, and generating insights';
            }
            if (progressStep) {
                progressStep.textContent = progressData.step || '';
            }
            if (progressFill) {
                progressFill.style.width = progressData.percent + '%';
                progressFill.setAttribute('aria-valuenow', progressData.percent);
            }
            if (progressPercent) {
                progressPercent.textContent = progressData.percent + '%';
            }

            if (progressData.percent >= 100) {
                progressComplete = true;
            } else {
                await new Promise(resolve => setTimeout(resolve, 1500));
            }
        }

        // Redirect to results
        if (loadingText) loadingText.textContent = 'Analysis complete!';
        if (loadingDetail) loadingDetail.textContent = 'Redirecting to results...';
        window.location.href = `/results/${sessionId}`;

    } catch (error) {
        console.error('Error:', error);
        if (loadingText) {
            loadingText.textContent = 'Error: ' + error.message;
        }
        if (loadingOverlay) {
            setTimeout(() => {
                loadingOverlay.style.display = 'none';
            }, 3000);
        }
    }
}

// ========== Results Page Interactions ==========

document.addEventListener('DOMContentLoaded', function() {
    // Expandable rows on results page with smooth animation
    const expandableRows = document.querySelectorAll('.expandable-row');
    expandableRows.forEach(row => {
        row.addEventListener('click', function() {
            const nextRow = this.nextElementSibling;
            if (nextRow && nextRow.classList.contains('gap-analysis-row')) {
                // Toggle expanded state
                const isExpanded = nextRow.classList.contains('expanded');
                
                if (isExpanded) {
                    nextRow.style.display = 'none';
                    nextRow.classList.remove('expanded');
                    this.classList.remove('expanded');
                } else {
                    nextRow.style.display = 'table-row';
                    nextRow.classList.add('expanded');
                    this.classList.add('expanded');
                }
            }
        });
    });

    // Sortable table headers with visual sort indicators
    const sortableHeaders = document.querySelectorAll('.sortable');
    sortableHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const column = this.dataset.column;
            sortTableByColumn(column, this);
        });
    });
});

function sortTableByColumn(column, headerElement) {
    const table = document.getElementById('ranking_table');
    if (!table) return;

    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr.expandable-row'));

    // Determine sort direction
    const isAscending = table.dataset.sortColumn === column && table.dataset.sortAscending === 'true';
    const sortAscending = !isAscending;

    // Sort rows
    rows.sort((a, b) => {
        let aValue, bValue;

        switch(column) {
            case 'rank':
                aValue = parseInt(a.cells[0].textContent);
                bValue = parseInt(b.cells[0].textContent);
                break;
            case 'candidate_name':
                aValue = a.cells[1].textContent.toLowerCase();
                bValue = b.cells[1].textContent.toLowerCase();
                break;
            case 'final_score':
                aValue = parseFloat(a.cells[2].textContent);
                bValue = parseFloat(b.cells[2].textContent);
                break;
            case 'skill_score':
                aValue = parseFloat(a.cells[3].textContent);
                bValue = parseFloat(b.cells[3].textContent);
                break;
            case 'experience_score':
                aValue = parseFloat(a.cells[4].textContent);
                bValue = parseFloat(b.cells[4].textContent);
                break;
            default:
                return 0;
        }

        if (sortAscending) {
            return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
        } else {
            return aValue < bValue ? 1 : aValue > bValue ? -1 : 0;
        }
    });

    // Reorder in DOM and include gap analysis rows
    const allRows = [];
    rows.forEach(row => {
        allRows.push(row);
        const nextRow = row.nextElementSibling;
        if (nextRow && nextRow.classList.contains('gap-analysis-row')) {
            allRows.push(nextRow);
        }
    });

    // Clear and re-add rows
    allRows.forEach(row => tbody.appendChild(row));

    // Update sort state
    table.dataset.sortColumn = column;
    table.dataset.sortAscending = sortAscending;

    // Update visual sort indicators on all headers
    const allHeaders = document.querySelectorAll('.sortable');
    allHeaders.forEach(header => {
        // Remove existing sort indicators
        header.innerHTML = header.innerHTML.replace(/ ▲| ▼/g, '');
        
        // Add indicator to active column
        if (header === headerElement) {
            header.innerHTML += sortAscending ? ' ▲' : ' ▼';
        }
    });
}
