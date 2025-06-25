#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: JobBase.py
@time: 2025/06/15
"""
import datetime
import hashlib
import logging
import os
import sys
import time
from contextlib import ContextDecorator
from functools import wraps
from typing import Union, Tuple, Callable, Optional, Dict, List

import pandas as pd
import requests
from loguru import logger
from requests import RequestException, ReadTimeout, ConnectTimeout
from requests.models import HTTPError

from Core.Config import content_type_ext
from Core.EntityBase import EntityBase
from Core.FileLock import FileLock
from Core.MongoDB import MongoDB


# 自定义exception
class JobException(Exception):
    pass


def retry(
        retries: int = 5,  # 重试次数
        delay: Union[int, float] = 1,  # 延迟时间
        max_delay: Union[int, float] = 8,  # 最大延迟时间
        backoff: Union[int, float] = 2,  # 延迟倍数
        exceptions: Tuple[Exception] = (RequestException, ReadTimeout, HTTPError, ConnectTimeout, JobException),
        # 捕获的异常类型
        log_args: bool = True  # 是否记录参数
):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(f"Function called: {func_name}")

            if log_args:
                logger.debug(f"Params - args: {args}, kwargs: {kwargs}")

            for attempt in range(retries + 1):
                try:
                    response = func(*args, **kwargs)
                    logger.debug(f"[{func_name}] Attempt {attempt + 1} success")
                    return response

                except exceptions as e:
                    final_error = e
                    if attempt < retries:
                        sleep_time = min(delay * (backoff ** attempt), max_delay)
                        logger.error(
                            f"[{func_name}] Attempt {attempt + 1} failed: {str(e)} "
                            f"Retrying in {sleep_time}s..."
                        )
                        time.sleep(sleep_time)
                    else:
                        # 最后一次失败后记录错误详情
                        error_log = (
                            f"[FINAL FAILURE] {func_name} after {retries} retries\n"
                            f"Params: args={args}, kwargs={kwargs}\n"
                            f"Error: {str(final_error)}"
                        )
                        logger.error(error_log)
                        raise final_error
                except Exception as unexpected_error:
                    # 捕获未预期的异常，立即终止并记录
                    logger.critical(
                        f"[UNEXPECTED ERROR] Attempt {attempt} failed:\n"
                        f"Params: args={args}, kwargs={kwargs}\n"
                        f"Error: {unexpected_error}"
                    )
                    raise unexpected_error
            return None

        return wrapper

    return decorator


class MongoDBHandler:
    """自定义MongoDB日志处理器（仅记录ERROR及以上级别）
        self.db = MongoDB(db_name=self.db_name, log_enabled=False)
        self.log_handler = MongoDBHandler(db=self.db, db_name=self.db_name, job_id=self.job_id, run_id=self.run_id)
        self.logger = self.log_handler.logger
    """

    def __init__(self, **kwargs):
        super().__init__()
        self.db = kwargs.get('db')
        self.db_name = kwargs.get('db_name')
        self.log_c = self.db['log']
        self.job_id = kwargs.get('job_id')
        self.run_id = kwargs.get('run_id')
        # DEBUG < INFO < WARNING < ERROR < CRITICAL
        self.default_log_level_no = kwargs.get('default_log_level_no', logging.INFO)
        self._setup_logging()

    def emit(self, message):
        record = message.record

        if record["level"].no < self.default_log_level_no:
            return

        log_entry = {
            'job_id': self.job_id,
            'run_id': self.run_id,
            'timestamp': record["time"].astimezone().replace(tzinfo=None),
            'level': record["level"].no,
            'message': record["message"],
            'logger': f"{self.db_name}.{self.job_id}",
            'module': record["module"],
            'lineno': record["line"]
        }

        try:
            self.log_c.save_dict_to_collection(log_entry)
        except Exception as e:
            print(f"Error logging to MongoDB: {e}")

    def _setup_logging(self):
        """配置日志记录，使用 loguru"""
        # 移除所有已有的日志处理器
        logger.remove()

        # 添加控制台处理器，使用默认格式并记录所有级别
        logger.add(sys.stderr, level="DEBUG")
        # DEBUG < INFO < WARNING < ERROR < CRITICAL
        logger.add(
            self.emit,
            level="INFO",
            format=""
        )
        self.logger = logger.bind(logger_name=f"{self.db_name}.{self.job_id}")


class JobContext(ContextDecorator):
    def __init__(self, job_instance):
        self.job = job_instance
        self.previous = EntityBase.get_current_job()  # 使用安全访问方法

    def __enter__(self):
        EntityBase.set_current_job(self.job)  # 使用安全设置方法
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        EntityBase.set_current_job(self.previous)
        return False


def protect_on_run(on_run_method):
    """装饰器：自动为on_run方法添加上下文保护"""

    @wraps(on_run_method)
    def wrapper(self, *args, **kwargs):
        with JobContext(self):
            return on_run_method(self, *args, **kwargs)
        return None

    return wrapper


class JobBaseMeta(type):
    """元类：自动为子类的on_run方法添加保护"""

    def __new__(cls, name, bases, attrs):
        if name != "JobBase" and "on_run" not in attrs:
            raise TypeError(f"Job subclass {name} must implement 'on_run' method")
        # 装饰当前类定义的on_run
        if "on_run" in attrs:
            attrs["on_run"] = protect_on_run(attrs["on_run"])
        return super().__new__(cls, name, bases, attrs)


class JobBase(metaclass=JobBaseMeta):
    """任务基类"""
    _registry = {}

    def __init_subclass__(cls, **kwargs):
        """自动注册子类，支持多个 job_id"""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'job_id'):
            # 将 job_id 转换为可迭代对象（支持列表、元组、集合或单个值）
            if not hasattr(cls, 'job_id'):
                raise ValueError(f"{cls.__name__} must define 'job_id' attribute")
            job_ids = cls.job_id
            if not isinstance(job_ids, (list, tuple, set)):
                job_ids = [job_ids]
            # 遍历所有 job_id 并注册
            for job_id in job_ids:
                if job_id in JobBase._registry:
                    raise ValueError(f"JobId {job_id} already registered by {JobBase._registry[job_id].__name__}")
                JobBase._registry[job_id] = cls
        # 处理 folder 路径的代码保持不变
        if hasattr(cls, 'folder'):
            cls.folder = os.path.join(os.path.dirname(__file__), cls.folder)
        # 获取date
        if hasattr(cls, 'date'):
            cls.date = cls.date
        else:
            cls.date = str(datetime.datetime.now().strftime("%Y-%m-%d"))

    def __init__(self, *args, **kwargs):
        self.job_id = kwargs.get('job_id')
        self.run_id = kwargs.get('run_id')
        self.retry_count = kwargs.get('retry', 30)
        self.InsertUpdateTime = str(datetime.datetime.now())
        self.job_name = self.__class__.__name__
        self.default_log_level_no = logging.INFO
        self.db = MongoDB(db_name=self.job_name, log_enabled=kwargs.get('log_enabled', False))
        self.log_handler = MongoDBHandler(db=self.db, db_name=self.job_name, job_id=self.job_id, run_id=self.run_id)
        self.logger = self.log_handler.logger
        self.log = self.log_handler.logger
        if not hasattr(self, 'folder'):
            raise ValueError(f"Folder not found in {self.__class__.__name__} job_id:{self.job_id}")
        if not hasattr(self, 'date'):
            self.date = str(datetime.datetime.now().strftime("%Y-%m-%d"))

    def on_run(self):
        """任务执行入口，子类重写此方法"""
        raise NotImplementedError("Subclasses must implement the on_run method")

    def md5_encrypt(self, text):
        """
        MD5 加密
        :param text:
        :return:
        """
        md5 = hashlib.md5()
        md5.update(str(text).encode('utf-8'))
        return md5.hexdigest()

    @logger.catch
    @retry(3)
    def send_request(
            self,
            url: str,
            method: str = 'GET',
            params: Optional[Dict] = None,
            data: Optional[Dict] = None,
            json_data: Optional[Dict] = None,
            headers: Optional[Dict[str, str]] = None,
            cookies: Optional[Dict[str, str]] = None,
            timeout: Union[int, float] = 10,
            encoding: Optional[str] = None,
            allow_redirects: bool = True,
            proxies: Optional[Dict[str, str]] = None,
            dump_file_name: Optional[str] = None,
            res_type: str = 'text',
            read_dump: bool = True,
            raise_for_status: bool = True,
            validate_str_list: Optional[List[str]] = None
    ) -> Union[str, dict, bytes]:
        """
        发送 GET 请求获取网页内容，支持缓存、自动重试和多种返回格式。

        Args:
            url (str): 目标 URL 地址。
            method(str): get, post
            params(dict): dict
            data(dict): dict
            json_data(dict): json
            headers (dict, optional): 自定义请求头，默认为 None。
            cookies (dict, optional): 自定义 Cookies，默认为 None。
            timeout (int/float, optional): 请求超时时间（秒），默认为 10。
            encoding (str, optional): 手动指定响应编码（如 'utf-8'、'gbk'），默认自动检测。
            allow_redirects (bool, optional): 是否允许重定向，默认为 True。
            proxies (dict, optional): 代理配置（如 {'http': 'http://10.10.1.10:3128'}）。
            dump_file_name (str, optional): 缓存文件名，若存在则优先读取缓存。
            res_type (str, optional): 返回类型，可选 'text'（文本）、'json'（字典）、'content'（二进制），默认为 'text'。
            read_dump (bool, optional): 是否读取缓存，默认为 True。
            raise_for_status (bool, optional): 是否在 HTTP 错误码时抛出异常，默认为 True。
            validate_str_list(str,optional): 根据传入的str，对响应进行校验，决定是否重试
        Returns:
            str/dict/bytes: 根据 res_type 返回响应内容。

        Raises:
            ValueError: 参数错误或不受支持的 res_type。
            requests.exceptions.RequestException: 网络请求异常。
            requests.exceptions.HTTPError: 当 raise_for_status=True 时，HTTP 状态码非 2xx 抛出。
        """
        if validate_str_list is None:
            validate_str_list = []
        # 尝试读取缓存文件（当不强制刷新时）
        res = None
        if read_dump and dump_file_name is not None:
            res = self.get_dump(file_name=dump_file_name)
        # 若缓存不存在或强制刷新，则发起请求
        if res is None or not read_dump:
            try:
                response = requests.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    json=json_data,
                    headers=headers,
                    cookies=cookies,
                    timeout=timeout,
                    allow_redirects=allow_redirects,
                    proxies=proxies
                )

                # 触发 HTTP 状态码异常检查
                if raise_for_status:
                    response.raise_for_status()

                # 手动覆盖响应编码（优先级高于响应头）
                if encoding is not None:
                    response.encoding = encoding
                else:
                    response.encoding = response.apparent_encoding
            except RequestException as e:
                self.logger.error(f"request failed: {e}")  # 可选日志记录
                raise JobException(e)  # 触发 retry 装饰器重试
            try:
                if res_type == 'text':
                    res = response.text
                elif res_type == 'json':
                    res = response.json()
                elif res_type == 'content':
                    res = response.content
                else:
                    error_msg = f"failed to parse the response not supported res_type: {res_type}，可选 'text', 'json', 'content'"
                    self.logger.error(error_msg)
                    raise JobException(error_msg)
            except Exception as e:
                error_msg = f"failed to parse the response: {e}"
                self.logger.error(error_msg)
                raise JobException(error_msg)
            # 通过 validate_str_list对响应校验，决定是否重试
            for each_validate_str in validate_str_list:
                if each_validate_str not in str(res):
                    self.logger.info(f"url: {url} str: {each_validate_str} request failed，on retry...")
                    raise JobException(f"请求失败, {each_validate_str} not in res")
            if dump_file_name is not None and res is not None:
                try:
                    self.dump(res, file_name=dump_file_name, res_type=res_type)  # 假设 dump 方法能处理不同类型数据
                except Exception as e:
                    error_msg = f"failed to save the cache file: {e}"
                    self.logger.error(error_msg)
                    raise JobException(f"failed to save the cache file: {e}")
        return res

    def dump(self, res_text, file_name: str, res_type: str = "text"):
        """
        将内容保存到指定路径

        Args:
            res_text: 要保存的内容（根据res_type可以是文本、json对象或二进制内容）
            file_name: 完整的文件保存路径（如 `data/dump_2023.txt`）
            res_type: 内容类型，可选值：
                - "text": 文本内容（默认）
                - "json": JSON对象
                - "content": 二进制内容（如图片等）
        """
        if file_name is None:
            raise ValueError("file_name cannot be None")
        if res_text is None:
            raise ValueError("res_text cannot be None")
        # 自动创建父目录（如果不存在）
        save_folder = os.path.join(self.folder, self.date)
        file_path = os.path.join(save_folder, file_name)
        file_dir = os.path.dirname(file_path)
        if file_dir:  # 确保目录路径非空
            os.makedirs(file_dir, exist_ok=True)
        # 处理不同内容类型
        file_path = os.path.join(save_folder, file_name)
        lock = FileLock.get_lock(file_path)  # 获取该路径的专属锁
        with lock:
            if res_type == "text":
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(str(res_text))
            elif res_type == "json":
                import json
                with open(file_path, "w", encoding="utf-8", errors="replace") as f:
                    json.dump(res_text, f, ensure_ascii=False, indent=2)
            elif res_type == "content":
                with open(file_path, "wb") as f:
                    f.write(res_text)
            else:
                raise ValueError(f"Invalid res_type: {res_type}. Must be one of 'text', 'json', or 'content'")
            self.logger.success(f'Saved file {file_name} to {save_folder}')

    def get_dump(self, file_name: str, date=None):
        """
        从指定路径读取已保存的内容，根据文件扩展名自动推断内容类型

        Args:
            file_name: 文件名称
            date: 可指定dump日期 %Y-%m-%d

        Returns:
            读取到的内容，自动根据文件扩展名返回：
            - .json 文件：返回解析后的JSON对象
            - 图片等二进制文件：返回二进制内容
            - 其他：返回文本内容

        Raises:
            FileNotFoundError: 文件不存在时抛出
            ValueError: 文件名无效时抛出
        """
        # 参数验证
        if not file_name or not isinstance(file_name, str) or file_name is None:
            raise ValueError("file_name cannot be empty")

        # 确定日期目录,如果没有传入参数date，则尝试获取子类初始化的date
        target_date = date or self.date
        if not target_date:
            raise ValueError("Date must be provided or set in instance")

        # 构建完整文件路径
        save_dir = os.path.join(self.folder, target_date)
        save_path = os.path.join(save_dir, file_name)
        # 检查文件是否存在
        if not os.path.exists(save_path):
            self.logger.warning(f"File not found: {save_path}")
            return None
        try:
            # 获取文件扩展名
            _, ext = os.path.splitext(file_name)
            ext = ext.lower()  # 统一小写处理
            self.logger.info(f'read cache {file_name}')
            lock = FileLock.get_lock(save_path)  # 获取该路径的专属锁
            with lock:
                if ext == '.json':
                    import json
                    with open(save_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                elif ext in [v.lower() for v in content_type_ext.values()]:
                    with open(save_path, "rb") as f:
                        return f.read()
                else:  # 默认按文本处理
                    with open(save_path, "r", encoding="utf-8") as f:
                        return f.read()
        except Exception as e:
            self.logger.error(f"Error reading file {save_path}: {str(e)}")
            raise  # 重新抛出异常

    def flatten_dict(self,
                     nested_dict,
                     parent_key='',
                     key_separator='_',
                     value_separator=',',
                     result=None,
                     key_registry=None
                     ) -> dict:
        """
        将多层嵌套字典转换为单层字典，自动处理键名冲突

        参数:
            nested_dict: 要扁平化的嵌套字典
            parent_key: 父级键前缀(递归使用)
            key_separator: 键名连接符
            value_separator: 值连接符
            result: 结果字典(递归使用)
            key_registry: 键名注册表(递归使用)

        返回:
            扁平化后的单层字典
        """
        if result is None:
            result = {}
        if key_registry is None:
            key_registry = {}

        for key, value in nested_dict.items():
            # 生成新键名
            new_key = f"{parent_key}{key_separator}{key}" if parent_key else key

            if isinstance(value, dict):
                # 递归处理子字典
                self.flatten_dict(value, new_key, key_separator, value_separator, result, key_registry)
            else:
                # 处理键名冲突
                final_key = new_key
                if new_key in key_registry:
                    # 更新计数并生成唯一键名
                    key_registry[new_key] += 1
                    final_key = f"{new_key}{key_separator}{key_registry[new_key]}"
                else:
                    # 首次出现的键名，注册为0
                    key_registry[new_key] = 0

                # 添加键值对
                if isinstance(value, list):
                    result[final_key] = value_separator.join(value)
                else:
                    result[final_key] = value

        return result

    def save_to_csv(self, data, file_name, date=None, index=False, **kwargs):
        """
        使用 Pandas 将字典列表保存为 CSV 文件

        参数:
            data: list of dict, 要保存的数据（每个字典代表一行）
            filename: str, 目标 CSV 文件名
            index: bool, 是否包含行索引（默认为 False）
            **kwargs: 其他 pandas.DataFrame.to_csv() 支持的参数
                - sep: 分隔符（默认为逗号）
                - encoding: 文件编码（默认为 'utf-8'）
                - header: 是否包含列名（默认为 True）
                - 其他参数如 na_rep, float_format 等

        示例:
            data = [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}]
            save_dicts_to_csv(data, 'output.csv', sep='|', encoding='gbk')
        """
        # 确定日期目录,如果没有传入参数date，则尝试获取子类初始化的date
        target_date = date or self.date
        if not target_date:
            raise ValueError("Date must be provided or set in instance")

        # 构建完整文件路径
        save_dir = os.path.join(self.folder, target_date)
        save_path = os.path.join(save_dir, file_name)
        # 将字典列表转换为 DataFrame
        df = pd.DataFrame(data)

        # 保存到 CSV 文件
        df.to_csv(save_path, index=index, encoding='utf-8-sig', **kwargs)
