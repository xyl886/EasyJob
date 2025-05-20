#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: result.py
@time: 2025/05/20
"""
from typing import TypeVar, Generic, Optional

from pydantic import BaseModel, Field

# 定义通用的响应结构
T = TypeVar('T')


class Result(BaseModel, Generic[T]):
    """
    通用响应结构
    """
    code: int = Field(200, description="状态码")
    message: str = Field("success", description="提示信息")
    data: Optional[T] = Field(None, description="响应数据")


class SuccessResult(Result):
    """
    成功响应结构
    """
    pass


class ErrorResult(Result):
    """
    错误响应结构
    """
    code: int = Field(400, description="状态码")
    message: str = Field("error", description="提示信息")
