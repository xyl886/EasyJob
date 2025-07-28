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
import random
import sys
import time
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import ContextDecorator
from functools import wraps
from typing import Union, Tuple, Callable, Optional, Dict, List

import requests
import tls_client
from DrissionPage import ChromiumPage
from loguru import logger
from pandas import DataFrame
from requests import RequestException, ReadTimeout, ConnectTimeout
from requests.models import HTTPError

from Core.Config import content_type_ext, DEBUG
from Core.EntityBase import EntityBase
from Core.MongoDB import MongoDB


# 自定义exception
class JobException(Exception):
    pass


capture_exceptions = (RequestException, ReadTimeout, HTTPError, ConnectTimeout, JobException)


def retry(
        default_count: int = 3,  # 重试次数
        delay: Union[int, float] = 1,  # 延迟时间
        max_delay: Union[int, float] = 8,  # 最大延迟时间
        backoff: Union[int, float] = 2,  # 延迟倍数
        exceptions: Tuple[Exception] = capture_exceptions,  # 捕获的异常类型
        log_args: bool = True  # 是否记录参数
):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = kwargs.pop('retry_count', default_count)
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
                        kwargs_copy = kwargs.copy()
                        kwargs_copy.pop('headers', None)
                        error_log = (
                            f"[FINAL FAILURE] {func_name} after {retries} retries\n"
                            f"Params: args={args}, kwargs={kwargs_copy}\n"
                            f"Error: {str(final_error)}"
                        )
                        logger.error(error_log)
                        raise final_error
                except Exception as unexpected_error:
                    # 捕获未预期的异常，立即终止并记录
                    kwargs_copy = kwargs.copy()
                    kwargs_copy.pop('headers', None)
                    logger.critical(
                        f"[UNEXPECTED ERROR] Attempt {attempt} failed:\n"
                        f"Params: args={args}, kwargs={kwargs_copy}\n"
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
        self.InsertUpdateTime = str(datetime.datetime.now())
        self.job_name = self.__class__.__name__
        self.default_log_level_no = logging.INFO
        self.db = MongoDB(db_name=self.job_name, log_enabled=kwargs.get('log_enabled', False))
        self.log_handler = MongoDBHandler(db=self.db, db_name=self.job_name, job_id=self.job_id, run_id=self.run_id)
        self.logger = self.log_handler.logger
        self.log = self.log_handler.logger
        # if not DEBUG:
        #     self.log_handler = MongoDBHandler(db=self.db, db_name=self.job_name, job_id=self.job_id, run_id=self.run_id)
        #     self.logger = self.log_handler.logger
        #     self.log = self.log_handler.logger
        # else:
        #     from loguru import logger
        #     self.logger = logger
        #     self.log = logger
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

    def _read_dump(self, dump_file_name: Optional[str] = None, read_dump: bool = True):
        # 尝试读取缓存文件（当不强制刷新时）
        res = None
        if read_dump and dump_file_name is not None:
            res = self.get_dump(file_name=dump_file_name)
        return res

    def _handle_response(self,
                         url,
                         response,
                         dump_file_name,
                         res_type,
                         validate_str_list,
                         ):
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
        if validate_str_list is not None:
            if not any(validate_str in res for validate_str in validate_str_list):
                # 如果都不存在，抛出异常并列出所有缺失的字符串
                missing_strs = [validate_str for validate_str in validate_str_list if validate_str not in res]
                error_msg = f"请求失败, url: {url} , missing_strs: {missing_strs} "
                self.log.error(error_msg)
                raise JobException(error_msg)
        if dump_file_name is not None and res is not None:
            try:
                self.dump(res, file_name=dump_file_name, res_type=res_type)  # 假设 dump 方法能处理不同类型数据
            except Exception as e:
                error_msg = f"failed to save the cache file: {e}"
                self.logger.error(error_msg)
                raise JobException(f"failed to save the cache file: {e}")
        return res

    def _requests(self,
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
                  raise_for_status: bool = True,
                  proxies: Optional[Dict[str, str]] = None,
                  ):
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
        return response

    def _tls_client(self,
                    url: str,
                    method: str = 'GET',
                    params: Optional[Dict] = None,
                    data: Optional[Dict] = None,
                    json_data: Optional[Dict] = None,
                    headers: Optional[Dict[str, str]] = None,
                    cookies: Optional[Dict[str, str]] = None,
                    allow_redirects: bool = True,
                    proxies: Optional[Dict[str, str]] = None,
                    ):
        try:
            ja3_string = "771,4865-4866-4867-49195-XXXXX-49196-49200-YYYYY-52392-49171-49172-156-157-47-53,0-23-ZZZZZ-10-11-35-16-5-13-18-51-45-43-27-17513,29-23-24,0"
            ja3_string = ja3_string.replace('XXXXX', str(random.randint(49234, 65231))).replace('YYYYY', str(
                random.randint(49234, 65231))).replace('ZZZZZ', str(random.randint(49234, 65231)))
            tsess = tls_client.Session(ja3_string=ja3_string, random_tls_extension_order=True)
            response = tsess.execute_request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                cookies=cookies,
                headers=headers,
                proxy=proxies,
                allow_redirects=allow_redirects
            )
        except RequestException as e:
            self.logger.error(f"request failed: {e}")  # 可选日志记录
            raise JobException(e)  # 触发 retry 装饰器重试
        return response

    def _update_cookies_from_response(self, response):
        """
        从响应中提取 cookies 并更新到 headers 中

        参数:
            response: requests 响应对象
        """
        cookie_str = '; '.join([f"{c.name}={c.value}" for c in response.cookies])
        self.headers['Cookie'] = cookie_str

    @retry(3)
    def download_page_tls_client(self,
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
                                 validate_str_list: Optional[List[str]] = None,  # 验证字符串
                                 retry_count=3,
                                 ) -> Union[str, dict, bytes]:
        res = self._read_dump(dump_file_name=dump_file_name, read_dump=read_dump)
        # 若缓存不存在或强制刷新，则发起请求
        if res is None or not read_dump:
            response = self._tls_client(url=url,
                                        method=method,
                                        params=params,
                                        data=data,
                                        json_data=json_data,
                                        cookies=cookies,
                                        headers=headers,
                                        allow_redirects=allow_redirects,
                                        proxies=proxies
                                        )
            res = self._handle_response(url=url, response=response, res_type=res_type,
                                        validate_str_list=validate_str_list, dump_file_name=dump_file_name)
        return res

    @retry(1)
    def download_page(
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
            validate_str_list(str,optional): 根据传入的str，对响应进行校验，决定是否重试, 任一str符合即可
        Returns:
            str/dict/bytes: 根据 res_type 返回响应内容。

        Raises:
            ValueError: 参数错误或不受支持的 res_type。
            requests.exceptions.RequestException: 网络请求异常。
            requests.exceptions.HTTPError: 当 raise_for_status=True 时，HTTP 状态码非 2xx 抛出。
        """
        # 尝试读取缓存文件（当不强制刷新时）
        res = self._read_dump(dump_file_name=dump_file_name, read_dump=read_dump)
        # 若缓存不存在或强制刷新，则发起请求
        if res is None or not read_dump:
            response = self._requests(url=url,
                                      method=method,
                                      params=params,
                                      data=data,
                                      json_data=json_data,
                                      cookies=cookies,
                                      headers=headers,
                                      timeout=timeout,
                                      encoding=encoding,
                                      allow_redirects=allow_redirects,
                                      raise_for_status=raise_for_status,
                                      proxies=proxies)
            res = self._handle_response(url=url, response=response, res_type=res_type,
                                        validate_str_list=validate_str_list, dump_file_name=dump_file_name)
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
        if res_type == "text":
            with open(file_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(str(res_text))
        elif res_type == "json":
            import json
            with open(file_path, "w", encoding="utf-8", errors="replace") as f:
                json.dump(res_text, f, ensure_ascii=False, indent=2)
        elif res_type == "content":
            with open(file_path, "wb", errors="replace") as f:
                f.write(res_text)
        else:
            raise ValueError(f"Invalid res_type: {res_type}. Must be one of 'text', 'json', or 'content'")
        self.logger.success(f'Saved file {file_name} to {save_folder}')

    def get_dump(self, file_name: str, date=None, check_exists: bool = False):
        """
        从指定路径读取已保存的内容，根据文件扩展名自动推断内容类型

        Args:
            file_name: 文件名称
            date: 可指定dump日期 %Y-%m-%d
            check_exists: 仅检查文件是否存在，不读取
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
            raise ValueError("Args date must be provided or set in instance")

        # 构建完整文件路径
        save_dir = os.path.join(self.folder, target_date)
        save_path = os.path.join(save_dir, file_name)
        # 检查文件是否存在
        if not os.path.exists(save_path):
            self.logger.warning(f"File not found: {save_path}")
            return None
        if check_exists and os.path.exists(save_path):
            return True
        try:
            # 获取文件扩展名
            _, ext = os.path.splitext(file_name)
            ext = ext.lower()  # 统一小写处理
            content = None
            if ext == '.json':
                import json
                with open(save_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
            elif ext in [v.lower() for v in content_type_ext.values()]:
                with open(save_path, "rb") as f:
                    content = f.read()
            else:  # 默认按文本处理
                with open(save_path, "r", encoding="utf-8") as f:
                    content = f.read()
            self.logger.success(f'Success read cache {file_name} form {save_dir}')
            return content
        except Exception as e:
            self.logger.error(f"Error reading file {save_path}: {str(e)}")
            raise  # 重新抛出异常

    def sanitize_filename(self, filename, replacement_text="_", max_length=255, platform_aware=True):
        """
        确保文件名合理化，处理非法字符、保留名称和长度限制

        参数:
            filename (str): 原始文件名（可以包含扩展名）
            replacement_text (str): 替换非法字符的字符（默认为"_"）
            max_length (int): 文件名最大长度（默认为255）
            platform_aware (bool): 是否根据当前操作系统处理保留名称（默认为True）

        返回:
            str: 合理化后的安全文件名
        """
        from pathvalidate import sanitize_filename

        return sanitize_filename(
            filename,
            replacement_text=replacement_text,
            max_len=max_length,
            platform="auto",  # 自动检测操作系统
        )

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

    def save_to_csv(self, data_list: List[dict], file_name: str, date=None):
        """
        使用 Pandas 将字典列表保存为 CSV 文件

        参数:
            data_list: list of dict, 要保存的数据（每个字典代表一行）
            filename: str, 目标 CSV 文件名
            date: 日期文件夹(不指定则从实际job类获取)
            **kwargs: 其他 pandas.DataFrame.to_csv() 支持的参数
                - sep: 分隔符（默认为逗号）
                - encoding: 文件编码（默认为 'utf-8'）
                - header: 是否包含列名（默认为 True）
                - 其他参数如 na_rep, float_format 等

        示例:
            data = [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'age': 25}]
            save_to_csv(data, 'output.csv', sep='|', encoding='gbk')
        """
        # 确定日期目录,如果没有传入参数date，则尝试获取子类初始化的date
        target_date = date or self.date
        if not target_date:
            raise ValueError("Date must be provided or set in instance")
        # 构建完整文件路径
        save_dir = os.path.join(self.folder, target_date)
        save_path = os.path.join(save_dir, file_name)
        DataFrame(data_list).to_csv(save_path, index=False, encoding='utf-8')

    def ThreadRun(self, _fun, run_list, chunk_size=16, *args, **kwargs):
        """
         使用线程池并发执行任务
         该函数创建一个线程池，将任务列表中的每个元素分配给不同的线程执行。
         支持传递自定义参数给任务函数，并自动管理线程池的生命周期。
         :param _fun: 要执行的任务函数，第一个参数必须接收run_list中的元素
         :param run_list: 任务数据列表，每个元素将作为参数传递给任务函数，必须接受 run_info
         :param chunk_size: 线程池最大工作线程数，默认16
         """
        run_list = list(run_list)
        with ThreadPoolExecutor(max_workers=chunk_size) as executor:
            for run_info in run_list:
                executor.submit(_fun, run_info, *args, **kwargs)

    def MultiTabs(self, _fun, tab_list, chunk_size=10, *args, **kwargs):
        '''
        通用的多标签页并发处理函数
        :param _fun: 处理单个任务的函数，必须接受两个参数：tab(ChromiumTab) 和 tab_info
        :param tab_list: 待处理的任务列表（每个元素会传递给_fun）
        :param chunk_size: 每组并发任务数（默认10）
        '''
        tab_list = list(tab_list)
        grouped = [
            tab_list[i:i + chunk_size]
            for i in range(0, len(tab_list), chunk_size)
        ]
        for group in grouped:
            # 提交当前组的所有任务
            self.page = ChromiumPage()
            tabs = []
            futures = []
            for index, detail in enumerate(group):
                tab = self.page.new_tab() if index > 0 else self.page.get_tab(0)
                tabs.append(tab)
            with ThreadPoolExecutor(max_workers=chunk_size) as executor:
                for tab, tab_info in zip(tabs, group):
                    future = executor.submit(_fun, tab, tab_info, *args, **kwargs)
                    futures.append(future)

                # 等待当前组所有任务完成（带异常捕获）
            for future in as_completed(futures):
                try:
                    future.result()  # 获取结果（会抛出异常）
                except Exception as e:
                    # 实际项目中替换为日志记录
                    print(f"Task failed: {e}")
                    # 可选：根据需求决定是否继续
                    # raise  # 如果需要中断整个流程
            self.page.close_tabs(tabs)
