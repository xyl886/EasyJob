#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: __init__.py.py
@time: 2025/04/21
"""
# Core/__init__.py

import importlib
import os
import random
import sys
import threading
import time
import traceback

from .Collection import Job
from .JobBase import JobBase
from .MongoDB import MongoDB


class JobThread(threading.Thread):
    """自定义线程，封装异常传递机制"""

    def __init__(self, job_instance):
        super().__init__()
        self.job_instance = job_instance
        self.exc = None  # 保存子线程异常

    def run(self):
        try:
            self.job_instance.on_run()
        except Exception as e:
            self.exc = e  # 捕获子线程异常

    def join(self, timeout=None):
        super().join(timeout)
        if self.exc:
            raise self.exc  # 在主线程重新抛出异常


def run(job_id, run_id=(int(time.time() * 1000) + random.randint(0, 999)) % 10 ** 6):
    if job_id not in JobBase._registry:
        raise ValueError(f"Job ID {job_id} not registered")
    job_class = JobBase._registry.get(job_id)
    job_instance = job_class(job_id=job_id, run_id=run_id)

    try:
        job_instance.logger.warning(f"Starting job: {job_id}")
        # 启动线程运行 on_run
        thread = JobThread(job_instance)
        thread.start()
        thread.join()  # 等待线程完成，并检查异常
        job_instance.logger.warning(f"Job {job_id} completed successfully")
    except Exception as e:
        job_instance.logger.error(f"Job failed: {str(e)}", exc_info=True)
        raise


try:
    import yaml

    with open('config.yaml') as f:
        config = yaml.safe_load(f)
    BASE_PACKAGE = config.get('jobs').get('base_package', 'Job')
    MODULE_PATTERN = config.get('jobs').get('module_pattern', 'Action.py')
except Exception as e:
    print(f"[AutoImport] Failed to load config.yaml: {e}")
    BASE_PACKAGE = 'Job'
    MODULE_PATTERN = 'Action.py'


def auto_import_jobs(base_package=BASE_PACKAGE):
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), base_package)
    modules = []
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(MODULE_PATTERN):
                # 构造模块名
                rel_path = os.path.relpath(os.path.join(root, file), os.path.dirname(os.path.dirname(__file__)))
                module_name = rel_path[:-3].replace(os.sep, '.')
                if module_name in sys.modules:
                    continue  # 已导入，跳过
                try:
                    importlib.import_module(module_name)
                    modules.append(module_name)
                except Exception as e:
                    print(f"[AutoImport] Failed to import {module_name}: {e}")
                    traceback.print_exc()
    print(f"[AutoImport] Auto import jobs completed: {modules}")
    print(f"JobBase._registry: {JobBase._registry}")


def save_jobs():
    job_c = MongoDB(db_name='EasyJob')['Job']
    existing_job_ids = [job['JobId'] for job in job_c.find_documents()]
    for job_id, job_class in JobBase._registry.items():
        job_name = str(job_class.__name__)
        try:
            job_dict = Job(
                JobId=job_id,
                JobName=job_name,
                JobClass=str(job_class.__module__),
                Package=BASE_PACKAGE,
                Description=f'This is {job_name}',
                Disabled=1,
                Minute="*",
                Hour="*",
                DayOfWeek="*",
                DayOfMonth="*",
                MonthOfYear="*",
                Status=1
            ).dict()
            if job_id not in existing_job_ids:
                job_c.save_dict_to_collection(job_dict)
        except Exception as e:
            print(f"[AutoImport] Failed to save job {job_id}: {e}")
            traceback.print_exc()


auto_import_jobs()
save_jobs()
__all__ = ['JobBase', 'run', 'save_jobs']
