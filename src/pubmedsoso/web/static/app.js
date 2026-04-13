let currentTaskId = null;
let currentPage = 1;
let pollInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    loadArticles();
    
    document.getElementById('search-form').addEventListener('submit', handleSearch);
    document.getElementById('export-xlsx').addEventListener('click', () => exportResults('xlsx'));
    document.getElementById('export-csv').addEventListener('click', () => exportResults('csv'));
});

async function handleSearch(e) {
    e.preventDefault();
    
    const keyword = document.getElementById('keyword').value;
    const pageNum = parseInt(document.getElementById('page-num').value);
    const downloadNum = parseInt(document.getElementById('download-num').value);
    const noDownload = document.getElementById('no-download').checked;
    
    const searchBtn = document.getElementById('search-btn');
    searchBtn.disabled = true;
    searchBtn.textContent = 'Starting...';
    
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                keyword,
                page_num: pageNum,
                download_num: downloadNum,
                no_download: noDownload,
            }),
        });
        
        const data = await response.json();
        currentTaskId = data.task_id;
        
        document.getElementById('progress-section').style.display = 'block';
        pollTaskStatus();
        
    } catch (error) {
        alert('Failed to start search: ' + error.message);
        searchBtn.disabled = false;
        searchBtn.textContent = 'Search';
    }
}

function pollTaskStatus() {
    if (pollInterval) clearInterval(pollInterval);
    
    pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/tasks/${currentTaskId}`);
            const task = await response.json();
            
            updateProgress(task);
            
            if (task.status === 'completed' || task.status === 'failed') {
                clearInterval(pollInterval);
                document.getElementById('search-btn').disabled = false;
                document.getElementById('search-btn').textContent = 'Search';
                
                if (task.status === 'completed') {
                    loadArticles(currentTaskId);
                    loadHistory();
                }
            }
        } catch (error) {
            console.error('Failed to poll task status:', error);
        }
    }, 1000);
}

function updateProgress(task) {
    document.getElementById('progress-status').textContent = 
        task.status.charAt(0).toUpperCase() + task.status.slice(1);
    document.getElementById('progress-percent').textContent = 
        Math.round(task.progress * 100) + '%';
    document.getElementById('progress-fill').style.width = 
        (task.progress * 100) + '%';
    document.getElementById('progress-message').textContent = task.message;
}

async function loadArticles(taskId = null, page = 1) {
    currentPage = page;
    let url = `/api/articles?page=${page}&page_size=20`;
    if (taskId) url += `&task_id=${taskId}`;
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        renderArticles(data.articles);
        document.getElementById('result-count').textContent = 
            `(${data.total} articles)`;
        renderPagination(data.total, data.page, data.page_size);
    } catch (error) {
        console.error('Failed to load articles:', error);
    }
}

function renderArticles(articles) {
    const tbody = document.getElementById('results-body');
    tbody.innerHTML = '';
    
    articles.forEach((article, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${(currentPage - 1) * 20 + index + 1}</td>
            <td class="title-cell" title="${escapeHtml(article.title)}">
                ${escapeHtml(truncate(article.title, 50))}
            </td>
            <td title="${escapeHtml(article.authors)}">
                ${escapeHtml(truncate(article.authors, 30))}
            </td>
            <td>${escapeHtml(truncate(article.journal, 20))}</td>
            <td>${article.pmid || '-'}</td>
            <td>${article.free_status > 0 ? 
                '<span class="badge badge-success">Yes</span>' : 
                '<span class="badge badge-secondary">No</span>'}</td>
            <td>${article.is_review ? 
                '<span class="badge badge-success">Yes</span>' : 
                '<span class="badge badge-secondary">No</span>'}</td>
        `;
        tbody.appendChild(row);
    });
}

function renderPagination(total, currentPage, pageSize) {
    const totalPages = Math.ceil(total / pageSize);
    const container = document.getElementById('pagination');
    container.innerHTML = '';
    
    if (totalPages <= 1) return;
    
    const maxButtons = 5;
    let start = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let end = Math.min(totalPages, start + maxButtons - 1);
    
    if (end - start < maxButtons - 1) {
        start = Math.max(1, end - maxButtons + 1);
    }
    
    if (start > 1) {
        container.appendChild(createPageButton(1));
        if (start > 2) container.appendChild(createEllipsis());
    }
    
    for (let i = start; i <= end; i++) {
        container.appendChild(createPageButton(i, i === currentPage));
    }
    
    if (end < totalPages) {
        if (end < totalPages - 1) container.appendChild(createEllipsis());
        container.appendChild(createPageButton(totalPages));
    }
}

function createPageButton(page, active = false) {
    const btn = document.createElement('button');
    btn.textContent = page;
    btn.className = active ? 'active' : '';
    btn.addEventListener('click', () => loadArticles(currentTaskId, page));
    return btn;
}

function createEllipsis() {
    const span = document.createElement('span');
    span.textContent = '...';
    span.style.padding = '8px';
    return span;
}

async function loadHistory() {
    try {
        const response = await fetch('/api/history');
        const history = await response.json();
        
        const tbody = document.getElementById('history-body');
        tbody.innerHTML = '';
        
        history.forEach(item => {
            const row = document.createElement('tr');
            row.style.cursor = 'pointer';
            row.innerHTML = `
                <td>${item.task_id}</td>
                <td>${item.article_count}</td>
                <td>${formatDate(item.created_at)}</td>
            `;
            row.addEventListener('click', () => {
                currentTaskId = item.task_id;
                loadArticles(item.task_id);
            });
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

function exportResults(format) {
    let url = `/api/export?format=${format}`;
    if (currentTaskId) url += `&task_id=${currentTaskId}`;
    window.location.href = url;
}

function truncate(str, length) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '...' : str;
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}
