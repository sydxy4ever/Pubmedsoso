# Pubmedsoso

一个基于 PubMed E-UTILS API 的文献检索工具，支持关键词搜索、期刊影响因子查询、摘要翻译，以及 Excel/CSV 导出。

## 功能

- 关键词搜索 PubMed 文献（自动获取全部结果）
- 自动提取文献详情（标题、摘要、关键词、作者、单位、PMID、PMCID 等）
- 期刊影响因子（IF）、JCR 分区、中科院分区显示
- 摘要中文翻译（Google Translate）
- PMID / PMCID 可点击链接
- 导出为 Excel (.xlsx) 或 CSV
- CLI 和 Web UI 两种使用方式
- 单一 SQLite 数据库，支持历史搜索管理
- OpenCode Skill 支持（AI Agent 可直接调用）

## 安装

```bash
git clone https://github.com/hiddenblue/Pubmedsoso.git
cd Pubmedsoso
pip install -e .
```

## 使用

### CLI

```bash
# 搜索 PubMed 并导出
pubmedsoso search "alzheimer's disease"

# 指定导出格式
pubmedsoso search "headache" -f csv

# 查看历史搜索
pubmedsoso export --list

# 按 search ID 导出历史结果
pubmedsoso export --search-id 1 -f xlsx

# 启动 Web UI
pubmedsoso web --port 8080

# 版本信息
pubmedsoso --version
```

### Web UI

```bash
pubmedsoso web
# 打开浏览器访问 http://localhost:8000/static/
```

Web UI 功能：
- 输入关键词搜索，结果超过 500 条时需确认
- 表格支持按标题、期刊、年份、IF、JCR、中科院分区排序
- 点击 📄 图标查看摘要及中文翻译
- PMID / PMCID 列可点击跳转 PubMed / PMC
- 历史记录按检索词显示，点击后只显示该搜索的结果

### OpenCode Skill

安装后 AI Agent（如 OpenCode、Hermes）可直接调用搜索功能：

```
请用 pubmedsoso 搜索 "CRISPR gene therapy" 的文献
```

Skill 文件位置：`~/.agents/skills/pubmedsoso/SKILL.md`

## 配置

通过环境变量覆盖默认配置（前缀 `PUBMEDSOSO_`）：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| PUBMEDSOSO_DB_DIR | ./data | 数据库目录 |
| PUBMEDSOSO_EXPORT_DIR | ./data/exports | 导出文件目录 |
| PUBMEDSOSO_MIN_REQUEST_INTERVAL | 1.0 | 请求间隔（秒） |
| PUBMEDSOSO_MAX_RETRIES | 3 | 最大重试次数 |
| PUBMEDSOSO_REQUEST_TIMEOUT | 30 | 请求超时（秒） |
| PUBMEDSOSO_WEB_HOST | 0.0.0.0 | Web UI 监听地址 |
| PUBMEDSOSO_WEB_PORT | 8000 | Web UI 端口 |

## 数据存储

所有搜索结果存储在单一 SQLite 数据库 `data/pubmedsoso.db` 中：

- `searches` 表 — 搜索记录（关键词、时间）
- `articles` 表 — 文献详情（标题、作者、期刊、IF、JCR、中科院分区等），通过 `search_id` 字段隔离不同搜索的结果
- `search_meta` 表 — 元数据键值对

每个搜索的结果是独立隔离的，不会混在一起。例如：
- 搜索 "covid" 得到的结果不会与 "lung cancer" 的结果混淆
- Web UI 历史记录中点击某个检索词，只会显示该搜索的结果

## 开发

```bash
pip install -e ".[dev]"
pytest
ruff check src/
```

## License

MIT
