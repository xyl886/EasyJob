#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: service.py
@time: 2025/05/20
"""
import asyncio
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger

import Core
from Core import Job_c, History_c
from Core.Collection import Job, History, JobStatus


async def get_statistics(days: int = 7) -> Optional[dict]:
    from datetime import datetime, timedelta
    now = datetime.now()

    # 计算一周前的日期
    day_ago = (now - timedelta(days=days)).strftime('%Y-%m-%d')

    # 生成过去一周的日期列表
    date_list = reversed([
        (now - timedelta(days=i)).strftime('%Y-%m-%d')
        for i in range(days)
    ])

    pipeline = [
        # 过滤出最近一周的记录
        {
            "$match": {
                "StartTime": {
                    "$gte": day_ago
                }
            }
        },
        # 将 StartTime 字符串转换为日期对象
        {
            "$addFields": {
                "dateObj": {"$dateFromString": {"dateString": "$StartTime"}}
            }
        },
        # 按日期分组，并计算不同状态的数量
        {
            "$group": {
                "_id": {
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$dateObj"}}
                },
                "running": {
                    "$sum": {"$cond": [{"$eq": ["$Status", JobStatus.RUNNING]}, 1, 0]}
                },
                "failure": {
                    "$sum": {"$cond": [{"$eq": ["$Status", JobStatus.FAILED]}, 1, 0]}
                },
                "success": {
                    "$sum": {"$cond": [{"$eq": ["$Status", JobStatus.COMPLETED]}, 1, 0]}
                }
            }
        },
        # 投影出需要的字段
        {
            "$project": {
                "_id": 0,
                "date": "$_id.date",
                "running": 1,
                "failure": 1,
                "success": 1
            }
        },
        # 按日期升序排序
        {
            "$sort": {"date": 1}
        }
    ]
    statistics = History_c.aggregate(pipeline=pipeline)
    statistics_dict = {stat['date']: stat for stat in statistics}
    result = [
        statistics_dict.get(date, {
            "date": date,
            "running": 0,
            "failure": 0,
            "success": 0
        })
        for date in date_list
    ]
    total, disabled, running = await asyncio.gather(
        get_jobs_count(),
        get_jobs_count({"Disabled": 1}),
        get_jobs_count({"Disabled": 0})
    )
    statistics_data = {
        "jobsTotal": total,
        'disabled': disabled,
        'running': running,
        "statistics": result
    }
    return statistics_data


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
    try:
        Core.run(job_id=job_id)
    except Exception as e:
        logger.error(f"Job execution failed: {str(e)}")


if __name__ == '__main__':
    # 获取当前线程的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # 运行异步函数
    loop.run_until_complete(get_statistics())
    loop.close()
