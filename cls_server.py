"""CLS 日志查询服务 — 端口 8003（真实日志主题 + 自动采集）"""

import os
import re
import glob
import random
import subprocess
from datetime import datetime, timedelta
from collections import Counter
import os as _os
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from loguru import logger

app = FastAPI(title="CLS Log Server", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

STATIC_DIR = "static"


@app.get("/")
async def root():
    """直接打开 CLS 日志查询页面"""
    path = _os.path.join(STATIC_DIR, "cls.html")
    if _os.path.exists(path):
        return FileResponse(path)
    return {"message": "CLS 日志查询服务", "docs": "/docs", "frontend": "/static/cls.html"}

LOG_STORE = "./cls_logs"

# 每个主题独立的日志文件
TOPIC_SOURCES = {
    "api-access": "cls_logs/api_access.log",
    "system": "cls_logs/system.log",
    "error": "cls_logs/error.log",
    "performance": "cls_logs/performance.log",
    "security": "cls_logs/security.log",
}

TOPIC_INFO = {
    "api-access": {"name": "API 访问日志", "desc": "HTTP 请求记录"},
    "system": {"name": "系统日志", "desc": "服务启停与状态变更"},
    "error": {"name": "错误日志", "desc": "应用异常与堆栈"},
    "performance": {"name": "性能日志", "desc": "CPU/内存/耗时指标"},
    "security": {"name": "安全审计日志", "desc": "登录/鉴权/越权操作"},
}


def _ensure_log_files():
    """确保各主题日志文件存在，首次启动时生成种子数据"""
    os.makedirs(LOG_STORE, exist_ok=True)
    now = datetime.now()

    for topic, path in TOPIC_SOURCES.items():
        if os.path.exists(path) and os.path.getsize(path) > 100:
            continue
        _generate_seed_logs(topic, path, now)


def _generate_seed_logs(topic: str, path: str, now: datetime):
    """生成各主题的种子日志数据"""
    entries = _topic_generators.get(topic, _gen_generic)
    lines = entries(now, 200)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _ts(now, offset_minutes=0):
    t = now - timedelta(minutes=offset_minutes)
    return t.strftime("%Y-%m-%d %H:%M:%S")


def _gen_api_access(now, count):
    methods = ["GET", "POST", "PUT", "DELETE"]
    paths = ["/api/chat", "/api/upload", "/api/aiops", "/api/chat_stream", "/api/health",
             "/api/monitor/now", "/api/index_status", "/api/cls/search"]
    statuses = [200]*70 + [201]*10 + [400]*5 + [401]*5 + [404]*3 + [500]*5 + [502]*2
    levels = ["INFO"]*80 + ["WARNING"]*12 + ["ERROR"]*8
    users = ["admin", "operator", "viewer", "system", "anonymous"]
    ips = ["192.168.1.100", "10.0.0.50", "172.16.0.25", "192.168.1.200", "10.0.0.101"]

    lines = []
    for i in range(count):
        method = random.choice(methods)
        path = random.choice(paths)
        status = random.choice(statuses)
        level = "ERROR" if status >= 500 else ("WARNING" if status >= 400 else "INFO")
        user = random.choice(users)
        ip = random.choice(ips)
        latency = round(random.uniform(2, 500) if status < 400 else random.uniform(500, 5000), 1)
        ts = _ts(now, count - i)
        lines.append(f"{ts} | {level: <8} | api-gateway | {method} {path} HTTP/1.1 | {status} | {latency}ms | user={user} | ip={ip}")
    return lines


def _gen_system(now, count):
    events = [
        ("服务启动", "service.oncall-agent started successfully"),
        ("配置变更", "config.update threshold.cpu: 80 -> 85"),
        ("健康检查", "health.check passed: all 8 services OK"),
        ("定时任务", "cron.cleanup expired sessions: 12 removed"),
        ("文件轮转", "log.rotate app_2026-05-11.log archived"),
        ("扩缩容", "scale.api-gateway replicas: 2 -> 3"),
        ("服务重启", "service.payment-service restarting"),
        ("端口监听", "listening on 0.0.0.0:9900"),
        ("内存告警", "memory.usage exceeded 80% threshold"),
        ("连接池", "db.pool connections: 15/20 active"),
    ]
    levels = ["INFO"]*70 + ["WARNING"]*20 + ["ERROR"]*10
    lines = []
    for i in range(count):
        level = random.choice(levels)
        evt = random.choice(events)
        ts = _ts(now, count - i)
        lines.append(f"{ts} | {level: <8} | system | {evt[1]}")
    return lines


def _gen_error(now, count):
    errors = [
        ("NullPointerException", "java.lang.NullPointerException at com.oncall.service.UserService.getUser(UserService.java:142)"),
        ("TimeoutError", "ConnectionTimeout: api-gateway -> user-service:8081 exceeded 30s"),
        ("OutOfMemory", "java.lang.OutOfMemoryError: Java heap space - heap dump generated"),
        ("DatabaseError", "SQLException: connection pool exhausted (20/20), query: SELECT * FROM orders"),
        ("FileNotFound", "FileNotFoundException: config/production.yaml not found"),
        ("ValidationError", "ValidationError: field 'email' invalid format for user_id=10523"),
        ("PermissionDenied", "AccessDenied: user 'viewer' attempted DELETE /api/admin/users"),
        ("RateLimitExceeded", "RateLimitExceeded: IP 10.0.0.101 exceeded 1000 req/min"),
        ("DiskSpaceLow", "DiskSpaceWarning: /var/log at 92% capacity"),
        ("SSLExpired", "SSLCertificateExpired: api.oncall.com cert expires in 3 days"),
    ]
    lines = []
    for i in range(count):
        err = random.choice(errors)
        ts = _ts(now, count - i)
        lines.append(f"{ts} | ERROR    | {err[0]} | {err[1]}")
        # 偶尔添加堆栈跟踪
        if random.random() < 0.3:
            lines.append(f"{ts} | ERROR    | {err[0]} |   at com.oncall.handler.ExceptionHandler.handle(Unknown Source)")
            lines.append(f"{ts} | ERROR    | {err[0]} |   at com.oncall.filter.ErrorFilter.doFilter(ErrorFilter.java:56)")
    return lines


def _gen_performance(now, count):
    lines = []
    for i in range(count):
        cpu = round(random.uniform(15, 95), 1)
        mem = round(random.uniform(40, 92), 1)
        disk = round(random.uniform(50, 88), 1)
        qps = random.randint(50, 800)
        p99 = round(random.uniform(20, 2000), 1)
        ts = _ts(now, count - i)

        level = "ERROR" if cpu > 90 or mem > 90 else ("WARNING" if cpu > 70 or mem > 80 else "INFO")
        lines.append(f"{ts} | {level: <8} | perf | cpu={cpu}% mem={mem}% disk={disk}% qps={qps} p99={p99}ms")
    return lines


def _gen_security(now, count):
    events = [
        ("login_success", "user=admin ip=192.168.1.100 method=password"),
        ("login_failed", "user=root ip=10.0.0.200 method=password reason=bad_credentials"),
        ("login_success", "user=operator ip=172.16.0.25 method=token"),
        ("permission_denied", "user=viewer action=DELETE /api/admin/config ip=192.168.1.200"),
        ("token_expired", "user=operator token_id=tk-88423 age=25h"),
        ("api_key_created", "user=admin key_name=monitoring-bot scope=read"),
        ("login_failed", "user=admin ip=10.0.0.150 method=password reason=bad_credentials"),
        ("brute_force_detect", "ip=10.0.0.150 failed_attempts=15 window=5min action=blocked"),
        ("config_access", "user=operator action=read config/production.yaml"),
        ("sudo_operation", "user=admin command=systemctl restart oncall-agent"),
    ]
    levels = ["INFO"]*60 + ["WARNING"]*25 + ["ERROR"]*15
    lines = []
    for i in range(count):
        level = random.choice(levels)
        evt = random.choice(events)
        ts = _ts(now, count - i)
        lines.append(f"{ts} | {level: <8} | security | {evt[0]} | {evt[1]}")
    return lines


def _gen_generic(now, count):
    return [f"{_ts(now, count-i)} | INFO     | generic | log entry {i+1}" for i in range(count)]


_topic_generators = {
    "api-access": _gen_api_access,
    "system": _gen_system,
    "error": _gen_error,
    "performance": _gen_performance,
    "security": _gen_security,
}


def _read_topic_logs(topic: str, max_lines: int = 2000) -> list:
    """读取指定主题的日志"""
    path = TOPIC_SOURCES.get(topic)
    if not path or not os.path.exists(path):
        _ensure_log_files()
    lines = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
            if max_lines > 0 and len(all_lines) > max_lines:
                all_lines = all_lines[-max_lines:]
            lines = [l.strip() for l in all_lines if l.strip()]
    except Exception:
        pass
    return lines


def _append_to_topic(topic: str, line: str):
    """追加日志到主题文件"""
    path = TOPIC_SOURCES.get(topic)
    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def _parse_log_line(line: str, topic: str) -> dict:
    """解析日志行"""
    level = "INFO"
    for lv in ["ERROR", "WARNING", "INFO", "DEBUG"]:
        if f"| {lv}" in line:
            level = lv
            break

    timestamp = ""
    match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', line)
    if match:
        timestamp = match.group(1)

    source = topic
    match2 = re.search(r'\|\s*(\w+)\s*\|', line)
    if match2 and match2.group(1) not in ("ERROR", "WARNING", "INFO", "DEBUG"):
        source = match2.group(1)

    return {"timestamp": timestamp, "level": level, "topic": topic, "source": source, "message": line}


def _collect_logs() -> str:
    """自动采集：从 app 日志 + 系统状态生成新日志条目"""
    now = datetime.now()
    ts = now.strftime("%Y-%m-%d %H:%M:%S")

    # 从真实 app 日志采集 ERROR/WARNING
    app_logs = glob.glob("logs/app_*.log")
    if app_logs:
        latest = sorted(app_logs)[-1]
        try:
            with open(latest, "r", encoding="utf-8", errors="ignore") as f:
                recent = f.readlines()[-20:]
                for line in recent:
                    line = line.strip()
                    if not line:
                        continue
                    if "| ERROR" in line:
                        _append_to_topic("error", line)
                    elif "| WARNING" in line:
                        _append_to_topic("error", line)
        except Exception:
            pass

    import psutil
    cpu = psutil.cpu_percent(interval=0.3)
    mem = psutil.virtual_memory().percent
    disk_use = psutil.disk_usage('/').percent

    _append_to_topic("performance",
                     f"{ts} | {'ERROR' if cpu > 90 or mem > 90 else 'WARNING' if cpu > 70 or mem > 80 else 'INFO'}     | perf | cpu={cpu}% mem={mem}% disk={disk_use}%")
    return ts


# 初始化日志文件
_ensure_log_files()


# ==================== API ====================

@app.get("/api/cls/timestamp")
async def get_current_timestamp():
    now = datetime.now()
    return JSONResponse(content={"code": 200, "data": {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp_ms": int(now.timestamp() * 1000),
        "timezone": "Asia/Shanghai",
    }})


@app.get("/api/cls/collect")
async def collect_now():
    """手动触发日志采集"""
    ts = _collect_logs()
    return JSONResponse(content={"code": 200, "message": f"采集完成 {ts}"})


@app.get("/api/cls/topics")
async def get_topic_info_by_name(name: str = Query(None)):
    topics = []
    for key, info in TOPIC_INFO.items():
        if name and name not in key and name not in info["name"]:
            continue
        logs = _read_topic_logs(key, 500)
        topics.append({
            "topic_id": key,
            "topic_name": info["name"],
            "description": info["desc"],
            "log_count": len(logs),
            "source_file": TOPIC_SOURCES[key],
            "retention_days": 30,
        })
    return JSONResponse(content={"code": 200, "data": {"topics": topics}})


@app.get("/api/cls/search")
async def search_log(
    topic: str = Query("", description="日志主题，空=全部"),
    query: str = Query("", description="关键词"),
    level: str = Query("", description="日志级别"),
    limit: int = Query(100, description="返回条数"),
):
    # 确定要查询的主题
    topics_to_search = [topic] if topic and topic in TOPIC_SOURCES else list(TOPIC_SOURCES.keys())
    effective_limit = limit if limit > 0 else 99999

    all_results = []
    for t in topics_to_search:
        lines = _read_topic_logs(t, effective_limit if effective_limit > 500 else 500)
        for line in reversed(lines):
            line_upper = line.upper()
            if level and level.upper() not in line_upper:
                continue
            if query and query.lower() not in line.lower():
                continue
            all_results.append(_parse_log_line(line, t))
            if len(all_results) >= effective_limit:
                break
        if len(all_results) >= effective_limit:
            break

    return JSONResponse(content={"code": 200, "data": {
        "total": len(all_results),
        "topic": topic or "all",
        "level": level or "all",
        "query": query,
        "logs": all_results[:effective_limit],
    }})


@app.get("/api/cls/service-logs")
async def search_service_logs(
    service_name: str = Query(""),
    level: str = Query(""),
    limit: int = Query(100),
):
    return await search_log(topic="", query=service_name, level=level, limit=limit)


@app.get("/api/cls/analyze")
async def analyze_log_pattern(
    topic: str = Query("", description="日志主题，空=全部"),
    hours: int = Query(24),
):
    topics_to_search = [topic] if topic and topic in TOPIC_SOURCES else list(TOPIC_SOURCES.keys())

    level_counts = Counter()
    source_counts = Counter()
    all_results = []
    total = 0

    for t in topics_to_search:
        lines = _read_topic_logs(t, 500)
        for line in lines:
            if not line:
                continue
            total += 1
            parsed = _parse_log_line(line, t)
            all_results.append(parsed)
            level_counts[parsed["level"]] += 1
            source_counts[parsed["source"]] += 1

    error_total = level_counts.get("ERROR", 0)
    warn_total = level_counts.get("WARNING", 0)
    error_rate = round(error_total / total * 100, 2) if total > 0 else 0

    top_sources = [{"source": s, "count": c} for s, c in source_counts.most_common(10)]

    patterns = []
    if error_rate > 15:
        patterns.append({"pattern": "高错误率", "severity": "danger", "detail": f"错误率 {error_rate}% 超过 15%"})
    elif error_rate > 5:
        patterns.append({"pattern": "错误率偏高", "severity": "warning", "detail": f"错误率 {error_rate}%"})
    if warn_total > total * 0.15:
        patterns.append({"pattern": "大量警告", "severity": "warning", "detail": f"警告占比 {round(warn_total/total*100,1)}%"})
    if total < 50:
        patterns.append({"pattern": "日志量偏低", "severity": "info", "detail": "日志条目较少，可能采集未正常工作"})
    if not patterns:
        patterns.append({"pattern": "日志模式正常", "severity": "info", "detail": "未发现异常模式"})

    return JSONResponse(content={"code": 200, "data": {
        "topic": topic or "all",
        "hours": hours,
        "total_lines": total,
        "level_distribution": dict(level_counts),
        "top_sources": top_sources,
        "error_rate": error_rate,
        "patterns": patterns,
        "summary": f"分析 {total} 条日志: ERROR={error_total}, WARNING={warn_total}, INFO={level_counts.get('INFO',0)}, 错误率={error_rate}%",
        "recent_logs": [{
            "timestamp": r["timestamp"], "level": r["level"], "topic": r["topic"], "message": r["message"][:200]
        } for r in all_results[-20:]],
    }})


if __name__ == "__main__":
    import uvicorn
    # 启动时自动采集
    _collect_logs()
    logger.info("CLS 日志服务启动: http://0.0.0.0:8003")
    uvicorn.run(app, host="0.0.0.0", port=8003)
