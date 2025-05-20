#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: schedule.py
@time: 2025/05/20
"""
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Dict

from .config import Job_c
from .service import execute_job_core

scheduler = AsyncIOScheduler()
# 存储当前任务的缓存
_current_jobs: Dict[str, dict] = {}


async def setup_scheduler():
    """初始化并启动周期性检查"""
    await _update_scheduler()
    asyncio.create_task(_monitor_job_changes())


async def _monitor_job_changes():
    """周期性检查任务变更"""
    while True:
        await asyncio.sleep(30)  # 每30秒检查一次
        await _update_scheduler()
        print("_current_jobs:", _current_jobs)


async def _update_scheduler():
    """更新调度器中的任务"""
    global _current_jobs

    # 获取数据库中所有启用的任务
    db_jobs = {j['JobId']: j for j in Job_c.find_documents({"Disabled": 0}).dict()}

    # 检查新增或修改的任务
    for job_id, job in db_jobs.items():
        if job_id not in _current_jobs or job != _current_jobs[job_id]:
            _add_or_update_job(job)

    # 检查需要删除的任务
    for job_id in list(_current_jobs.keys()):
        if job_id not in db_jobs:
            _remove_job(job_id)

    # 更新缓存
    _current_jobs = db_jobs


def _add_or_update_job(job: dict):
    """添加或更新任务"""
    trigger = CronTrigger(
        minute=job.get("Minute", "*"),
        hour=job.get("Hour", "*"),
        day=job.get("DayOfMonth", "*"),
        month=job.get("MonthOfYear", "*"),
        day_of_week=job.get("DayOfWeek", "*")
    )

    scheduler.add_job(
        execute_job_core,
        trigger,
        args=[job['JobId']],
        id=f"job_{job['JobId']}",
        replace_existing=True
    )


def _remove_job(job_id: str):
    """移除任务"""
    job = scheduler.get_job(f"job_{job_id}")
    if job:
        job.remove()
