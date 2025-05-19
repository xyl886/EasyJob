# -*- coding: utf-8 -*-
# Core/JobBase.py
import datetime
import hashlib
import json
import logging
import os
import sys
import time
from functools import wraps
from typing import Union, Tuple, Callable, Optional, Dict, List

import requests
from loguru import logger
from requests import RequestException

from .MongoDB import MongoDB


def retry(
        retries: int = 5,  # 重试次数
        delay: Union[int, float] = 1,  # 延迟时间
        backoff: Union[int, float] = 2,  # 延迟倍数
        exceptions: Tuple[Exception] = (RequestException,),  # 捕获的异常类型
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
                        sleep_time = delay * (backoff ** attempt)
                        logger.warning(
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

                except Exception as unexpected_error:
                    # 捕获未预期的异常，立即终止并记录
                    logger.critical(
                        f"[UNEXPECTED ERROR] {func_name} failed with unhandled exception\n"
                        f"Error: {str(unexpected_error)}"
                    )

        return wrapper

    return decorator


class MongoDBHandler:
    """自定义MongoDB日志处理器（仅记录ERROR及以上级别）"""

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
            'level': record["level"].name,
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


class JobBase:
    """任务基类"""
    _registry = {}

    def __init_subclass__(cls, **kwargs):
        """自动注册子类，支持多个 job_id"""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'job_id'):
            # 将 job_id 转换为可迭代对象（支持列表、元组、集合或单个值）
            job_ids = cls.job_id
            if job_ids is None:
                raise ValueError(f"job_id not found in {cls.__name__}")
            if not isinstance(job_ids, (list, tuple, set)):
                job_ids = [job_ids]
            # 遍历所有 job_id 并注册
            for job_id in job_ids:
                if job_id in JobBase._registry:
                    print(f"Job {job_id} {cls.__name__} already registered, skipping...")
                    pass
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
        self.db_name = self.__class__.__name__
        self.default_log_level_no = logging.INFO
        self.db = MongoDB(db_name=self.db_name, log_enabled=kwargs.get('log_enabled', False))
        self.log_handler = MongoDBHandler(db=self.db, db_name=self.db_name, job_id=self.job_id, run_id=self.run_id)
        self.logger = self.log_handler.logger
        if not hasattr(self, 'folder'):
            raise ValueError(f"Folder not found in {self.__class__.__name__} job_id:{self.job_id}")

    def on_run(self):
        """任务执行入口，需要子类实现"""
        raise NotImplementedError("Subclasses must implement this method")

    def md5_encrypt(self, text):
        text = str(text)
        md5 = hashlib.md5()
        md5.update(text.encode('utf-8'))
        return md5.hexdigest()

    @retry(30)
    def send_request(
            self,
            url: str,
            method: str = 'GET',
            params: Optional[Dict] = None,
            json_data: Optional[Dict] = None,
            headers: Optional[Dict[str, str]] = None,
            cookies: Optional[Dict[str, str]] = None,
            timeout: Union[int, float] = 10,
            encoding: Optional[str] = None,
            allow_redirects: bool = True,
            proxies: Optional[Dict[str, str]] = None,
            dump_file_name: Optional[str] = None,
            res_type: str = 'text',
            force_refresh: bool = False,
            raise_for_status: bool = False,
            validate_str_list: Optional[List[str]] = None
    ) -> Union[str, dict, bytes]:
        """
        发送 GET 请求获取网页内容，支持缓存、自动重试和多种返回格式。

        Args:
            url (str): 目标 URL 地址。
            method(str): get, post
            params(dict): dict
            json_data(dict): json
            headers (dict, optional): 自定义请求头，默认为 None。
            cookies (dict, optional): 自定义 Cookies，默认为 None。
            timeout (int/float, optional): 请求超时时间（秒），默认为 10。
            encoding (str, optional): 手动指定响应编码（如 'utf-8'、'gbk'），默认自动检测。
            allow_redirects (bool, optional): 是否允许重定向，默认为 True。
            proxies (dict, optional): 代理配置（如 {'http': 'http://10.10.1.10:3128'}）。
            dump_file_name (str, optional): 缓存文件名，若存在则优先读取缓存。
            res_type (str, optional): 返回类型，可选 'text'（文本）、'json'（字典）、'content'（二进制），默认为 'text'。
            force_refresh (bool, optional): 强制跳过dump重新请求，默认为 False。
            raise_for_status (bool, optional): 是否在 HTTP 错误码时抛出异常，默认为 False。
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
        if not force_refresh and dump_file_name is not None:
            res = self.get_dump(file_name=dump_file_name)
            if res_type == 'json' and res is not None:
                res = json.loads(res)
        # 若缓存不存在或强制刷新，则发起请求
        if res is None or force_refresh:
            try:
                response = requests.request(
                    method,
                    url,
                    params=params,
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
            except requests.exceptions.RequestException as e:
                self.logger.error(f"request failed: {e}")  # 可选日志记录
                raise  # 触发 retry 装饰器重试
            if res_type == 'text':
                res = response.text
                dump_data = res
            elif res_type == 'json':
                res = response.json()
                dump_data = json.dumps(res, ensure_ascii=False)
            elif res_type == 'content':
                res = response.content
                dump_data = res
            else:
                raise ValueError(f"not supported res_type: {res_type}，可选 'text', 'json', 'content'")
            if dump_file_name is not None:
                try:
                    self.dump(dump_data, file_name=dump_file_name)  # 假设 dump 方法能处理不同类型数据
                except Exception as e:
                    self.logger.error(f"failed to save the cache file: {e}")
        # 通过 validate_str_list对响应校验，决定是否重试
        for each_validate_str in validate_str_list:
            if each_validate_str not in str(res):
                self.logger.info(f"url: {url} str: {each_validate_str} request failed，on retry...{res}")
                raise requests.exceptions.RequestException("请求失败")
        return res

    def dump(self, res_text, file_name: str):
        """
        将文本内容保存到指定路径

        Args:
            res_text: 要保存的文本内容
            file_name: 完整的文件保存路径（如 `data/dump_2023.txt`）
        """
        if file_name is None:
            raise ValueError("file_name cannot be None")
        if res_text is None:
            raise ValueError("res_text cannot be None")
        # 自动创建父目录（如果不存在）
        save_folder = self.folder + '\\' + self.date
        os.makedirs(save_folder, exist_ok=True)
        # 写入内容（默认覆盖已有文件）
        with open(save_folder + '\\' + file_name, "w", encoding="utf-8") as f:
            f.write(str(res_text))
        self.logger.info(f'{file_name} saved_to {save_folder}')

    def get_dump(self, file_name: str, date=None):
        """
        从指定路径读取已保存的文本内容

        Args:
            date: 可指定dump日期 %Y-%m-%d
            file_name: 文件名称

        Returns:
            读取到的文本内容（字符串）

        Raises:
            FileNotFoundError: 文件不存在时抛出异常
        """
        if file_name is None:
            return None
        try:
            if date:
                save_path = self.folder + '/' + date + '/' + file_name
            else:
                save_path = self.folder + '/' + self.date + '/' + file_name
            with open(save_path, "r", encoding="utf-8") as f:
                f_read = f.read()
        except FileNotFoundError:
            self.logger.info(f"File {file_name} not found")
            return None
        self.logger.info(f'{file_name} has been read from {save_path}')
        return f_read
