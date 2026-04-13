let currentTaskId = null;
let currentPage = 1;
let pollInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    loadArticles();

    document.getElementById('search-form').addEventListener('submit', handleSearch);
    document.getElementById('export-xlsx').addEventListener('click', () => exportResults('xlsx'));
    document.getElementById('export-csv').addEventListener('click', () => exportResults('csv'));
    document.getElementById('download-pdf').addEventListener('click', handleDownload);
});

async function handleSearch(e) {
    e.preventDefault();

    const keyword = document.getElementById('keyword').value.trim();
    if (!keyword) return;

    const pageNum = parseInt(document.getElementById('page-num').value) || 10;

    const searchBtn = document.getElementById('search-btn');
    searchBtn.disabled = true;
    searchBtn.textContent = '搜索中...';

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keyword, page_num: pageNum }),
        });

        const data = await response.json();
        currentTaskId = data.task_id;

        document.getElementById('progress-section').style.display = 'block';
        document.getElementById('results-section').style.display = 'none';
        pollTaskStatus();

    } catch (error) {
        alert('搜索失败: ' + error.message);
        searchBtn.disabled = false;
        searchBtn.textContent = '搜索';
    }
}

async function handleDownload() {
    if (!currentTaskId) { alert('请先搜索'); return; }

    const downloadBtn = document.getElementById('download-pdf');
    downloadBtn.disabled = true;
    downloadBtn.textContent = '下载中...';

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: currentTaskId, download_num: 10 }),
        });

        const data = await response.json();
        document.getElementById('progress-section').style.display = 'block';
        pollTaskStatus(() => {
            downloadBtn.disabled = false;
            downloadBtn.textContent = '下载免费 PDF';
            loadArticles(currentTaskId);
        });

    } catch (error) {
        alert('下载失败: ' + error.message);
        downloadBtn.disabled = false;
        downloadBtn.textContent = '下载免费 PDF';
    }
}

function pollTaskStatus(onDone = null) {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/tasks/${currentTaskId}`);
            const task = await response.json();

            updateProgress(task);

            if (task.status === 'completed' || task.status === 'failed') {
                clearInterval(pollInterval);
                const searchBtn = document.getElementById('search-btn');
                searchBtn.disabled = false;
                searchBtn.textContent = '搜索';

                if (task.status === 'completed') {
                    document.getElementById('progress-section').style.display = 'none';
                    document.getElementById('results-section').style.display = 'block';
                    loadArticles(currentTaskId);
                    loadHistory();
                }
                if (onDone) onDone();
            }
        } catch (error) {
            console.error('Poll failed:', error);
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
            `(${data.total} 篇)`;
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
            <td>${article.free_status === 2 ?
                '<span class="badge badge-success">免费</span>' :
                (article.free_status === 1 ?
                '<span class="badge badge-warning">部分</span>' :
                '<span class="badge badge-secondary">否</span>')}</td>
            <td>${article.is_review ?
                '<span class="badge badge-success">是</span>' :
                ''}</td>
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
                document.getElementById('results-section').style.display = 'block';
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
