#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: Email.py
@time: 2025/05/22
"""
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Set
from typing import List, Union, Optional, Dict

from jinja2 import Template
from loguru import logger


class EmailValidator:
    """邮箱格式校验器"""

    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

    @staticmethod
    def is_valid(email: str) -> bool:
        return bool(EmailValidator.EMAIL_REGEX.match(email))


class SMTPConfig:
    """SMTP服务器配置"""

    DEFAULT_SMTP_SERVER = "smtp.qq.com"
    DEFAULT_SMTP_PORT = 587

    def __init__(self, login: str, password: str, **kwargs: Any) -> None:
        """
        SMTP服务器配置

        :param login: 发件人邮箱地址
        :param password: 邮箱密码
        :param smtp_server: SMTP服务器地址，默认为 "smtp.qq.com"
        :param smtp_port: SMTP服务器端口，默认为 587
        """
        if not EmailValidator.is_valid(login):
            raise ValueError(f"无效的发件人邮箱地址：{login}")
        if not password:
            raise ValueError("邮箱密码不能为空")

        self.login = login
        self.password = password
        self.server = kwargs.get("smtp_server", self.DEFAULT_SMTP_SERVER)

        try:
            self.port = int(kwargs.get("smtp_port", self.DEFAULT_SMTP_PORT))
        except (TypeError, ValueError):
            raise ValueError("SMTP端口必须为整数类型")

        if self.port <= 0:
            raise ValueError("SMTP端口必须为正整数")


class EmailMessageContent:
    """邮件内容定义（支持模板，多人收件）"""

    VALID_SUBTYPES: Set[str] = {"plain", "html", "xml", "richtext", "json"}

    def __init__(
            self,
            to: Union[str, List[str]],
            subject: str = "",
            body: Optional[str] = "",
            subtype: str = "plain",
            cc: Optional[Union[str, List[str]]] = None,
            bcc: Optional[Union[str, List[str]]] = None,
            template: Optional[str] = None,
            template_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        邮件内容定义（支持模板，多人收件）

        :param to: 主送人邮箱地址，可以一个字符串或字符串列表
        :param subject: 邮件主题
        :param body: 邮件正文内容，如果使用模板则可为空
        :param subtype: 邮件内容类型，支持 plain、html、json 等
        :param cc: 抄送人邮箱地址，可以是字符串或字符串列表
        :param bcc: 密送人邮箱地址，可以是字符串或字符串列表
        :param template: 可选的 Jinja2 模板字符串，优先级高于 body
        :param template_data: 模板渲染所需数据字典
        """
        self.to = self._normalize_emails(to)
        self.cc = self._normalize_emails(cc)
        self.bcc = self._normalize_emails(bcc)
        self.subject = subject
        self.subtype = subtype

        if subtype not in self.VALID_SUBTYPES:
            raise ValueError(f"无效的内容类型：{subtype}，允许类型有：{self.VALID_SUBTYPES}")

        if template:
            self.body = Template(template).render(template_data or {})
        else:
            self.body = body or ""

    @staticmethod
    def _normalize_emails(emails: Union[str, List[str], None]) -> List[str]:
        if not emails:
            return []
        if isinstance(emails, str):
            emails = [email.strip() for email in emails.split(",")]
        return [e for e in emails if EmailValidator.is_valid(e)]


class EmailSender(object):
    """邮件发送器，支持多收件人、抄送、密送"""

    def __init__(self, config: SMTPConfig) -> None:
        self.config = config

    def send(self, content: EmailMessageContent) -> None:
        msg = MIMEMultipart()
        msg["From"] = self.config.login
        msg["To"] = ", ".join(content.to)
        if content.cc:
            msg["Cc"] = ", ".join(content.cc)
        msg["Subject"] = content.subject
        msg.attach(MIMEText(content.body, _subtype=content.subtype))
        all_recipients = content.to + content.cc + content.bcc

        try:
            with smtplib.SMTP(self.config.server, self.config.port) as smtp:
                smtp.starttls()
                smtp.login(self.config.login, self.config.password)
                smtp.sendmail(self.config.login, all_recipients, msg.as_string())
            logger.info(f"✅ 邮件已成功发送至 {all_recipients}")
        except smtplib.SMTPAuthenticationError as e:
            logger.error("❌ SMTP认证失败，请检查用户名和密码" + str(e))
            raise
        except smtplib.SMTPConnectError as e:
            logger.error("❌ 无法连接SMTP服务器" + str(e))
            raise
        except smtplib.SMTPResponseException as e:
            logger.error("❌ 无法连接到SMTP服务器" + str(e))
            raise
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP协议错误：{e}")
            raise
        except Exception as e:
            logger.critical(f"❌ 发送邮件时发生未知错误：{e}")
            raise


# def send_email(title, logs: List[dict] = None):
#     if logs is None:
#         logs = []
#     header = sorted({key for log in logs for key in log.keys()})
#
#     # 加载模板
#     template_path = r'D:\soft\pythonProject\xyl886\EasyJob\log_template.html'
#     with open(template_path, encoding="utf-8") as f:
#         template = Template(f.read())
#
#     # 渲染 HTML 内容
#     rendered_html = template.render(title=title, logs=logs, header=header)
#     email_content = EmailMessageContent(
#         to=['1803466516@qq.com'],
#         subject=title,
#         body=rendered_html,
#         subtype="html"
#     )
#     smtp_config = SMTPConfig(
#         login='1803466516@qq.com',
#         password='favqogvppmfjbgcj'
#     )
#     sender = EmailSender(smtp_config)
#     sender.send(email_content)
#
#
# if __name__ == '__main__':
#     level_ = 30
#     job_id = 100015
#     run_id = 579453
#     clazz = 'BabylistAction'
#     query = {
#         'level': {'$gte': level_},  # 大于30
#         'job_id': job_id,
#         'run_id': run_id
#     }
#     db = MongoClient(f"mongodb://localhost:27017")
#     logs = db[clazz]['log'].find(query)
#     title = f"{clazz}:{job_id}"
#     send_email(title, logs=[doc for doc in logs])
