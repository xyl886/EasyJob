#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: __init__.py
@time: 2025/04/21
"""
# Core/__init__.py

import importlib
import os
import sys
import traceback

from Core.Collection import Job, JobStatus, History
from Core.Config import *
from Core.JobBase import JobBase
from Core.JobRunner import JobRunner
from Core.MongoDB import MongoDB

db = MongoDB(uri=MONGO_URI, db_name=DB_NAME)
Job_c = db['Job']
History_c = db['History']


def run(job_id):
    """运行指定任务"""
    last_history = History_c.find_documents(sort=[("RunId", -1)]).dict(0)
    run_id = last_history.get("RunId") + 1 if last_history else 100001
    runner = JobRunner(job_id, run_id)
    runner.execute()


def auto_import_jobs(base_package=BASE_PACKAGE):
    """
    自动导入所有任务模块
    Automatically import all job modules

    :param base_package: 基础包路径 base package path
    :return: 导入的模块列表 list of imported modules
    """
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
    print(f"JobBase.registry: {sorted(JobBase._registry.keys())}")


def save_jobs():
    # 保存任务
    existing_job_ids = [job['JobId'] for job in Job_c.find_documents()]
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
                Minute="0",
                Hour="0",
                DayOfWeek="*",
                DayOfMonth="*",
                MonthOfYear="*",
                Status=1
            ).dict()
            if job_id not in existing_job_ids:
                Job_c.save_dict_to_collection(job_dict)
        except Exception as e:
            print(f"[AutoImport] Failed to save job {job_id}: {e}")
            traceback.print_exc()


auto_import_jobs()
save_jobs()
__all__ = [
    'Job_c',
    'History_c',
    'run',
    'auto_import_jobs',
    'save_jobs'
]
