"""系统监控服务 — 后台自动检测 + 实时告警"""

import asyncio
from typing import Any, AsyncGenerator, Dict
from datetime import datetime
from loguru import logger
import psutil

# 告警阈值
THRESHOLDS = {
    "cpu": 80,       # CPU 超过 80% 告警
    "memory": 85,     # 内存超过 85% 告警
    "disk": 90,       # 磁盘超过 90% 告警
}

# 告警事件队列 — SSE 推送
_alerts: asyncio.Queue = asyncio.Queue(maxsize=100)


async def push_alert(alert: dict):
    """推送告警到队列"""
    if _alerts.full():
        _ = await _alerts.get()
    await _alerts.put(alert)


async def get_alert_stream() -> AsyncGenerator[Dict[str, Any], None]:
    """SSE 告警流"""
    while True:
        alert = await _alerts.get()
        yield alert


def check_system_now() -> dict:
    """即时检查系统，返回告警列表和指标"""
    alerts = []
    metrics = {}

    # CPU
    try:
        cpu = psutil.cpu_percent(interval=1)
        metrics["cpu"] = round(cpu, 1)
        if cpu > THRESHOLDS["cpu"]:
            alerts.append({
                "type": "cpu", "level": "warning",
                "message": f"CPU 使用率过高: {cpu:.1f}% (阈值 {THRESHOLDS['cpu']}%)",
                "value": round(cpu, 1), "threshold": THRESHOLDS["cpu"],
            })
    except Exception as e:
        metrics["cpu"] = -1
        logger.error(f"CPU 检测失败: {e}")

    # Memory
    try:
        mem = psutil.virtual_memory()
        metrics["memory"] = round(mem.percent, 1)
        if mem.percent > THRESHOLDS["memory"]:
            alerts.append({
                "type": "memory", "level": "warning",
                "message": f"内存使用率过高: {mem.percent:.1f}% (阈值 {THRESHOLDS['memory']}%)",
                "value": round(mem.percent, 1), "threshold": THRESHOLDS["memory"],
            })
    except Exception as e:
        metrics["memory"] = -1
        logger.error(f"内存检测失败: {e}")

    # Disk
    try:
        disk = psutil.disk_usage('/')
        metrics["disk"] = round(disk.percent, 1)
        if disk.percent > THRESHOLDS["disk"]:
            alerts.append({
                "type": "disk", "level": "danger" if disk.percent > 95 else "warning",
                "message": f"磁盘使用率过高: {disk.percent:.1f}% (阈值 {THRESHOLDS['disk']}%)",
                "value": round(disk.percent, 1), "threshold": THRESHOLDS["disk"],
            })
    except Exception as e:
        metrics["disk"] = -1
        logger.error(f"磁盘检测失败: {e}")

    # Network
    try:
        net = psutil.net_io_counters()
        metrics["net_sent_mb"] = round(net.bytes_sent / (1024**2), 1)
        metrics["net_recv_mb"] = round(net.bytes_recv / (1024**2), 1)
    except Exception:
        metrics["net_sent_mb"] = 0
        metrics["net_recv_mb"] = 0

    metrics["process_count"] = len(psutil.pids())
    metrics["timestamp"] = datetime.now().isoformat()

    # Top CPU processes
    try:
        top_procs = sorted(
            [p.info for p in psutil.process_iter(['name', 'cpu_percent', 'memory_info'])
             if p.info['cpu_percent'] and p.info['cpu_percent'] > 0],
            key=lambda x: x['cpu_percent'], reverse=True
        )[:3]
        metrics["top_processes"] = [
            {"name": p['name'], "cpu": round(p['cpu_percent'], 1),
             "mem_mb": round(p['memory_info'].rss / (1024**2)) if p['memory_info'] else 0}
            for p in top_procs
        ]
    except Exception:
        metrics["top_processes"] = []

    return {"alerts": alerts, "metrics": metrics}


async def monitor_loop(interval: int = 10):
    """后台监控循环，每 N 秒检查一次"""
    logger.info(f"系统监控已启动，间隔 {interval}s，阈值: CPU>{THRESHOLDS['cpu']}% MEM>{THRESHOLDS['memory']}% DISK>{THRESHOLDS['disk']}%")

    while True:
        try:
            result = check_system_now()
            for alert in result["alerts"]:
                alert["timestamp"] = datetime.now().isoformat()
                await push_alert(alert)
                logger.warning(f"告警: {alert['message']}")
        except Exception as e:
            logger.error(f"监控循环异常: {e}")

        await asyncio.sleep(interval)


_monitor_task = None


async def start_monitor(interval: int = 10):
    """启动后台监控"""
    global _monitor_task
    if _monitor_task is None or _monitor_task.done():
        _monitor_task = asyncio.create_task(monitor_loop(interval))
        logger.info("后台监控任务已启动")


async def stop_monitor():
    """停止后台监控"""
    global _monitor_task
    if _monitor_task and not _monitor_task.done():
        _monitor_task.cancel()
        logger.info("后台监控任务已停止")
