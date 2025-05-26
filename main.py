#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: main.py
@time: 2025/05/19
"""
import threading
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI
from fastapi import Query
from starlette.middleware.cors import CORSMiddleware
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from Core import auto_import_jobs, MODULE_PATTERN, BASE_PACKAGE
from Core.Collection import PageInt, JobIdInt, PageSizeInt
from Core.Result import *
from Core.Scheduler import JobScheduler
from Core.Service import *

"""
基于FastAPI的任务调度平台核心实现
"""

# 创建全局调度器实例
job_scheduler = JobScheduler()
# 创建观察者实例
observer = Observer()


class JobFileHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(MODULE_PATTERN):
            auto_import_jobs()


# 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    observer.schedule(JobFileHandler(), path=BASE_PACKAGE, recursive=True)
    observer.start()
    await job_scheduler.start()
    yield
    await job_scheduler.shutdown()


# 创建FastAPI实例
app = FastAPI(
    title="EasyJob Scheduler",
    version="1.0.0",
    lifespan=lifespan
)
# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Specify exact frontend origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
    expose_headers=["Content-Type"],
    max_age=600  # Cache preflight requests for 10 minutes
)


# API路由
@app.post("/jobs/", response_model=Result[Job])
async def add_job(job: Job):
    try:
        job_data = await create_job(job)
        return SuccessResult(data=job_data)
    except HTTPException as e:
        return ErrorResult(code=e.status_code, message=e.detail)
    except Exception as e:
        return ErrorResult(message=str(e))


@app.get("/jobs/", response_model=Result[Dict])
async def list_jobs(
        current_page: PageInt = Query(1, description="当前页码，从1开始"),
        page_size: PageSizeInt = Query(10, description="每页数量，最大100", le=100),
        job_name: Optional[str] = Query(None, description="任务名称模糊查询", max_length=50),
        status: Optional[int] = Query(None, description="任务状态(1-禁用,0-启用)", ge=0, le=1)
):
    """
    获取任务列表
    - current_page: 当前页码(从1开始)
    - page_size: 每页数量(1-100)
    - job_name: 任务名称模糊查询(可选)
    - status: 任务状态筛选(可选,0-禁用,1-启用)
    
    返回格式:
    {
        "items": [],  # 任务列表
        "total": 0,   # 总记录数
        "page": 1,    # 当前页码
        "page_size": 10,  # 每页数量
        "page_count": 1  # 总页数
    }
    """
    try:
        # 添加查询参数过滤
        filters = {}
        if job_name:
            filters["JobName"] = {"$regex": job_name}
        if status is not None:
            filters["Disabled"] = status

        # 获取总数
        total = await get_jobs_count(filters)
        # 计算总页数
        page_count = (total + page_size - 1) // page_size
        # 获取分页数据
        items = await get_jobs(current_page, page_size, filters)

        # 构建返回数据
        result = {
            "items": items,
            "total": total,
            "page": current_page,
            "page_size": page_size,
            "page_count": page_count
        }

        return SuccessResult(data=result)
    except ValueError as e:
        return ErrorResult(message=f"参数错误: {str(e)}", code=400)
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        return ErrorResult(message="服务器内部错误", code=500)


@app.get("/jobs/{job_id}", response_model=Result[Job])
async def get_job_detail(job_id: JobIdInt):
    try:
        job = await get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return SuccessResult(data=job)
    except HTTPException as e:
        return ErrorResult(code=e.status_code, message=e.detail)
    except Exception as e:
        return ErrorResult(message=str(e))


@app.put("/jobs/{job_id}", response_model=Result[Job])
async def update_job_detail(job_id: JobIdInt, job: Job):
    try:
        if job_id != job.JobId:
            raise HTTPException(status_code=400, detail="Job ID mismatch")
        updated_job = await update_job(job_id, job)
        return SuccessResult(data=updated_job)
    except HTTPException as e:
        return ErrorResult(code=e.status_code, message=e.detail)
    except Exception as e:
        return ErrorResult(message=str(e))


@app.delete("/jobs/{job_id}", response_model=Result)
async def remove_job(job_id: JobIdInt):
    try:
        if not await delete_job(job_id):
            raise HTTPException(status_code=404, detail="Job not found")
        return SuccessResult(message="Job deleted successfully")
    except HTTPException as e:
        return ErrorResult(code=e.status_code, message=e.detail)
    except Exception as e:
        return ErrorResult(message=str(e))


@app.post("/jobs/{job_id}/run", response_model=Result)
async def trigger_job(job_id: JobIdInt):
    try:
        job = await get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        thread = threading.Thread(target=start_async_job, args=(job_id,))
        thread.start()
        return SuccessResult(message="Job started in background")
    except HTTPException as e:
        return ErrorResult(code=e.status_code, message=e.detail)
    except Exception as e:
        return ErrorResult(message=str(e))


@app.get("/history", response_model=Result[Dict])
async def get_history(
        current_page: PageInt = Query(1, description="当前页码，从1开始"),
        page_size: PageSizeInt = Query(10, description="每页数量，最大100", le=100),
        job_name: Optional[str] = Query(None, description="任务名称模糊查询", max_length=50),
        status: Optional[int] = Query(None, description="任务状态")

):
    """
    获取任务执行历史记录
    - current_page: 当前页码(从1开始)
    - page_size: 每页数量(1-100)

    返回格式:
    {
        "items": [],  # 历史记录列表
        "total": 0,   # 总记录数
        "page": 1,    # 当前页码
        "page_size": 10,  # 每页数量
        "page_count": 1  # 总页数
    }
    """
    try:
        # 添加查询参数过滤
        filters = {}
        if job_name:
            filters["$or"] = [
                {"JobName": {"$regex": job_name}},
                {"JobId": job_name}
            ]
        if status is not None:
            filters["Status"] = status
        total = await get_job_logs_count(filters=filters)
        page_count = (total + page_size - 1) // page_size
        items = await get_job_logs(current_page=current_page, page_size=page_size,  filters=filters)
        result = {
            "items": items,
            "total": total,
            "page": current_page,
            "page_size": page_size,
            "page_count": page_count
        }
        return SuccessResult(data=result)
    except ValueError as e:
        return ErrorResult(message=f"参数错误: {str(e)}", code=400)
    except Exception as e:
        logger.error(f"获取任务历史失败: {str(e)}")
        return ErrorResult(message="服务器内部错误", code=500)


@app.get("/jobs/{job_id}/history", response_model=Result[Dict])
async def get_job_history(
        job_id: Optional[JobIdInt] = None,  # 可选参数
        current_page: PageInt = Query(1, description="当前页码，从1开始"),
        page_size: PageSizeInt = Query(10, description="每页数量，最大100", le=100),
):
    """
    获取任务执行历史记录
    - job_id: 任务ID(正整数)
    - current_page: 当前页码(从1开始)
    - page_size: 每页数量(1-100)

    返回格式:
    {
        "items": [],  # 历史记录列表
        "total": 0,   # 总记录数
        "page": 1,    # 当前页码
        "page_size": 10,  # 每页数量
        "page_count": 1  # 总页数
    }
    """
    try:
        total = await get_job_logs_count(job_id=job_id)
        page_count = (total + page_size - 1) // page_size
        items = await get_job_logs(job_id=job_id, current_page=current_page, page_size=page_size)
        result = {
            "items": items,
            "total": total,
            "page": current_page,
            "page_size": page_size,
            "page_count": page_count
        }
        return SuccessResult(data=result)
    except ValueError as e:
        return ErrorResult(message=f"参数错误: {str(e)}", code=400)
    except Exception as e:
        logger.error(f"获取任务历史失败: {str(e)}")
        return ErrorResult(message="服务器内部错误", code=500)


# 统计接口
# http://127.0.0.1:8000/docs
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000)
