#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: service.py
@time: 2025/05/20
"""
import asyncio
import time
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger

import Core
from Core.Collection import Job, History, JobStatus
from . import Job_c, History_c


# CRUD操作
async def get_job(job_id: int) -> Optional[dict]:
    return Job_c.find_documents(query={"JobId": job_id}, limit=1).dict(0)


async def get_jobs_count(query: dict = None):
    return Job_c.count(query=query)


async def get_jobs(current_page: int = 1, page_size: int = 10, filters=None) -> List[dict]:
    if filters is None:
        filters = {}
    return Job_c.find_documents(query=filters, sort=[("JobId", -1)], limit=page_size,
                                skip=(current_page - 1) * page_size).dict()


async def create_job(job: Job) -> dict:
    if await get_job(job.JobId):
        raise HTTPException(status_code=400, detail="Job ID already exists")
    job_dict = job.dict()
    Job_c.save_dict_to_collection(job_dict)
    return job_dict


async def update_job(job_id: int, job: Job) -> dict:
    result_count = Job_c.save_dict_to_collection(job.dict(), 'JobId')
    if result_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    return await get_job(job_id)


async def delete_job(job_id: int) -> bool:
    deleted_count = Job_c.delete_documents(query={"JobId": job_id})
    return deleted_count > 0


async def create_run_log(log: History) -> dict:
    History_c.save_dict_to_collection(log.dict())
    return log.dict()


async def get_job_logs_count(job_id: int = None, filters: dict = None) -> int:
    query = {}
    if job_id:
        query["JobId"] = job_id
    if filters:
        query.update(filters)
    return History_c.count(query=query)


async def get_job_logs(job_id: int = None, current_page: int = 1, page_size: int = 10, filters=None) -> List[dict]:
    skip = (current_page - 1) * page_size
    query = {}
    if job_id:
        query["JobId"] = job_id
    if filters:
        query.update(filters)
    return History_c.find_documents(query=query, sort=[("StartTime", -1)], limit=page_size, skip=skip).dict()


# 获取最大的RunId
async def get_max_RunId() -> int:
    """获取最大dRunId"""
    history = History_c.find_documents(sort=[("RunId", -1)]).dict(0)
    if history:
        return history.get("RunId") + 1
    else:
        return 100001


def start_async_job(job_id):
    # 获取当前线程的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # 运行异步函数
    loop.run_until_complete(execute_job_core(job_id))
    loop.close()


# 任务执行核心
async def execute_job_core(job_id: int):
    """动态加载并执行任务"""
    job = await get_job(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    history = History(
        JobId=job_id,
        JobName=job.get("JobName"),
        Package=job.get("Package"),
        JobClass=job.get("JobClass"),
        Description=job.get("Description"),
        Status=JobStatus.COMPLETED,
        RunId=None,
        Output='',
        StartTime='',
        EndTime='')
    try:
        job_id = job.get("JobId")
        history.StartTime = str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        run_id = await get_max_RunId()
        history.RunId = run_id
        Core.run(job_id=job_id, run_id=run_id)
    except Exception as e:
        logger.error(f"Job execution failed: {str(e)}")
        history.Output = f"Job execution failed: {str(e)}"
        history.Status = JobStatus.FAILED
    history.EndTime = str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    History_c.save_dict_to_collection(history.dict(), 'RunId')
