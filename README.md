# Pubmedsoso

一个自动批量提取 PubMed 文献信息和下载免费文献的工具。

## 功能

- 关键词搜索 PubMed 文献
- 自动提取文献详情（标题、摘要、关键词、作者、单位等）
- 下载免费 PMC 全文 PDF
- SciHub 兜底下载非免费文献
- 导出为 Excel (.xlsx) 或 CSV
- CLI 和 Web UI 两种使用方式

## 安装

```bash
git clone https://github.com/hiddenblue/Pubmedsoso.git
cd Pubmedsoso
pip install -e .
```

## 使用

### CLI

```bash
# 搜索 + 提取 + 下载 + 导出
pubmedsoso search "alzheimer's disease" -n 10 -d 5

# 仅搜索提取，不下载 PDF
pubmedsoso search "headache" -n 5 --no-download

# 导出历史搜索结果
pubmedsoso export --list
pubmedsoso export --task 20260412120000 --format xlsx

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

## 配置

通过环境变量覆盖默认配置（前缀 `PUBMEDSOSO_`）：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| PUBMEDSOSO_SCIHUB_ENABLED | true | 启用 SciHub 兜底下载 |
| PUBMEDSOSO_SCIHUB_BASE_URL | https://sci-hub.se | SciHub 域名 |
| PUBMEDSOSO_DOWNLOAD_TIMEOUT | 60 | PDF 下载超时（秒） |
| PUBMEDSOSO_MIN_REQUEST_INTERVAL | 1.0 | 请求间隔（秒） |
| PUBMEDSOSO_MAX_RETRIES | 3 | 最大重试次数 |
| PUBMEDSOSO_WEB_PORT | 8000 | Web UI 端口 |

## 开发

```bash
pip install -e ".[dev]"
pytest
ruff check src/
```

## License

MIT
