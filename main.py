#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: main.py
@time: 2025/05/19
"""
import threading
from contextlib import asynccontextmanager
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from Core import auto_import_jobs, MODULE_PATTERN, BASE_PACKAGE

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
    auto_import_jobs()
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


@app.get("/jobs/", response_model=Result[List[Job]])
async def list_jobs():
    try:
        jobs = await get_all_jobs()
        return SuccessResult(data=jobs)
    except Exception as e:
        return ErrorResult(message=str(e))


@app.get("/jobs/{job_id}", response_model=Result[Job])
async def get_job_detail(job_id: int):
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
async def update_job_detail(job_id: int, job: Job):
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
async def remove_job(job_id: int):
    try:
        if not await delete_job(job_id):
            raise HTTPException(status_code=404, detail="Job not found")
        return SuccessResult(message="Job deleted successfully")
    except HTTPException as e:
        return ErrorResult(code=e.status_code, message=e.detail)
    except Exception as e:
        return ErrorResult(message=str(e))


@app.post("/jobs/{job_id}/run", response_model=Result)
async def trigger_job(job_id: int):
    try:
        job = await get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job["Disabled"] == 1:
            raise HTTPException(status_code=400, detail="Job is disabled")
        threading.Thread(target=execute_job_core, args=(job_id,)).start()
        return SuccessResult(message="Job started in background")
    except HTTPException as e:
        return ErrorResult(code=e.status_code, message=e.detail)
    except Exception as e:
        return ErrorResult(message=str(e))


@app.get("/jobs/{job_id}/history", response_model=Result[List[History]])
async def get_job_history(job_id: int, limit: int = 10):
    try:
        histories = await get_job_logs(job_id, limit)
        return SuccessResult(data=histories)
    except Exception as e:
        return ErrorResult(message=str(e))


# http://127.0.0.1:8000/docs
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000)
