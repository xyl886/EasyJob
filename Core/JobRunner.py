#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: xyl
@file:  JobRunner.py
@time: 2025/06/16
"""
import threading
import time
from concurrent.futures.thread import ThreadPoolExecutor
from typing import List

from jinja2 import Template
from loguru import logger

from Core.Collection import History, JobStatus
from Core.Config import *
from Core.Email import EmailMessageContent, SMTPConfig, EmailSender
from Core.JobBase import JobBase
from Core.MongoDB import MongoDB


class JobRunner:
    _task_executor = ThreadPoolExecutor(max_workers=10)

    # 类级别的数据库连接
    _db = None
    _Job_c = None
    _History_c = None

    def __init__(self, job_id, run_id):
        self.job_id = job_id
        self.run_id = run_id
        self.job_instance = None
        self._init_job()  # 初始化任务记录

    @classmethod
    def _init_db(cls):
        """初始化共享数据库连接"""
        if cls._db is None:
            try:
                cls._db = MongoDB(uri=MONGO_URI, db_name=DB_NAME)
                cls._Job_c = cls._db['Job']
                cls._History_c = cls._db['History']
            except Exception as e:
                logger.error(f"Failed to connect MongoDB uri={MONGO_URI}, db_name={DB_NAME}, e: {str(e)}")
                raise

    def _init_job(self):
        """初始化任务历史记录"""
        self._init_db()
        try:
            job = self._Job_c.find_documents(query={"JobId": self.job_id}, limit=1).dict(0)
            if not job:
                raise ValueError(f"Job {self.job_id} not found")

            history = History(
                JobId=self.job_id,
                JobName=job.get("JobName"),
                Package=job.get("Package"),
                JobClass=job.get("JobClass"),
                Description=job.get("Description"),
                Status=JobStatus.RUNNING,
                RunId=self.run_id,
                Output='',
                StartTime=str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())),
                EndTime=''
            )
            self._History_c.save_dict_to_collection(history.dict(), 'RunId')
        except Exception as e:
            logger.exception(f"CRITICAL: Job initialization failed - {str(e)}")
            raise

    # ✅ 使用示例
    def send_email(self, title: str, logs: List[dict] = None):
        if logs is None:
            logs = []
        header = sorted({key for log in logs for key in log.keys()})

        # 加载模板
        template_path = get_file_path(__file__, marker="log_template.html")
        with open(template_path, encoding="utf-8") as f:
            template = Template(f.read())

        # 渲染 HTML 内容
        rendered_html = template.render(title=title, logs=logs, header=header)
        email_content = EmailMessageContent(
            to=TO.split(","),
            subject=title,
            body=rendered_html,
            subtype="html"
        )
        smtp_config = SMTPConfig(
            login=SMTP.get('user'),
            password=SMTP.get('password'),
            smtp_server=SMTP.get('host'),
            smtp_port=SMTP.get('port'),
        )
        sender = EmailSender(smtp_config)
        sender.send(email_content)

    def execute(self):
        """执行任务核心逻辑"""
        try:
            if self.job_id not in JobBase._registry:
                raise ValueError(f"Job ID {self.job_id} not registered")

            job_class = JobBase._registry.get(self.job_id)
            self.job_instance = job_class(job_id=self.job_id, run_id=self.run_id)

            self.job_instance.logger.warning(
                "Start Job, JobName:%s JobID:%s RunID:%s StartTime:%s" % (
                    self.job_instance.job_name,
                    self.job_id,
                    self.run_id,
                    str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                ))
            # 提交任务到线程池
            future = self._task_executor.submit(self._execute_core)
            future.add_done_callback(self._task_callback)
            return future  # 返回Future对象

        except Exception as e:
            if self.job_instance:
                self.job_instance.logger.error(f"Job startup failed: {str(e)}", exc_info=True)
            raise

    def _execute_core(self):
        """实际执行任务的方法（线程中运行）"""
        try:
            self.job_instance.on_run()
        except Exception as e:
            logger.exception(f"Job failed: JobId:{self.job_id} RunId:{self.run_id} - {str(e)}")
            raise

    def _task_callback(self, future):
        """任务完成回调处理"""
        error = future.result()
        history_query = {'JobId': self.job_id, 'RunId': self.run_id}

        try:
            history = self._History_c.find_documents(query=history_query)[0]
            if error:
                self.job_instance.logger.error(
                    f"Job failed: JobId:{self.job_id} RunId:{self.run_id} - {str(error)}",
                    exc_info=True
                )
                history['Output'] = f"Job execution failed: {str(error)}"
                history['Status'] = JobStatus.FAILED
            else:
                history['Status'] = JobStatus.COMPLETED
            EndTime = str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            history['EndTime'] = EndTime
            self.job_instance.logger.warning(
                f"Job finished, JobName:{history.get('JobName')} JobId:{self.job_id} RunId:{self.run_id} EndTime:{EndTime}"
            )
            self._History_c.save_dict_to_collection(history, 'RunId')

            # 错误日志邮件通知
            error_query = {'level': {'$gte': 40}, 'job_id': self.job_id, 'run_id': self.run_id}
            if not DEBUG and self.job_instance.db['log'].count(query=error_query) > 0:
                title = f"{self.job_instance.job_name}:{self.job_id}"
                warning_query = {'level': {'$gte': 30}, 'job_id': self.job_id, 'run_id': self.run_id}
                logs = self.job_instance.db['log'].find_documents(query=warning_query).dict()
                threading.Thread(target=self.send_email, args=(title, logs)).start()

        except Exception as e:
            logger.exception(f"CRITICAL: Completion handling failed: {str(e)}")
