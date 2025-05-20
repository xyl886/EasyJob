#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: service.py
@time: 2025/05/20
"""
import random
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


async def get_all_jobs() -> List[dict]:
    return Job_c.find_documents().dict()


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


async def get_job_logs(job_id: int, limit: int = 10) -> List[dict]:
    return History_c.find_documents(query={"JobId": job_id}, sort="StartTime", limit=limit).dict()


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
        RunId=100000,
        Output="",
        StartTime='',
        EndTime="")
    try:
        job_id = job.get("JobId")
        history.StartTime = str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        run_id = (int(time.time() * 1000) + random.randint(0, 999)) % 10 ** 6
        history.RunId = run_id
        Core.run(job_id=job_id, run_id=run_id)
    except Exception as e:
        logger.error(f"Job execution failed: {str(e)}")
        history.Output = f"Job execution failed: {str(e)}"
        history.Status = JobStatus.FAILED
    history.EndTime = str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    History_c.save_dict_to_collection(history.dict())
