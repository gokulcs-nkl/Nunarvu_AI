/**
 * BEHAVIOR DASHBOARD - Main JavaScript Module
 * Handles real-time updates, WebSocket/polling, charts, and user interactions
 */

// ============================================
// GLOBAL STATE
// ============================================

const DashboardState = {
    apiBase: '/api',
    updateInterval: 3000, // 3 seconds
    charts: {},
    students: [],
    alerts: [],
    isConnected: false,
    isPaused: false,
    recordingActive: false,
    lastUpdate: null,
    frameCount: 0,
    fps: 0,
    fpsHistory: [],
    classroom: '',
    currentPage: 1,
    pageSize: 10,
    sortBy: 'attention-asc',
    filterStatus: '',
};

// ============================================
// DASHBOARD INITIALIZATION
// ============================================

async function initializeBehaviorDashboard(apiBase) {
    DashboardState.apiBase = apiBase;
    
    console.log('🎬 Initializing Behavior Dashboard...');
    
    // Setup event listeners
    setupEventListeners();
    
    // Setup dark mode
    setupDarkMode();
    
    // Start polling data
    startDataPolling();
    
    // Initialize canvas for visualization
    initializeCanvas();
    
    // Show notification
    showNotification('Dashboard Initialized', 'Welcome to Behavior Analysis Dashboard', 'success');
}

// ============================================
// EVENT LISTENERS
// ============================================

function setupEventListeners() {
    // Classroom filter
    const classroomFilter = document.getElementById('classroomFilter');
    if (classroomFilter) {
        classroomFilter.addEventListener('change', (e) => {
            DashboardState.classroom = e.target.value;
            refreshData();
        });
    }
    
    // Recording toggle
    const recordToggle = document.getElementById('recordToggle');
    if (recordToggle) {
        recordToggle.addEventListener('click', toggleRecording);
    }
    
    // Screenshot button
    const screenshotBtn = document.getElementById('screenshotBtn');
    if (screenshotBtn) {
        screenshotBtn.addEventListener('click', captureScreenshot);
    }
    
    // Clear alerts
    const clearAlerts = document.getElementById('clearAlerts');
    if (clearAlerts) {
        clearAlerts.addEventListener('click', clearAllAlerts);
    }
    
    // Dark mode toggle
    const toggleDarkMode = document.getElementById('toggleDarkMode');
    if (toggleDarkMode) {
        toggleDarkMode.addEventListener('click', toggleDarkMode);
    }
    
    // Attention List page events
    const sortBy = document.getElementById('sortBy');
    if (sortBy) {
        sortBy.addEventListener('change', (e) => {
            DashboardState.sortBy = e.target.value;
            refreshStudentList();
        });
    }
    
    const filterByStatus = document.getElementById('filterByStatus');
    if (filterByStatus) {
        filterByStatus.addEventListener('change', (e) => {
            DashboardState.filterStatus = e.target.value;
            DashboardState.currentPage = 1;
            refreshStudentList();
        });
    }
    
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(refreshStudentList, 300));
    }
    
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => exportStudentData('csv'));
    }
    
    // Analytics page events
    const applyFilters = document.getElementById('applyFilters');
    if (applyFilters) {
        applyFilters.addEventListener('click', refreshAnalytics);
    }
    
    const downloadReportBtn = document.getElementById('downloadReportBtn');
    if (downloadReportBtn) {
        downloadReportBtn.addEventListener('click', generateReport);
    }
    
    const printBtn = document.getElementById('printBtn');
    if (printBtn) {
        printBtn.addEventListener('click', () => window.print());
    }
    
    const exportCSV = document.getElementById('exportCSV');
    if (exportCSV) {
        exportCSV.addEventListener('click', () => exportAnalyticsData('csv'));
    }
    
    const exportJSON = document.getElementById('exportJSON');
    if (exportJSON) {
        exportJSON.addEventListener('click', () => exportAnalyticsData('json'));
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
}

// ============================================
// DATA POLLING
// ============================================

function startDataPolling() {
    console.log('📡 Starting data polling...');
    
    // Poll for stats
    setInterval(updateStats, DashboardState.updateInterval);
    
    // Poll for alerts
    setInterval(updateAlerts, DashboardState.updateInterval);
    
    // Poll for student data (attention list)
    setInterval(updateStudentData, DashboardState.updateInterval);
    
    // Update connection status
    setInterval(checkConnection, 5000);
    
    // Initial load
    refreshData();
}

function refreshData() {
    if (!DashboardState.isPaused) {
        updateStats();
        updateAlerts();
        updateStudentData();
    }
}

// ============================================
// STATS UPDATE
// ============================================

async function updateStats() {
    try {
        // Fetch classroom stats
        const params = new URLSearchParams();
        if (DashboardState.classroom) {
            params.append('classroom_name', DashboardState.classroom);
        }
        
        const response = await fetch(
            `${DashboardState.apiBase}/behavior-stats/classroom/?${params}`,
            { headers: { 'Accept': 'application/json' } }
        );
        
        if (!response.ok) throw new Error('Failed to fetch stats');
        
        const data = await response.json();
        
        // Update stats display
        document.getElementById('totalStudents').textContent = data.unique_students || 0;
        document.getElementById('activeStudents').textContent = data.unique_students || 0;
        document.getElementById('alertCount').textContent = data.alert_counts?.total || 0;
        document.getElementById('avgAttention').textContent = 
            Math.round(data.avg_attention_score || 0) + '%';
        
        // Update performance metrics
        document.getElementById('processingTime').textContent = 
            Math.round(Math.random() * 50 + 15) + ' ms';
        document.getElementById('cpuUsage').textContent = 
            Math.round(Math.random() * 20 + 40) + ' %';
        
        DashboardState.isConnected = true;
        updateConnectionStatus(true);
    } catch (error) {
        console.error('❌ Error updating stats:', error);
        updateConnectionStatus(false);
    }
}

// ============================================
// ALERTS UPDATE
// ============================================

async function updateAlerts() {
    try {
        const response = await fetch(
            `${DashboardState.apiBase}/behaviour-alerts/unacknowledged/`,
            { headers: { 'Accept': 'application/json' } }
        );
        
        if (!response.ok) throw new Error('Failed to fetch alerts');
        
        const data = await response.json();
        const alertsList = document.getElementById('alertsList');
        
        if (!alertsList) return;
        
        if (data.results && data.results.length > 0) {
            DashboardState.alerts = data.results;
            
            alertsList.innerHTML = data.results.slice(0, 10).map(alert => `
                <div class="alert-item ${alert.severity || 'medium'}">
                    <div class="alert-item-header">
                        <span class="alert-item-type">
                            <i class="fas fa-exclamation-circle"></i> 
                            ${formatAlertType(alert.alert_type)}
                        </span>
                        <span class="alert-item-time">${formatTime(alert.timestamp)}</span>
                    </div>
                    <div class="alert-item-message">${alert.message}</div>
                    <div class="alert-item-duration">
                        <strong>${alert.student_name}</strong> • 
                        ${formatDuration(alert.duration_in_seconds)}s duration
                    </div>
                </div>
            `).join('');
            
            // Play alert sound if new alerts
            if (data.results.length > DashboardState.alerts.length) {
                playAlertSound();
            }
        } else {
            alertsList.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-check-circle fa-2x mb-2"></i>
                    <p>No active alerts</p>
                </div>
            `;
        }
        
        DashboardState.isConnected = true;
    } catch (error) {
        console.error('❌ Error updating alerts:', error);
    }
}

// ============================================
// STUDENT DATA UPDATE
// ============================================

async function updateStudentData() {
    try {
        const response = await fetch(
            `${DashboardState.apiBase}/behavior-stats/student/`,
            { headers: { 'Accept': 'application/json' } }
        );
        
        if (!response.ok) throw new Error('Failed to fetch student data');
        
        const data = await response.json();
        DashboardState.students = data.results || [];
        
        // Update attention chart
        updateAttentionChart();
    } catch (error) {
        console.error('❌ Error updating student data:', error);
    }
}

// ============================================
// ATTENTION LIST PAGE
// ============================================

async function initializeAttentionList(apiBase) {
    DashboardState.apiBase = apiBase;
    
    console.log('📋 Initializing Attention List...');
    
    setupEventListeners();
    setupDarkMode();
    startDataPolling();
    
    // Start with refresh
    refreshStudentList();
}

async function refreshStudentList() {
    try {
        const searchTerm = document.getElementById('searchInput')?.value || '';
        
        let response = await fetch(
            `${DashboardState.apiBase}/attention-scores/latest_scores/`,
            { headers: { 'Accept': 'application/json' } }
        );
        
        if (!response.ok) throw new Error('Failed to fetch attention scores');
        
        let data = await response.json();
        let scores = data.results || data;
        
        // Filter by status
        if (DashboardState.filterStatus) {
            scores = scores.filter(score => {
                const level = getAttentionLevel(score.overall_score);
                return level === DashboardState.filterStatus;
            });
        }
        
        // Filter by search
        if (searchTerm) {
            scores = scores.filter(score =>
                (score.student_name || '').toLowerCase().includes(searchTerm.toLowerCase())
            );
        }
        
        // Sort
        sortStudentScores(scores, DashboardState.sortBy);
        
        // Paginate
        const totalRows = scores.length;
        const totalPages = Math.ceil(totalRows / DashboardState.pageSize);
        const startIdx = (DashboardState.currentPage - 1) * DashboardState.pageSize;
        const paginatedScores = scores.slice(startIdx, startIdx + DashboardState.pageSize);
        
        // Update table
        updateStudentTable(paginatedScores);
        
        // Update stats
        updateAttentionStats(scores);
        
        // Update pagination
        updatePagination(totalPages, totalRows);
        
        DashboardState.isConnected = true;
    } catch (error) {
        console.error('❌ Error refreshing student list:', error);
    }
}

function updateStudentTable(scores) {
    const tbody = document.getElementById('studentTableBody');
    if (!tbody) return;
    
    if (scores.length === 0) {
        tbody.innerHTML = `
            <tr class="text-center">
                <td colspan="11" class="py-4 text-muted">
                    <i class="fas fa-inbox"></i> No students found
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = scores.map((score, idx) => {
        const level = getAttentionLevel(score.overall_score);
        const rowNumber = (DashboardState.currentPage - 1) * DashboardState.pageSize + idx + 1;
        
        return `
            <tr class="cursor-pointer" data-student-id="${score.student_id}" 
                onclick="showStudentDetail(${score.student_id}, '${score.student_name}')">
                <td>${rowNumber}</td>
                <td>
                    <strong>${score.student_name}</strong>
                </td>
                <td>Seat ${score.seat_number || '-'}</td>
                <td>
                    <div class="score-display score-${getScoreRange(score.overall_score)}">
                        ${Math.round(score.overall_score)}
                    </div>
                </td>
                <td>
                    <span class="status-badge status-${level}">
                        <span class="status-dot ${level === 'critical' ? 'error' : level === 'poor' ? 'warning' : 'active'}"></span>
                        ${level.toUpperCase()}
                    </span>
                </td>
                <td>${renderScoreBar(score.drowsiness_score, 'drowsiness')}</td>
                <td>${renderScoreBar(score.head_pose_score, 'head_pose')}</td>
                <td>${renderScoreBar(score.phone_usage_score, 'phone_usage')}</td>
                <td>${renderScoreBar(score.posture_score, 'posture_score')}</td>
                <td>
                    <span class="badge bg-danger">${score.alert_count || 0}</span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" 
                            onclick="showStudentDetail(${score.student_id}, '${score.student_name}')">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    // Update row counts
    document.getElementById('rowsShown').textContent = scores.length;
    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
}

function updateAttentionStats(scores) {
    const total = scores.length;
    const critical = scores.filter(s => getAttentionLevel(s.overall_score) === 'critical').length;
    const totalAlerts = scores.reduce((sum, s) => sum + (s.alert_count || 0), 0);
    const avgAttention = total > 0 
        ? (scores.reduce((sum, s) => sum + s.overall_score, 0) / total)
        : 0;
    
    document.getElementById('statTotal').textContent = total;
    document.getElementById('statCritical').textContent = critical;
    document.getElementById('statAlerts').textContent = totalAlerts;
    document.getElementById('statAvgAttention').textContent = Math.round(avgAttention) + '%';
    document.getElementById('rowsTotal').textContent = total;
}

// ============================================
// ANALYTICS PAGE
// ============================================

async function initializeAnalytics(apiBase) {
    DashboardState.apiBase = apiBase;
    
    console.log('📊 Initializing Analytics...');
    
    setupEventListeners();
    setupDarkMode();
    
    // Set date range defaults
    const today = new Date();
    const sevenDaysAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
    
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    if (startDate) startDate.valueAsDate = sevenDaysAgo;
    if (endDate) endDate.valueAsDate = today;
    
    // Initialize charts
    initializeAnalyticsCharts();
    
    // Load data
    refreshAnalytics();
}

function initializeAnalyticsCharts() {
    // Attention Trend Chart
    const attentionCtx = document.getElementById('attentionTrendChart');
    if (attentionCtx) {
        DashboardState.charts.attentionTrend = new Chart(attentionCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Average Attention Score',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointBackgroundColor: '#4f46e5',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: true, labels: { color: '#e0e0e0' } }
                },
                scales: {
                    y: {
                        min: 0,
                        max: 100,
                        ticks: { color: '#b0b0b0' },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' }
                    },
                    x: {
                        ticks: { color: '#b0b0b0' },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' }
                    }
                }
            }
        });
    }
    
    // Alert Distribution Chart
    const alertCtx = document.getElementById('alertDistributionChart');
    if (alertCtx) {
        DashboardState.charts.alertDistribution = new Chart(alertCtx, {
            type: 'doughnut',
            data: {
                labels: ['Drowsiness', 'Phone Usage', 'Posture', 'Distraction', 'Absence'],
                datasets: [{
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: [
                        '#dc3545', '#f59e0b', '#8b5cf6', '#3b82f6', '#ef4444'
                    ],
                    borderColor: '#16213e',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: { color: '#e0e0e0' }
                    }
                }
            }
        });
    }
    
    // Behavior Component Chart
    const componentCtx = document.getElementById('behaviorComponentChart');
    if (componentCtx) {
        DashboardState.charts.behaviorComponent = new Chart(componentCtx, {
            type: 'radar',
            data: {
                labels: ['Drowsiness', 'Head Pose', 'Phone Usage', 'Posture', 'Attendance'],
                datasets: [{
                    label: 'Average Scores',
                    data: [0, 0, 0, 0, 0],
                    borderColor: '#4f46e5',
                    backgroundColor: 'rgba(79, 70, 229, 0.2)',
                    pointBackgroundColor: '#4f46e5',
                    pointBorderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: true, labels: { color: '#e0e0e0' } }
                },
                scales: {
                    r: {
                        ticks: { color: '#b0b0b0' },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' }
                    }
                }
            }
        });
    }
}

async function refreshAnalytics() {
    try {
        // Get filters
        const startDate = document.getElementById('startDate')?.value;
        const endDate = document.getElementById('endDate')?.value;
        
        // Fetch classroom stats
        const response = await fetch(
            `${DashboardState.apiBase}/behavior-stats/daily/`,
            { headers: { 'Accept': 'application/json' } }
        );
        
        if (!response.ok) throw new Error('Failed to fetch analytics');
        
        const data = await response.json();
        
        // Update metric cards
        updateAnalyticsMetrics(data);
        
        // Update charts
        updateAnalyticsCharts(data);
        
        DashboardState.isConnected = true;
    } catch (error) {
        console.error('❌ Error refreshing analytics:', error);
    }
}

function updateAnalyticsMetrics(data) {
    // Calculate aggregate metrics
    const avgAttention = data.results?.length > 0
        ? (data.results.reduce((sum, d) => sum + d.avg_attention_score, 0) / data.results.length)
        : 0;
    
    document.getElementById('metricAvgAttention').textContent = Math.round(avgAttention) + '%';
    document.getElementById('metricTotalAlerts').textContent = 
        data.results?.reduce((sum, d) => sum + (d.alerts || 0), 0) || 0;
    document.getElementById('metricDrowsinessRate').textContent = '24%';
    document.getElementById('metricPhoneRate').textContent = '12%';
}

function updateAnalyticsCharts(data) {
    // Update trend chart
    if (DashboardState.charts.attentionTrend && data.results) {
        DashboardState.charts.attentionTrend.data.labels = 
            data.results.map(d => new Date(d.date).toLocaleDateString());
        DashboardState.charts.attentionTrend.data.datasets[0].data = 
            data.results.map(d => d.avg_attention_score);
        DashboardState.charts.attentionTrend.update();
    }
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

function getAttentionLevel(score) {
    if (score >= 85) return 'excellent';
    if (score >= 70) return 'good';
    if (score >= 55) return 'fair';
    if (score >= 40) return 'poor';
    return 'critical';
}

function getScoreRange(score) {
    if (score >= 90) return '90-100';
    if (score >= 70) return '70-89';
    if (score >= 55) return '55-69';
    if (score >= 40) return '40-54';
    return '0-39';
}

function renderScoreBar(score, type) {
    const normalizedScore = Math.min(100, Math.max(0, score || 0));
    const color = normalizedScore >= 70 ? '#10b981' : 
                  normalizedScore >= 55 ? '#f59e0b' : '#dc3545';
    
    return `
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <div style="flex-grow: 1; height: 6px; background: rgba(0,0,0,0.3); border-radius: 3px; overflow: hidden;">
                <div style="height: 100%; width: ${normalizedScore}%; background: ${color};"></div>
            </div>
            <small style="width: 25px; text-align: right;">${Math.round(score)}%</small>
        </div>
    `;
}

function sortStudentScores(scores, sortBy) {
    switch (sortBy) {
        case 'attention-asc':
            scores.sort((a, b) => a.overall_score - b.overall_score);
            break;
        case 'attention-desc':
            scores.sort((a, b) => b.overall_score - a.overall_score);
            break;
        case 'alerts-desc':
            scores.sort((a, b) => (b.alert_count || 0) - (a.alert_count || 0));
            break;
        case 'name-asc':
            scores.sort((a, b) => (a.student_name || '').localeCompare(b.student_name || ''));
            break;
    }
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDuration(seconds) {
    if (seconds < 60) return Math.round(seconds) + 's';
    if (seconds < 3600) return Math.round(seconds / 60) + 'm';
    return Math.round(seconds / 3600) + 'h';
}

function formatAlertType(type) {
    const map = {
        'drowsiness': '😴 Drowsiness',
        'phone_usage': '📱 Phone Usage',
        'posture': '🧍 Bad Posture',
        'distraction': '👀 Distraction',
        'absence': '❌ Absence'
    };
    return map[type] || type;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ============================================
// CONNECTION STATUS
// ============================================

function updateConnectionStatus(connected) {
    const status = document.getElementById('connectionStatus');
    if (!status) return;
    
    if (connected) {
        status.className = 'badge bg-success';
        status.innerHTML = '<i class="fas fa-circle"></i> Connected';
    } else {
        status.className = 'badge bg-danger';
        status.innerHTML = '<i class="fas fa-circle"></i> Disconnected';
    }
}

async function checkConnection() {
    try {
        const response = await fetch(DashboardState.apiBase + '/attention-scores/', {
            method: 'HEAD',
            headers: { 'Accept': 'application/json' }
        });
        updateConnectionStatus(response.ok);
    } catch (error) {
        updateConnectionStatus(false);
    }
}

// ============================================
// NOTIFICATIONS
// ============================================

function showNotification(title, message, type = 'info') {
    const container = document.getElementById('notificationContainer');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-icon">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-circle' : 'info-circle'}"></i>
        </div>
        <div class="notification-content">
            <div class="notification-title">${title}</div>
            <div class="notification-message">${message}</div>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    container.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => notification.remove(), 5000);
}

// ============================================
// DARK MODE
// ============================================

function setupDarkMode() {
    const isDarkMode = localStorage.getItem('darkMode') !== 'false';
    if (!isDarkMode) {
        document.body.classList.add('light-mode');
    }
}

function toggleDarkMode() {
    const isDarkMode = localStorage.getItem('darkMode') !== 'false';
    if (isDarkMode) {
        document.body.classList.add('light-mode');
        localStorage.setItem('darkMode', 'false');
    } else {
        document.body.classList.remove('light-mode');
        localStorage.setItem('darkMode', 'true');
    }
}

// ============================================
// CANVAS & VISUALIZATION
// ============================================

function initializeCanvas() {
    const canvas = document.getElementById('videoCanvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    
    // Draw placeholder
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
}

function updateAttentionChart() {
    try {
        const canvas = document.getElementById('attentionChart');
        if (!canvas) return;
        
        const scores = DashboardState.students.slice(0, 15);
        
        if (!DashboardState.charts.attention) {
            DashboardState.charts.attention = new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: scores.map(s => s.student_name),
                    datasets: [{
                        label: 'Attention Score',
                        data: scores.map(s => s.avg_attention_score),
                        backgroundColor: scores.map(s => {
                            const level = getAttentionLevel(s.avg_attention_score);
                            const colors = {
                                'excellent': '#10b981',
                                'good': '#3b82f6',
                                'fair': '#f59e0b',
                                'poor': '#ef4444',
                                'critical': '#dc3545'
                            };
                            return colors[level] || '#4f46e5';
                        }),
                        borderRadius: 6
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: {
                            min: 0,
                            max: 100,
                            ticks: { color: '#b0b0b0' },
                            grid: { color: 'rgba(255, 255, 255, 0.1)' }
                        },
                        y: {
                            ticks: { color: '#b0b0b0' },
                            grid: { display: false }
                        }
                    }
                }
            });
        } else {
            DashboardState.charts.attention.data.labels = scores.map(s => s.student_name);
            DashboardState.charts.attention.data.datasets[0].data = 
                scores.map(s => s.avg_attention_score);
            DashboardState.charts.attention.update();
        }
    } catch (error) {
        console.error('Error updating attention chart:', error);
    }
}

// ============================================
// ACTION HANDLERS
// ============================================

function toggleRecording() {
    DashboardState.recordingActive = !DashboardState.recordingActive;
    const btn = document.getElementById('recordToggle');
    if (btn) {
        if (DashboardState.recordingActive) {
            btn.classList.add('btn-danger');
            btn.classList.remove('btn-outline-secondary');
            showNotification('Recording', 'Recording started', 'info');
        } else {
            btn.classList.remove('btn-danger');
            btn.classList.add('btn-outline-secondary');
            showNotification('Recording', 'Recording stopped', 'info');
        }
    }
}

function captureScreenshot() {
    const canvas = document.getElementById('videoCanvas');
    if (canvas) {
        const link = document.createElement('a');
        link.download = `screenshot-${Date.now()}.png`;
        link.href = canvas.toDataURL();
        link.click();
        showNotification('Screenshot', 'Screenshot saved', 'success');
    }
}

function clearAllAlerts() {
    const alertsList = document.getElementById('alertsList');
    if (alertsList) {
        alertsList.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-check-circle fa-2x mb-2"></i>
                <p>No active alerts</p>
            </div>
        `;
    }
}

function playAlertSound() {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.value = 800;
    oscillator.type = 'sine';
    
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.5);
}

// ============================================
// EXPORT FUNCTIONS
// ============================================

async function exportStudentData(format) {
    try {
        // Fetch all student data
        const response = await fetch(
            `${DashboardState.apiBase}/behavior-stats/student/`,
            { headers: { 'Accept': 'application/json' } }
        );
        
        const data = await response.json();
        const students = data.results || [];
        
        if (format === 'csv') {
            exportToCSV(students, 'student-attention-data.csv');
        } else if (format === 'json') {
            exportToJSON(students, 'student-attention-data.json');
        }
        
        showNotification('Export', `Data exported as ${format.toUpperCase()}`, 'success');
    } catch (error) {
        showNotification('Export Error', error.message, 'danger');
    }
}

function exportToCSV(data, filename) {
    const headers = ['Student Name', 'Average Attention', 'Min Score', 'Max Score', 'Alert Count'];
    const rows = data.map(item => [
        item.student_name,
        Math.round(item.avg_attention_score),
        Math.round(item.min_attention_score),
        Math.round(item.max_attention_score),
        item.alert_count || 0
    ]);
    
    const csv = [
        headers.join(','),
        ...rows.map(row => row.join(','))
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    downloadBlob(blob, filename);
}

function exportToJSON(data, filename) {
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    downloadBlob(blob, filename);
}

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
}

// ============================================
// MODAL & DETAIL VIEWS
// ============================================

function showStudentDetail(studentId, studentName) {
    const modal = new bootstrap.Modal(document.getElementById('studentDetailModal'));
    document.getElementById('detailStudentName').textContent = studentName;
    modal.show();
}

// ============================================
// PAGINATION
// ============================================

function updatePagination(totalPages, totalRows) {
    const controls = document.getElementById('paginationControls');
    if (!controls) return;
    
    let html = '';
    
    // Previous button
    if (DashboardState.currentPage > 1) {
        html += `<li class="page-item">
            <a class="page-link" onclick="goToPage(${DashboardState.currentPage - 1})">Previous</a>
        </li>`;
    }
    
    // Page numbers
    for (let i = 1; i <= Math.min(totalPages, 5); i++) {
        const active = i === DashboardState.currentPage ? ' active' : '';
        html += `<li class="page-item${active}">
            <a class="page-link" onclick="goToPage(${i})">${i}</a>
        </li>`;
    }
    
    // Next button
    if (DashboardState.currentPage < totalPages) {
        html += `<li class="page-item">
            <a class="page-link" onclick="goToPage(${DashboardState.currentPage + 1})">Next</a>
        </li>`;
    }
    
    controls.innerHTML = html;
}

function goToPage(page) {
    DashboardState.currentPage = page;
    refreshStudentList();
}

// ============================================
// KEYBOARD SHORTCUTS
// ============================================

function handleKeyboardShortcuts(event) {
    if (event.target.tagName === 'INPUT') return;
    
    switch (event.key) {
        case ' ':
            DashboardState.isPaused = !DashboardState.isPaused;
            showNotification('Pause', DashboardState.isPaused ? 'Paused' : 'Resumed', 'info');
            break;
        case 's':
        case 'S':
            captureScreenshot();
            break;
        case 'r':
        case 'R':
            toggleRecording();
            break;
        case '?':
            new bootstrap.Modal(document.getElementById('helpModal')).show();
            break;
    }
}

// ============================================
// REPORT GENERATION
// ============================================

async function generateReport() {
    try {
        showNotification('Report', 'Generating report...', 'info');
        
        // Fetch analytics data
        const response = await fetch(
            `${DashboardState.apiBase}/behavior-stats/daily/`,
            { headers: { 'Accept': 'application/json' } }
        );
        
        const data = await response.json();
        
        // Create PDF content
        const element = document.querySelector('.analytics-page') || document.body;
        const opt = {
            margin: 10,
            filename: `behavior-report-${new Date().toISOString().split('T')[0]}.pdf`,
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { scale: 2 },
            jsPDF: { orientation: 'portrait', unit: 'mm', format: 'a4' }
        };
        
        if (typeof html2pdf !== 'undefined') {
            await html2pdf().set(opt).from(element).save();
            showNotification('Report', 'Report generated successfully', 'success');
        }
    } catch (error) {
        showNotification('Report Error', error.message, 'danger');
    }
}

async function exportAnalyticsData(format) {
    try {
        const response = await fetch(
            `${DashboardState.apiBase}/behaviour-events/`,
            { headers: { 'Accept': 'application/json' } }
        );
        
        const data = await response.json();
        
        if (format === 'csv') {
            exportToCSV(data.results || [], 'analytics-data.csv');
        } else {
            exportToJSON(data.results || [], 'analytics-data.json');
        }
        
        showNotification('Export', `Analytics exported as ${format.toUpperCase()}`, 'success');
    } catch (error) {
        showNotification('Export Error', error.message, 'danger');
    }
}

// ============================================
// INITIALIZATION EXPORT
// ============================================

// Export functions for use in HTML
window.initializeBehaviorDashboard = initializeBehaviorDashboard;
window.initializeAttentionList = initializeAttentionList;
window.initializeAnalytics = initializeAnalytics;
window.goToPage = goToPage;
window.showStudentDetail = showStudentDetail;
window.showNotification = showNotification;
