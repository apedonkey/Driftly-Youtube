// AI Video Studio Frontend

let currentJobId = null;
let statusCheckInterval = null;

// Check for first time setup
document.addEventListener('DOMContentLoaded', function() {
    checkFirstTimeSetup();
    loadStats();
});

function checkFirstTimeSetup() {
    const hasKeys = localStorage.getItem('grokApiKey') && localStorage.getItem('falApiKey');
    
    if (!hasKeys) {
        document.getElementById('firstTimeSetup').style.display = 'flex';
    } else {
        loadRecentVideos();
    }
}

function toggleYoutubeFields() {
    const checkbox = document.getElementById('setupYoutube');
    const fields = document.getElementById('youtubeFields');
    fields.style.display = checkbox.checked ? 'block' : 'none';
}

function saveSetup() {
    const grokKey = document.getElementById('setupGrokKey').value.trim();
    const falKey = document.getElementById('setupFalKey').value.trim();
    const sheetId = document.getElementById('setupSheetId').value.trim();
    const useYoutube = document.getElementById('setupYoutube').checked;
    const youtubeSecrets = document.getElementById('youtubeClientSecrets').value.trim();
    
    if (!grokKey || !falKey) {
        alert('Please enter both API keys');
        return;
    }
    
    if (useYoutube && !youtubeSecrets) {
        alert('Please paste your YouTube client secrets JSON');
        return;
    }
    
    // Save to localStorage
    localStorage.setItem('grokApiKey', grokKey);
    localStorage.setItem('falApiKey', falKey);
    if (sheetId) localStorage.setItem('spreadsheetId', sheetId);
    localStorage.setItem('useYoutube', useYoutube);
    if (youtubeSecrets) {
        try {
            // Validate JSON
            JSON.parse(youtubeSecrets);
            localStorage.setItem('youtubeClientSecrets', youtubeSecrets);
        } catch (e) {
            alert('Invalid JSON format for YouTube credentials');
            return;
        }
    }
    
    // Hide setup
    document.getElementById('firstTimeSetup').style.display = 'none';
    
    // Reload page to apply settings
    location.reload();
}

function showSetup() {
    document.getElementById('firstTimeSetup').style.display = 'flex';
    
    // Pre-fill existing values
    document.getElementById('setupGrokKey').value = localStorage.getItem('grokApiKey') || '';
    document.getElementById('setupFalKey').value = localStorage.getItem('falApiKey') || '';
    document.getElementById('setupSheetId').value = localStorage.getItem('spreadsheetId') || '';
    
    const useYoutube = localStorage.getItem('useYoutube') === 'true';
    document.getElementById('setupYoutube').checked = useYoutube;
    
    if (useYoutube) {
        document.getElementById('youtubeFields').style.display = 'block';
        document.getElementById('youtubeClientSecrets').value = localStorage.getItem('youtubeClientSecrets') || '';
    }
}

function showInstructions() {
    const modal = new bootstrap.Modal(document.getElementById('instructionsModal'));
    modal.show();
}

function setTopic(template) {
    document.getElementById('quickTopic').value = template;
}

async function generateVideo() {
    const topic = document.getElementById('quickTopic').value.trim();
    
    if (!topic) {
        alert('Please enter a topic');
        return;
    }
    
    // Check API keys
    const grokKey = localStorage.getItem('grokApiKey');
    const falKey = localStorage.getItem('falApiKey');
    
    if (!grokKey || !falKey) {
        showSetup();
        return;
    }
    
    // Show progress
    document.getElementById('progressSection').style.display = 'block';
    document.getElementById('resultSection').style.display = 'none';
    document.getElementById('progressText').textContent = 'Starting video generation...';
    updateProgressBar(10);
    
    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                topic: topic,
                grokApiKey: grokKey,
                falApiKey: falKey,
                useYoutube: localStorage.getItem('useYoutube') === 'true',
                youtubeClientSecrets: localStorage.getItem('youtubeClientSecrets')
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentJobId = data.job_id;
            startStatusChecking();
        } else {
            showError(data.error);
        }
    } catch (error) {
        showError('Failed to start video generation');
    }
}

function startStatusChecking() {
    statusCheckInterval = setInterval(checkJobStatus, 2000);
}

async function checkJobStatus() {
    if (!currentJobId) return;
    
    try {
        const response = await fetch(`/api/status/${currentJobId}`);
        const data = await response.json();
        
        if (data.success) {
            const job = data.job;
            
            // Update progress text
            document.getElementById('progressText').textContent = job.progress;
            
            // Update progress bar
            if (job.progress.includes('script')) {
                updateProgressBar(30);
            } else if (job.progress.includes('video')) {
                updateProgressBar(60);
            } else if (job.progress.includes('YouTube') || job.progress.includes('Saving')) {
                updateProgressBar(90);
            }
            
            // Handle completion
            if (job.status === 'completed') {
                clearInterval(statusCheckInterval);
                showSuccess(job);
                loadRecentVideos();
                updateTodayCount();
            } else if (job.status === 'error') {
                clearInterval(statusCheckInterval);
                showError(job.error);
            }
        }
    } catch (error) {
        console.error('Status check failed:', error);
    }
}

function updateProgressBar(percent) {
    document.getElementById('progressBar').style.width = percent + '%';
}

function showSuccess(job) {
    document.getElementById('progressSection').style.display = 'none';
    document.getElementById('resultSection').style.display = 'block';
    
    document.getElementById('resultTitle').textContent = job.video_title || 'Video Created!';
    document.getElementById('resultMessage').textContent = job.video_url ? 
        'Your video has been uploaded to YouTube.' : 
        'Your video has been saved locally.';
    
    if (job.video_url) {
        const link = document.getElementById('resultLink');
        link.href = job.video_url;
        link.style.display = 'inline-block';
    }
}

function showError(message) {
    document.getElementById('progressSection').style.display = 'none';
    document.getElementById('resultSection').style.display = 'block';
    
    document.querySelector('.result-icon i').className = 'bi bi-x-circle-fill text-danger';
    document.getElementById('resultTitle').textContent = 'Error';
    document.getElementById('resultMessage').textContent = message;
    document.getElementById('resultLink').style.display = 'none';
}

function resetForm() {
    document.getElementById('quickTopic').value = '';
    document.getElementById('resultSection').style.display = 'none';
    document.querySelector('.result-icon i').className = 'bi bi-check-circle-fill text-success';
}

async function loadRecentVideos() {
    try {
        const response = await fetch('/api/recent-videos');
        const data = await response.json();
        
        if (data.success) {
            const container = document.getElementById('recentVideosList');
            container.innerHTML = '';
            
            if (data.videos.length === 0) {
                container.innerHTML = '<div class="text-center text-muted"><i class="bi bi-film"></i> No videos yet</div>';
                return;
            }
            
            data.videos.forEach(video => {
                const item = document.createElement('div');
                item.className = 'video-item';
                
                const date = new Date(video.created_at || video['Published Date']);
                const timeAgo = getTimeAgo(date);
                
                item.innerHTML = `
                    <h6>${video.title || video.Title}</h6>
                    <small>${video.topic || video.Topic}</small>
                    <div class="d-flex justify-content-between mt-2">
                        <small class="text-muted">${timeAgo}</small>
                        ${video.video_url || video['Video URL'] ? 
                            `<a href="${video.video_url || video['Video URL']}" target="_blank" class="btn btn-sm btn-outline-primary">
                                <i class="bi bi-play-circle"></i> Watch
                            </a>` : 
                            '<span class="badge bg-secondary">Local Only</span>'
                        }
                    </div>
                `;
                
                container.appendChild(item);
            });
        }
    } catch (error) {
        console.error('Failed to load recent videos:', error);
    }
}

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('totalVideos').textContent = data.total || 0;
            document.getElementById('totalViews').textContent = data.views || 0;
            document.getElementById('todayVideos').textContent = data.today || 0;
        }
    } catch (error) {
        // Stats are optional, don't show error
    }
}

function updateTodayCount() {
    const current = parseInt(document.getElementById('todayVideos').textContent) || 0;
    document.getElementById('todayVideos').textContent = current + 1;
}

function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return Math.floor(seconds / 60) + ' min ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + ' hours ago';
    return Math.floor(seconds / 86400) + ' days ago';
}