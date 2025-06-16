#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: schedule.py
@time: 2025/05/20
"""
# Scheduler.py
import asyncio
import time
from typing import Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from watchdog.events import FileSystemEventHandler

from Core import Job_c, save_jobs, auto_import_jobs, MODULE_PATTERN
from Core.Service import execute_job_core


class JobScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._current_jobs: Dict[str, dict] = {}

    async def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
        await self._update_scheduler()
        asyncio.create_task(self.run_periodic_task())
        asyncio.create_task(self._monitor_job_changes())

    async def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()

    async def run_periodic_task(self):
        """定时刷新Job"""
        while True:
            await asyncio.sleep(60)
            save_jobs()

    async def _monitor_job_changes(self):
        """周期性检查任务变更"""
        while True:
            await asyncio.sleep(30)  # 每30秒检查一次
            await self._update_scheduler()
            # print("_current_jobs:", self._current_jobs)

    async def _update_scheduler(self):
        """更新调度器中的任务"""
        # 获取数据库中所有启用的任务
        db_jobs = {j['JobId']: j for j in Job_c.find_documents({"Disabled": 0}).dict()}

        # 检查新增或修改的任务
        for job_id, job in db_jobs.items():
            if job_id not in self._current_jobs or job != self._current_jobs[job_id]:
                self._add_or_update_job(job)

        # 检查需要删除的任务
        for job_id in list(self._current_jobs.keys()):
            if job_id not in db_jobs:
                self._remove_job(job_id)

        # 更新缓存
        self._current_jobs = db_jobs

    def _add_or_update_job(self, job: dict):
        """添加或更新任务"""
        trigger = CronTrigger(
            minute=job.get("Minute", "0"),
            hour=job.get("Hour", "0"),
            day=job.get("DayOfMonth", "*"),
            month=job.get("MonthOfYear", "*"),
            day_of_week=job.get("DayOfWeek", "*")
        )

        self.scheduler.add_job(
            execute_job_core,
            trigger,
            args=[job['JobId']],
            id=f"job_{job['JobId']}",
            replace_existing=True
        )

    def _remove_job(self, job_id: str):
        """移除任务"""
        job = self.scheduler.get_job(f"job_{job_id}")
        if job:
            job.remove()


class JobFileHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_trigger = 0  # 防抖计时

    def on_modified(self, event):
        # 过滤目录和临时文件
        if event.is_directory or not event.src_path.endswith(MODULE_PATTERN):
            return

        # 防抖机制（1秒内不重复触发）
        current_time = time.time()
        if current_time - self.last_trigger < 1.0:
            return

        self.last_trigger = current_time
        print(f"Reloading jobs from {event.src_path}")
        try:
            auto_import_jobs()  # 确保此函数线程安全
        except Exception as e:
            print(f"Job reload failed: {e}")
