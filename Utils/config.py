#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: config.py
@time: 2025/05/20
"""

from Core.MongoDB import MongoDB

try:
    import yaml

    with open('config.yaml') as f:
        config = yaml.safe_load(f)
    MONGO_URI = config.get('mongo').get('uri', 'mongodb://localhost:27017')
    DB_NAME = config.get('mongo').get('database', 'EasyJob')
except Exception as e:
    print(f"[AutoImport] Failed to load config.yaml: {e}")
    MONGO_URI = 'mongodb://localhost:27017'
    DB_NAME = 'EasyJob'

db = MongoDB(uri=MONGO_URI, db_name=DB_NAME)
Job_c = db['Job']
History_c = db['History']
