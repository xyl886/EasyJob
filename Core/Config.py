#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: Config.py
@time: 2025/05/22
"""
from pathlib import Path


def get_file_path(current_file, marker=""):
    """
    向上递归查找项目根目录（直到找到标记文件，如 .git/pyproject.toml）
    """
    current_path = Path(current_file).resolve().parent
    while current_path != current_path.parent:  # 防止无限循环
        if (current_path / marker).exists():
            return str(current_path) + "\\" + marker
        current_path = current_path.parent
    raise FileNotFoundError(f"Could not find project root with marker: {marker}")


yaml_path = ''
try:
    yaml_path = get_file_path(__file__, marker="config.yaml")
    print(f"[AutoImport] config.yaml found at: {yaml_path}")
except Exception as e:
    print("[AutoImport] Failed to get_file_path config.yaml, e:" + str(e))
try:
    import yaml

    with open(yaml_path, encoding='utf-8') as f:
        config = yaml.safe_load(f)
    BASE_PACKAGE = config.get('jobs').get('base_package', 'Job')
    MODULE_PATTERN = config.get('jobs').get('module_pattern', 'Action.py')
    DEBUG = config.get('jobs').get('debug')
    MONGO_URI = config.get('mongo').get('uri', 'mongodb://localhost:27017')
    DB_NAME = config.get('mongo').get('database', 'EasyJob')
    SMTP = config.get('smtp')
    TO = config.get('smtp').get('to')
    print("[AutoImport] Success loaded config.yaml")
except Exception as e:
    print(f"[AutoImport] Failed to load config.yaml: {e}")
    BASE_PACKAGE = 'Job'
    MODULE_PATTERN = 'Action.py'
    MONGO_URI = 'mongodb://localhost:27017'
    DB_NAME = 'EasyJob'

content_type_ext = {
    # 图片类
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "image/x-icon": ".ico",

    # 文档类
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/plain": ".txt",  # 虽然可用text，但也可用content

    # 压缩包类
    "application/zip": ".zip",
    "application/x-rar-compressed": ".rar",
    "application/x-tar": ".tar",
    "application/gzip": ".gz",
    "application/x-7z-compressed": ".7z",

    # 音视频类
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/x-msvideo": ".avi",
    "video/x-flv": ".flv",
    "video/webm": ".webm",
    "video/ogg": ".ogv",
    "video/3gpp": ".3gp",

    # 二进制流类
    "application/octet-stream": ".bin",  # 通用二进制文件

    # 程序类
    "application/x-executable": ".exe",
    "application/x-shockwave-flash": ".swf",

    # 字体类
    "font/woff": ".woff",
    "font/woff2": ".woff2",

    # 其他
    "application/xml": ".xml"
}
