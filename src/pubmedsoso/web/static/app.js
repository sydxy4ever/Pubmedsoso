let currentTaskId = null;
let currentPage = 1;
let pollInterval = null;
let allArticles = [];
let sortField = null;
let sortAsc = true;
const PAGE_SIZE = 20;

document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    loadArticles();

    document.getElementById('search-form').addEventListener('submit', handleSearch);
    document.getElementById('export-xlsx').addEventListener('click', () => exportResults('xlsx'));
    document.getElementById('export-csv').addEventListener('click', () => exportResults('csv'));

    document.querySelectorAll('th.sortable').forEach(th => {
        th.addEventListener('click', () => handleSort(th.dataset.sort));
    });
});

function handleSort(field) {
    if (sortField === field) {
        sortAsc = !sortAsc;
    } else {
        sortField = field;
        sortAsc = true;
    }

    document.querySelectorAll('th.sortable').forEach(th => {
        const arrow = th.dataset.sort === field ? (sortAsc ? ' ↑' : ' ↓') : ' ↕';
        th.textContent = th.textContent.replace(/ [↕↑↓]$/, '') + arrow;
    });

    allArticles.sort((a, b) => {
        let va = a[field] || '';
        let vb = b[field] || '';

        if (field === 'impact_factor') {
            va = parseFloat(va) || 0;
            vb = parseFloat(vb) || 0;
            return sortAsc ? va - vb : vb - va;
        }

        if (field === 'jcr_quartile' || field === 'cas_quartile') {
            va = va.replace(/[^Q1-4]/g, '').replace('Q', '') || '9';
            vb = vb.replace(/[^Q1-4]/g, '').replace('Q', '') || '9';
            const cmp = va.localeCompare(vb);
            return sortAsc ? cmp : -cmp;
        }

        const cmp = va.localeCompare(vb, 'zh');
        return sortAsc ? cmp : -cmp;
    });

    currentPage = 1;
    renderPage();
}

async function handleSearch(e) {
    e.preventDefault();

    const keyword = document.getElementById('keyword').value.trim();
    if (!keyword) return;

    const searchBtn = document.getElementById('search-btn');
    searchBtn.disabled = true;
    searchBtn.textContent = '搜索中...';

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keyword }),
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

function pollTaskStatus(onDone = null) {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/tasks/${currentTaskId}`);
            const task = await response.json();

            updateProgress(task);

            if (task.status === 'confirm') {
                clearInterval(pollInterval);
                const searchBtn = document.getElementById('search-btn');
                searchBtn.disabled = false;
                searchBtn.textContent = '搜索';
                showConfirmDialog(task.result_count);
                return;
            }

            if (task.status === 'counted') {
                clearInterval(pollInterval);
                confirmAndFetch();
                return;
            }

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

function showConfirmDialog(totalCount) {
    document.getElementById('progress-section').style.display = 'none';
    const dialog = document.getElementById('confirm-dialog');
    document.getElementById('confirm-count').textContent = totalCount;
    dialog.style.display = 'block';
}

async function confirmAndFetch() {
    const dialog = document.getElementById('confirm-dialog');
    dialog.style.display = 'none';

    try {
        const response = await fetch('/api/search/confirm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: currentTaskId }),
        });

        const data = await response.json();

        document.getElementById('progress-section').style.display = 'block';
        document.getElementById('results-section').style.display = 'none';
        pollTaskStatus();

    } catch (error) {
        alert('确认失败: ' + error.message);
    }
}

function cancelSearch() {
    const dialog = document.getElementById('confirm-dialog');
    dialog.style.display = 'none';
    document.getElementById('search-btn').disabled = false;
    document.getElementById('search-btn').textContent = '搜索';
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

async function loadArticles(taskId = null) {
    let url = '/api/articles?page=1&page_size=99999';
    if (taskId) url += `&task_id=${taskId}`;

    try {
        const response = await fetch(url);
        const data = await response.json();

        allArticles = data.articles;
        currentPage = 1;
        sortField = null;
        sortAsc = true;
        document.querySelectorAll('th.sortable').forEach(th => {
            th.textContent = th.textContent.replace(/ [↕↑↓]$/, '') + ' ↕';
        });

        document.getElementById('result-count').textContent =
            `(${allArticles.length} 篇)`;
        renderPage();
    } catch (error) {
        console.error('Failed to load articles:', error);
    }
}

function renderPage() {
    const total = allArticles.length;
    const totalPages = Math.ceil(total / PAGE_SIZE);
    if (currentPage > totalPages) currentPage = totalPages || 1;

    const start = (currentPage - 1) * PAGE_SIZE;
    const end = start + PAGE_SIZE;
    const pageArticles = allArticles.slice(start, end);

    renderArticles(pageArticles);
    renderPagination(total, currentPage, PAGE_SIZE);
}

function renderArticles(articles) {
    const tbody = document.getElementById('results-body');
    tbody.innerHTML = '';

    articles.forEach((article, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${(currentPage - 1) * PAGE_SIZE + index + 1}</td>
            <td class="title-cell" title="${escapeHtml(article.title)}">
                ${escapeHtml(truncate(article.title, 50))}
            </td>
            <td title="${escapeHtml(article.authors)}">
                ${escapeHtml(truncate(article.authors, 30))}
            </td>
            <td>${escapeHtml(truncate(article.journal, 20))}</td>
            <td class="rank-cell">${escapeHtml(article.impact_factor)}</td>
            <td class="rank-cell">${escapeHtml(article.jcr_quartile)}</td>
            <td class="rank-cell">${escapeHtml(article.cas_quartile)}</td>
            <td>${article.pmid ?
                `<a href="https://pubmed.ncbi.nlm.nih.gov/${article.pmid}/" target="_blank" rel="noopener">${article.pmid}</a>` :
                '-'}</td>
            <td>${article.pmcid ?
                `<a href="https://www.ncbi.nlm.nih.gov/pmc/articles/${article.pmcid}/" target="_blank" rel="noopener">${article.pmcid}</a>` :
                '-'}</td>
            <td>${article.abstract ?
                `<span class="abstract-icon" onclick="showAbstract(${(currentPage - 1) * PAGE_SIZE + index})" title="查看摘要">📄</span>` :
                ''}</td>
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
    btn.addEventListener('click', () => {
        currentPage = page;
        renderPage();
    });
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

let currentAbstractIndex = -1;

function showAbstract(index) {
    const article = allArticles[index];
    if (!article) return;
    currentAbstractIndex = index;
    document.getElementById('abstract-title').textContent = article.title || '摘要';
    document.getElementById('abstract-body').textContent = article.abstract || '无摘要';
    document.getElementById('abstract-translate').style.display = article.abstract ? 'block' : 'none';
    document.getElementById('translate-text').textContent = '翻译中...';
    document.getElementById('abstract-dialog').style.display = 'flex';

    if (article.abstract) translateAbstract();
}

function closeAbstract() {
    document.getElementById('abstract-dialog').style.display = 'none';
    currentAbstractIndex = -1;
}

async function translateAbstract() {
    const article = allArticles[currentAbstractIndex];
    if (!article || !article.abstract) return;

    try {
        const response = await fetch('/api/translate?text=' + encodeURIComponent(article.abstract));
        const data = await response.json();
        document.getElementById('translate-text').textContent = data.translated || '翻译失败';
    } catch (error) {
        document.getElementById('translate-text').textContent = '翻译失败';
    }
}
