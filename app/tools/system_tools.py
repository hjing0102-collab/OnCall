"""真实系统监控工具 — CPU、内存、磁盘、进程"""

import psutil
from langchain_core.tools import tool


@tool
def get_cpu_usage() -> str:
    """获取 CPU 使用率详情"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        cpu_avg = sum(cpu_percent) / len(cpu_percent)
        cpu_count = psutil.cpu_count()
        load = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None

        result = f"CPU 核心数: {cpu_count}\n整体使用率: {cpu_avg:.1f}%\n各核心: {cpu_percent}"
        if load:
            result += f"\n系统负载 (1/5/15min): {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}"

        # 最高占用的进程
        procs = sorted(
            [p.info for p in psutil.process_iter(['name', 'cpu_percent']) if p.info['cpu_percent']],
            key=lambda x: x['cpu_percent'], reverse=True
        )[:5]
        if procs:
            result += "\n\nCPU 占用 TOP5 进程:\n"
            for p in procs:
                result += f"  {p['name']}: {p['cpu_percent']:.1f}%\n"
        return result
    except Exception as e:
        return f"获取 CPU 信息失败: {e}"


@tool
def get_memory_usage() -> str:
    """获取内存使用详情"""
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        result = (
            f"物理内存: {mem.used / (1024**3):.1f}GB / {mem.total / (1024**3):.1f}GB ({mem.percent:.1f}%)\n"
            f"  已用: {mem.used / (1024**3):.1f}GB  可用: {mem.available / (1024**3):.1f}GB\n"
        )
        if swap.total > 0:
            result += f"虚拟内存: {swap.used / (1024**3):.1f}GB / {swap.total / (1024**3):.1f}GB ({swap.percent:.1f}%)\n"

        # 最高内存占用的进程
        procs = sorted(
            [p.info for p in psutil.process_iter(['name', 'memory_info']) if p.info['memory_info']],
            key=lambda x: x['memory_info'].rss, reverse=True
        )[:5]
        if procs:
            result += "\n内存占用 TOP5 进程:\n"
            for p in procs:
                result += f"  {p['name']}: {p['memory_info'].rss / (1024**2):.0f}MB\n"
        return result
    except Exception as e:
        return f"获取内存信息失败: {e}"


@tool
def get_disk_usage() -> str:
    """获取磁盘使用详情"""
    try:
        parts = psutil.disk_partitions()
        result = "磁盘使用情况:\n"
        for part in parts:
            try:
                usage = psutil.disk_usage(part.mountpoint)
                result += (
                    f"  {part.device} ({part.mountpoint}): "
                    f"{usage.used / (1024**3):.1f}GB / {usage.total / (1024**3):.1f}GB "
                    f"({usage.percent:.1f}%)\n"
                )
            except Exception:
                continue
        return result.strip()
    except Exception as e:
        return f"获取磁盘信息失败: {e}"


@tool
def get_system_overview() -> str:
    """获取系统整体概览（CPU + 内存 + 磁盘 + 进程数 + 开机时间）"""
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        boot = psutil.boot_time()
        from datetime import datetime
        boot_time = datetime.fromtimestamp(boot).strftime('%Y-%m-%d %H:%M:%S')

        return (
            f"=== 系统概览 ===\n"
            f"CPU: {cpu:.1f}% | 核心: {psutil.cpu_count()}\n"
            f"内存: {mem.used / (1024**3):.1f}G/{mem.total / (1024**3):.1f}G ({mem.percent:.1f}%)\n"
            f"磁盘: {disk.used / (1024**3):.1f}G/{disk.total / (1024**3):.1f}G ({disk.percent:.1f}%)\n"
            f"进程: {len(psutil.pids())} 个\n"
            f"开机: {boot_time}\n"
        )
    except Exception as e:
        return f"获取系统概览失败: {e}"
