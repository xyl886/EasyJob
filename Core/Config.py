#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: Config.py
@time: 2025/05/22
"""
content_type_ext = {
    # 图片类
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",

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

    # 音视频类
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",

    # 二进制流类
    "application/octet-stream": ".bin",  # 通用二进制文件

    # 程序类
    "application/x-executable": ".exe",
    "application/x-shockwave-flash": ".swf",

    # 字体类
    "font/woff": ".woff",
    "font/woff2": ".woff2",

    # 其他
    "application/json": ".json",  # 虽然常用json()解析，但也可用content
    "application/xml": ".xml"
}
