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

from Core.MongoDB import MongoDB
from Core.Config import *
from Core.Collection import History, JobStatus
from Core.Email import *
from Core.JobBase import JobBase

_task_executor = ThreadPoolExecutor(max_workers=10)


class JobRunner:
    def __init__(self, job_id, run_id):
        self.job_id = job_id
        self.run_id = run_id
        self.job_instance = None
        self._init_job()  # 初始化任务记录

    def _init_job(self):
        """初始化任务历史记录"""
        try:
            self.db = MongoDB(uri=MONGO_URI, db_name=DB_NAME)
            self.Job_c = self.db['Job']
            self.History_c = self.db['History']
        except Exception as e:
            print(f"Failed to connect MongoDB uri={MONGO_URI}, db_name={DB_NAME}, e: {str(e)}")
        try:
            job = self.Job_c.find_documents(query={"JobId": self.job_id}, limit=1).dict(0)
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
            self.History_c.save_dict_to_collection(history.dict(), 'RunId')
        except Exception as e:
            print(f"CRITICAL: Job initialization failed - {str(e)}")
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
                "Start Job, JobName: %s   JobID: %s   RunID: %s   StartTime: %s" % (
                    self.job_instance.job_name,
                    self.job_id,
                    self.run_id,
                    str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
                ))
            # 提交任务到线程池
            future = _task_executor.submit(self._execute_core)
            future.add_done_callback(self._handle_completion)

        except Exception as e:
            if self.job_instance:
                self.job_instance.logger.error(f"Job startup failed: {str(e)}", exc_info=True)
            raise

    def _execute_core(self):
        """实际执行任务的方法（线程中运行）"""
        try:
            self.job_instance.on_run()
            return None
        except Exception as e:
            return e

    def _handle_completion(self, future):
        """任务完成回调处理"""
        error = future.result()
        history_query = {'JobId': self.job_id, 'RunId': self.run_id}

        try:
            history = self.History_c.find_documents(query=history_query)[0]
            if error:
                self.job_instance.logger.error(
                    f"Job failed: {self.job_id}/{self.run_id} - {str(error)}",
                    exc_info=True
                )
                history['Output'] = f"Job execution failed: {str(error)}"
                history['Status'] = JobStatus.FAILED
            else:
                self.job_instance.logger.warning(
                    f"Job finished, JobId: {self.job_id} RunId: {self.run_id}"
                )
                history['Status'] = JobStatus.COMPLETED

            history['EndTime'] = str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
            self.History_c.save_dict_to_collection(history, 'RunId')

            # 错误日志邮件通知
            if not DEBUG:
                error_query = {'level': {'$gte': 40}, 'job_id': self.job_id, 'run_id': self.run_id}
                if self.job_instance.db['log'].count(query=error_query) > 0:
                    title = f"{self.job_instance.job_name}:{self.job_id}"
                    warning_query = {'level': {'$gte': 30}, 'job_id': self.job_id, 'run_id': self.run_id}
                    logs = self.job_instance.db['log'].find_documents(query=warning_query).dict()
                    threading.Thread(target=send_email, args=(title, logs)).start()

        except Exception as e:
            print(f"CRITICAL: Completion handling failed: {str(e)}")
