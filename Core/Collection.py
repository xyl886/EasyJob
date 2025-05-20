#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: Collection.py
@time: 2025/05/19
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, conint
from typing import Optional


class Job(BaseModel):
    JobId: conint(ge=100000, le=999999) = Field(..., description="任务ID，6位整数")
    JobName: str = Field(..., description="任务名称")
    JobClass: str = Field(..., description="任务对应的类名（字符串）")
    Package: str = Field(..., description="任务所在的包名")
    Description: Optional[str] = Field(None, description="任务描述")
    Disabled: int = Field(0, description="是否禁用：0-启用，1-禁用")
    Minute: str = Field('', description="分钟（Cron表达式）")
    Hour: str = Field('', description="小时（Cron表达式）")
    DayOfWeek: str = Field('', description="星期几（Cron表达式）")
    DayOfMonth: str = Field('', description="每月第几天（Cron表达式）")
    MonthOfYear: str = Field('', description="每年第几月（Cron表达式）")
    Status: int = Field(1, description="状态字段，默认1（可自定义含义）")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": 123456,
                "job_name": "数据同步任务",
                "job_class": "SyncJob",
                "package": "easyjob.jobs",
                "description": "每晚12点同步数据",
                "disabled": 1,
                "Minute": "",
                "Hour": "",
                "DayOfWeek": "",
                "DayOfMonth": "",
                "MonthOfYear": "",
                "status": 1
            }
        }


class History(BaseModel):
    JobId: conint(ge=100000, le=999999) = Field(..., description="任务ID，6位整数")
    RunId: conint(ge=100000, le=999999) = Field(..., description="运行ID，6位整数")
    JobName: str = Field(..., description="任务名称")
    JobClass: str = Field(..., description="任务对应的类名（字符串）")
    Package: str = Field(..., description="任务所在的包名")
    Description: Optional[str] = Field(None, description="任务描述")
    StartTime: str = Field(..., description="开始时间")
    EndTime: str = Field(..., description="结束时间")
    Status: int = Field("pending", description="运行状态")
    Output: Optional[str] = Field(None, description="运行输出")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": 123456,
                "run_id": 123456,
                "job_name": "数据同步任务",
                "job_class": "SyncJob",
                "package": "easyjob.jobs",
                "description": "每晚12点同步数据",
                "start_time": "2023-05-19 12:00:00",
                "end_time": "2023-05-19 12:00:00",
            }
        }


class JobStatus(int, Enum):
    DISABLED = 0
    READY = 1
    RUNNING = 2
    COMPLETED = 3
    FAILED = 4
