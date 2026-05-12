# SuperOnCallAgent — 企业级智能 OnCall 运维助手

基于阿里云通义千问（qwen-max）+ LangGraph + FAISS + RAG 的智能运维系统，支持实时系统监控、日志分析、知识库问答和 AI 自动诊断。

---

## 功能概览

| 功能 | 说明 |
|------|------|
| 智能对话 | 多轮对话记忆 + 流式输出 + 会话历史持久化 |
| RAG 知识库 | 上传 PDF/TXT/MD → 自动切片 → 向量嵌入 → FAISS 检索 |
| AIOps 诊断 | Plan-Execute-Replan 自动故障诊断，实时流式展示进度 |
| 实时系统监控 | CPU/内存/磁盘/进程/网络，自动告警 SSE 推送 |
| CLS 日志查询 | 5 大日志主题独立存储，关键词搜索 + 模式分析 |
| Web 界面 | 三页面架构，现代化聊天 UI，侧边栏会话管理 |

---

## 架构

```
用户浏览器
    ├── http://localhost:9900  (OnCall 主服务 — FastAPI)
    │   ├── /api/chat         快速对话 + 流式对话
    │   ├── /api/aiops        AIOps 诊断 (SSE)
    │   ├── /api/upload       文件上传 + 自动向量化
    │   ├── /api/index_status 向量库查看 + 删除
    │   └── /api/monitor      实时监控 SSE 推送
    │
    ├── http://localhost:8003  (CLS 日志查询服务)
    │   ├── /api/cls/search   日志搜索
    │   ├── /api/cls/analyze  模式分析
    │   └── /api/cls/topics   主题管理
    │
    └── http://localhost:8004  (监控数据中心)
        ├── /api/monitor/cpu         CPU 指标
        ├── /api/monitor/memory      内存指标
        ├── /api/monitor/disk        磁盘分区
        ├── /api/monitor/memory-top  内存 TOP10
        ├── /api/monitor/processes   进程列表
        ├── /api/monitor/network     网络 I/O
        ├── /api/monitor/services    服务自动发现
        └── /api/monitor/tickets     历史工单
```

### 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI + uvicorn |
| 大模型 | 阿里云通义千问 qwen-max（OpenAI 兼容接口） |
| AI 框架 | LangChain + LangGraph |
| 向量数据库 | FAISS（纯 Python 嵌入式） |
| 嵌入模型 | DashScope text-embedding-v4（1024 维） |
| 系统监控 | psutil |
| 前端 | 原生 HTML/CSS/JS（零依赖框架） |
| 存储 | localStorage（前端会话持久化） |

---

## 快速开始

### 环境要求

- Python 3.10+（推荐 conda 环境）
- Windows / Linux / macOS

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `.env` 文件：

```ini
APP_NAME=SuperOnCallAgent
DEBUG=True
HOST=0.0.0.0
PORT=9900

DASHSCOPE_API_KEY=your-api-key-here
DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_MODEL=qwen-max
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4

RAG_TOP_K=3
CHUNK_MAX_SIZE=800
CHUNK_OVERLAP=100
```

### 3. 启动服务

同时启动三个服务：

```bash
# 终端 1 — OnCall 主服务 (9900)
python -m uvicorn app.main:app --host 0.0.0.0 --port 9900

# 终端 2 — CLS 日志服务 (8003)
python cls_server.py

# 终端 3 — 监控中心 (8004)
python monitor_server.py
```

### 4. 访问

| 地址 | 页面 |
|------|------|
| http://localhost:9900 | OnCall 主界面 |
| http://localhost:8003 | CLS 日志查询 |
| http://localhost:8004 | 系统监控中心 |
| http://localhost:9900/docs | API 文档 (Swagger) |

### 5. 上传知识库

```bash
# 通过 API 批量上传
for f in aiops-docs/*.md; do
    curl -X POST "http://localhost:9900/api/upload" -F "file=@$f"
done
```

或在 Web 界面点击输入框左侧 `...` → `上传文件`。

---

## 项目结构

```
oncall/
├── app/
│   ├── main.py                    # FastAPI 入口 + 生命周期管理
│   ├── config.py                  # 配置管理 (pydantic-settings)
│   ├── api/
│   │   ├── chat.py                # 对话接口 (快速/流式/会话管理)
│   │   ├── aiops.py               # AIOps 诊断接口 (SSE)
│   │   ├── file.py                # 文件上传 + 向量库管理
│   │   ├── health.py              # 健康检查
│   │   └── monitor.py             # 实时监控 SSE 推送
│   ├── services/
│   │   ├── rag_agent_service.py   # RAG Agent（LangGraph + ChatOpenAI）
│   │   ├── aiops_service.py       # AIOps Plan-Execute-Replan
│   │   ├── monitor_service.py     # 后台监控循环 + 告警推送
│   │   ├── vector_store_manager.py    # FAISS 存储管理（分批嵌入）
│   │   ├── vector_embedding_service.py # DashScope 嵌入服务
│   │   ├── vector_index_service.py     # 文件索引服务
│   │   ├── vector_search_service.py    # 向量检索服务
│   │   └── document_splitter_service.py # 文档分割（MD/PDF/TXT）
│   ├── agent/aiops/
│   │   ├── planner.py             # Plan 节点 — 制定执行计划
│   │   ├── executor.py            # Execute 节点 — 调用工具执行
│   │   ├── replanner.py           # Replan 节点 — 重新规划/生成报告
│   │   └── state.py               # 状态定义
│   ├── tools/
│   │   ├── knowledge_tool.py      # RAG 知识检索工具
│   │   ├── time_tool.py           # 时间工具
│   │   └── system_tools.py        # 系统监控工具 (psutil)
│   ├── models/                    # Pydantic 数据模型
│   └── utils/
│       ├── logger.py              # 日志配置 (loguru)
│       └── http_client.py         # HTTP 客户端（SSL 兼容）
├── static/
│   ├── index.html                 # OnCall 主界面
│   ├── cls.html                   # CLS 日志查询页面
│   ├── monitor.html               # 系统监控中心页面
│   ├── app.js                     # 主界面前端逻辑
│   └── styles.css                 # 全局样式
├── cls_server.py                  # CLS 日志服务（端口 8003）
├── monitor_server.py              # 监控数据服务（端口 8004）
├── cls_logs/                      # CLS 日志文件（自动生成）
│   ├── api_access.log
│   ├── system.log
│   ├── error.log
│   ├── performance.log
│   └── security.log
├── faiss_index/                   # FAISS 向量索引（持久化）
├── uploads/                       # 上传文件目录
├── aiops-docs/                    # 运维知识库文档
├── logs/                          # 应用日志
├── requirements.txt
├── .env
└── README.md
```

---

## 核心功能详解

### 1. RAG 知识库

```
上传文件 → DocumentSplitterService 切片
         → DashScopeEmbeddings 生成 1024 维向量
         → FAISS 存储 + 持久化 (faiss_index/)
         → retrieve_knowledge 工具检索 top_k=3
         → 注入 LLM 上下文生成答案
```

**切片规则**：
- Markdown 文件：先按 `#`/`##` 标题切分，再按 `chunk_max_size=800` 字符递归切分
- TXT/PDF：直接按 `chunk_max_size=800` 切分
- 小片段（<300 字符）自动合并
- DashScope 嵌入 API 每批 6 条，自动分批

**向量库管理**：
- `GET /api/index_status` — 查看所有已索引文件及切片详情
- `DELETE /api/index_file?file_name=xxx.md` — 按文件名删除切片

### 2. 对话模式

| 模式 | 说明 | 实现 |
|------|------|------|
| 快速模式 | 等待完整回答后一次性展示 | `POST /api/chat` |
| 流式模式 | 逐 token 实时输出 | `POST /api/chat_stream` (SSE) |

**多轮对话记忆**：
- 后端：LangGraph `MemorySaver` 按 `thread_id` 维护会话上下文
- 前端：`localStorage` 持久化所有会话消息 HTML

### 3. AIOps 诊断

采用 **Plan-Execute-Replan** 三阶段框架：

```
用户触发 → Planner（LLM 制定执行计划）
         → Executor（LLM 决策调用工具 → 真实执行 → 生成总结）
         → Replanner（判断是否继续 or 生成最终报告）
         → SSE 实时推送进度（计划/步骤完成/报告）
```

**可用工具**：
- `get_current_time` — 系统时间
- `get_system_overview` / `get_cpu_usage` / `get_memory_usage` / `get_disk_usage` — 真实系统监控
- `retrieve_knowledge` — 知识库检索

### 4. 系统监控

后台每 **10 秒**检测 CPU/内存/磁盘，超标时 SSE 推送到前端：

| 指标 | 告警阈值 |
|------|---------|
| CPU | >80% 告警 |
| 内存 | >85% 告警 |
| 磁盘 | >90% 告警 (>95% 紧急) |

### 5. CLS 日志查询

5 个独立日志主题，数据存储在 `cls_logs/` 目录：

| 主题 | 内容 | 来源 |
|------|------|------|
| API 访问日志 | HTTP 请求/响应/延迟 | 自动生成种子数据 |
| 系统日志 | 服务启停/配置变更/健康检查 | 自动生成种子数据 |
| 错误日志 | 应用异常 + 堆栈跟踪 | 种子数据 + 真实 app 日志采集 |
| 性能日志 | CPU/内存/QPS/p99 指标 | 种子数据 + 实时性能指标 |
| 安全审计日志 | 登录/鉴权/越权操作 | 自动生成种子数据 |

---

## API 参考

### OnCall 主服务 (9900)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/chat` | 快速对话 |
| POST | `/api/chat_stream` | 流式对话 (SSE) |
| POST | `/api/chat/clear` | 清空会话 |
| GET | `/api/chat/session/{id}` | 会话历史 |
| POST | `/api/aiops` | AIOps 诊断 (SSE) |
| POST | `/api/upload` | 上传文件 + 自动向量化 |
| GET | `/api/index_status` | 向量库状态 |
| DELETE | `/api/index_file?file_name=x` | 删除向量 |
| GET | `/api/monitor/stream` | 实时监控告警 (SSE) |
| GET | `/api/monitor/now` | 即时系统快照 |

### CLS 日志服务 (8003)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/cls/timestamp` | 当前时间戳 |
| GET | `/api/cls/topics` | 日志主题列表 |
| GET | `/api/cls/search?topic=&level=&query=&limit=` | 日志搜索 |
| GET | `/api/cls/service-logs?level=&limit=` | 服务日志查询 |
| GET | `/api/cls/analyze?topic=` | 日志模式分析 |
| GET | `/api/cls/collect` | 手动触发采集 |

### 监控中心 (8004)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/monitor/cpu` | CPU 使用率 + 各核心 |
| GET | `/api/monitor/memory` | 内存使用详情 |
| GET | `/api/monitor/disk` | 磁盘分区详情 |
| GET | `/api/monitor/processes?limit=` | CPU 占用进程列表 |
| GET | `/api/monitor/memory-top?limit=` | 内存占用 TOP N |
| GET | `/api/monitor/network` | 网络 I/O + 开机时长 |
| GET | `/api/monitor/services` | 服务自动发现 |
| GET | `/api/monitor/tickets` | 历史工单 |

---

## 运维知识库

`aiops-docs/` 目录内置 5 份参考文档：

- `cpu_high_usage.md` — CPU 使用率过高处理方案
- `memory_high_usage.md` — 内存使用率过高处理方案
- `disk_high_usage.md` — 磁盘使用率过高处理方案
- `slow_response.md` — 服务响应缓慢处理方案
- `service_unavailable.md` — 服务不可用处理方案

---

## 常见问题

**Q: 对话中文乱码？**
A: 确保终端/浏览器使用 UTF-8 编码。Windows CMD 使用 `chcp 65001` 切换。

**Q: FAISS 索引损坏？**
A: 删除 `faiss_index/` 目录，重新上传文件即可重建索引。

**Q: DashScope API 连接失败？**
A: 已内置 `verify=False` 兼容企业网络 SSL 检查。如仍有问题，检查防火墙/代理设置。

**Q: 流式对话没效果？**
A: 确认前端切换为"流式"模式。流式使用直接 LLM 调用而非 agent 聚合，可逐 token 输出。

**Q: 监控中心服务列表为空？**
A: Windows 下 psutil 可能需要管理员权限才能获取网络连接信息。确保以管理员权限运行。

**Q: 为什么用 ChatOpenAI 而非 ChatQwen？**
A: Python 3.10 不支持 `typing.Self`（3.11 新增），langchain-qwq 无法导入。DashScope 提供 OpenAI 兼容 API，功能完全等价。

**Q: 为什么用 FAISS 而非 Milvus？**
A: Milvus Lite 在 Windows 上不可用。FAISS 纯 Python 实现，无需 Docker 或外部服务。

---

## License

MIT
