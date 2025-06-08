# -*- coding: utf-8 -*-
import hashlib
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List

import pymongo.errors
from loguru import logger
from pymongo import MongoClient


class DocumentList:
    def __init__(self, documents: List[dict]):
        """
        初始化 DocumentList 对象
        :param documents: 集合中的文档列表
        """
        # 确保 documents 是列表类型
        if not isinstance(documents, list):
            raise TypeError("documents 必须是列表类型")
        self.documents = documents if documents else []

    def _convert_id_to_str(self):
        """
        内部方法：将所有文档的 _id 字段转换为字符串，方便序列化
        """
        for doc in self.documents:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])

    def __iter__(self):
        return iter(self.documents)

    def __len__(self):
        return len(self.documents)

    def count(self):
        """
        计算查询结果的数量
        """
        return len(self.documents)

    def dict(self, index: int = None) -> List[dict] | dict:
        """
        将 object_id 转换为str,此方法是为了方便后续序列化不出错
        :param index: 如果提供索引，返回对应索引位置的文档dict
        """
        if not self.documents:
            return []
        self._convert_id_to_str()
        if index is not None:
            # 增加索引范围检查，避免 IndexError
            if not isinstance(index, int) or index < 0 or index >= len(self.documents):
                raise IndexError(f"请检查index: {index}")
            return self.documents[index]
        return self.documents


class CollectionWrapper:
    def __init__(self, db_name: str, collection, log_enabled=True):
        """
        初始化 CollectionWrapper 对象
        :param db_name: str 数据库名称
        :param collection: 集合对象
        """
        self.db_name = db_name
        self.collection_name = collection.name
        self.collection = collection
        self.rlock = threading.RLock()  # 为每个集合添加锁
        self.log_enabled = log_enabled  # 添加日志开关

    def __getitem__(self, key):
        """
        获取集合中的某个属性
        :param key: str 集合名称
        :return: 属性值
        """
        return getattr(self.collection, key)

    def index_information(self, index_name=None):
        if index_name:
            return self.collection.index_information(index_name)
        else:
            return self.collection.index_information()

    def create_index(self, index, unique=True):
        """
        创建索引
        """
        self.collection.create_index(index, unique=unique)

    def aggregate(self, pipeline):
        """
        聚合查询
        :param pipeline: a list of aggregation pipeline stages

        """
        return DocumentList(list(self.collection.aggregate(pipeline)))

    # def count(self):
    #     return int(self.collection.estimated_document_count())

    def count(self, query: dict = None) -> int:
        """
        根据给定的查询条件（query）从指定集合中统计文档数量。

        参数:
            query (dict): 查询条件，使用 MongoDB 查询语法。默认为空查询。

        返回:
            int: 匹配查询条件的文档数量。
        """
        if query is None:
            query = {}
        return int(self.collection.count_documents(query))

    @staticmethod
    def remove_duplicates(dict_list, distinct_key):
        """
        参数:
            dict_list (list[dict]): 包含字典的列表。
            distinct_key(str,optional): 根据某个key的value进行去重
        返回:
            list[dict]: 去重后的字典列表。
        """
        seen_ids = set()
        unique_list = []

        for item in dict_list:
            id = item.get(distinct_key)
            if id not in seen_ids:
                seen_ids.add(id)
                unique_list.append(item)

        return unique_list

    @logger.catch
    def find_documents(self,
                       query: dict = None,
                       projection: dict = None,
                       limit: int = 0,
                       skip: int = 0,
                       distinct_key: str = None,
                       sort: list = None) -> DocumentList | None:
        """
        根据给定的查询条件（query）从指定集合中查找文档。

        参数:
            query (dict): 查询条件，使用 MongoDB 查询语法。
            projection (dict, optional): 返回字段投影，仅返回指定的字段。默认返回所有字段。
            limit (int, optional): 返回结果的最大数量，默认返回所有匹配的文档。
            skip (int, optional): 跳过指定数量的文档，用于分页。
            distinct_key(str,optional): 根据某个key的value进行去重
            sort    : 排序
        返回:
            - list[dict]: 匹配查询条件的文档列表（字典形式）。
            - dict: 如果`explain=True`，返回查询计划。
        """

        start_time = time.perf_counter()
        try:
            if distinct_key is not None:
                with self.rlock:
                    self.collection.create_index(distinct_key)
                    distinct_values = self.collection.distinct(distinct_key, filter=query)
                    cursor = self.collection.find(query, projection=projection, limit=limit, skip=skip, sort=sort)
                    data = [doc for doc in cursor if doc[distinct_key] in distinct_values]
                    # # 直接使用 distinct 方法
                    # distinct_values = self.collection.distinct(distinct_key, query)
                    # data = [{distinct_key: value} for value in distinct_values]
                    data = self.remove_duplicates(data, distinct_key)
            else:
                with self.rlock:
                    cursor = self.collection.find(query, projection=projection, limit=limit, skip=skip, sort=sort)
                    data = [doc for doc in cursor]
            cursor.batch_size = 10000  # 或根据实际情况调整 batch_size
            if self.log_enabled:
                logger.info(f"{self.db_name}:{self.collection_name} 查询到 {len(data)} 条数据, "
                            f"耗时: {time.perf_counter() - start_time:.6f} 秒")
            return DocumentList(data)
        except pymongo.errors.ConnectionFailure as e:
            logger.error(f"连接数据库失败: {e}")
        except pymongo.errors.ExecutionTimeout as e:
            logger.error(f"查询超时: {e.details['errmsg']}")
        except pymongo.errors.OperationFailure as e:
            logger.error(f"查询数据失败: {e.details['errmsg']}")
        except pymongo.errors.PyMongoError as e:
            logger.error(f"Database query failed: {str(e)}")
        except Exception as e:
            logger.error(f"查询数据时发生未知错误: {e}")

    @logger.catch
    def batch_find_documents(self, query=None, projection: dict = None, batch_size: int = 1000, skip: int = 0):
        """
        分批查询文档，每次查询`batch_size`条数据。

        参数:
            query (dict): 查询条件，使用 MongoDB 查询语法。
            projection (dict, optional): 返回字段投影，仅返回指定的字段。默认返回所有字段。
            batch_size (int, optional): 每批次查询的文档数量。默认为1000。

        返回:
            Generator[List[dict]]: 生成器，逐批返回匹配查询条件的文档列表（字典形式）。
        """

        if query is None:
            query = {}
        while True:
            logger.info(f'开始查询第 {skip} 条到第 {batch_size + skip} 条的数据')
            docs_batch = self.find_documents(query=query, projection=projection, limit=batch_size, skip=skip)
            if not docs_batch:
                break
            yield docs_batch
            skip += batch_size

    @logger.catch
    def stream_find_documents(self, query: dict, projection: dict = None, batch_size: int = 1000, skip: int = 0):
        """
        流式查询文档，逐条返回匹配查询条件的文档。

        参数:
            query (dict): 查询条件，使用 MongoDB 查询语法。
            projection (dict, optional): 返回字段投影，仅返回指定的字段。默认返回所有字段。

        返回:
            Generator[dict]: 生成器，逐条返回匹配查询条件的文档（字典形式）。
        """
        if query is None:
            query = {}
        cursor = self.find_documents(query=query, projection=projection, limit=batch_size, skip=skip)
        cursor.batch_size = 10000  # 或根据实际情况调整 batch_size
        for doc in cursor:
            yield doc

    def export_data_to_excel(self,
                             output_file: str = None,
                             sheet_name: str = None,
                             check_columns: bool = True,
                             query: dict = None,
                             projection: dict = None,
                             limit: int = 0,
                             skip: int = 0,
                             distinct_key: str = None,
                             explain: bool = False
                             ):
        """
        将查询到的数据保存到Excel文件中。(废弃)
        """
        if output_file is None:
            if self.db_name == '':
                logger.error("请选择MongoDB数据库")
                return
            else:
                output_file = self.db_name
        if not output_file.endswith('.xlsx') or not output_file.endswith('.xls'):
            output_file += '.xlsx'
        if sheet_name is None:
            if self.collection_name == '':
                logger.error(f"当前库为{self.db_name} 请选择集合")
                return
            else:
                sheet_name = self.collection_name
        try:
            infos = self.find_documents(query=query,
                                        projection=projection,
                                        limit=limit,
                                        skip=skip,
                                        distinct_key=distinct_key,
                                        explain=explain)
        except Exception as e:
            logger.error(f"查询数据时发生错误: {e}")
            return
        if not infos:
            logger.error("请先执行find_documents方法查询数据")
            return
        # save_dict_list_to_excel(infos,
        #                         output_file=output_file,
        #                         sheet_name=sheet_name,
        #                         check_columns=check_columns)

    @logger.catch
    def update_documents(self, data_dict, query_key: str):
        """
        根据传入的字典的某个key的值进行查询，判断是否已经存在相同记录，
        如果存在则更新记录，保留已有的字段数据，仅更新传入的字段。
        如果不存在则不进行任何操作。

        Args:
            data_dict (dict): 待更新的数据字典。
            query_key (str): 用于查询和判断重复的键名。
        """
        if not isinstance(data_dict, dict):
            raise TypeError("data_dict 必须是一个字典")
        if not query_key:
            raise ValueError("query_key 不能为空")

        collection_info = f"{self.db_name}:{self.collection_name}"
        start_time = time.perf_counter()

        try:
            query_value = data_dict.get(query_key)
            if query_value is None:
                raise ValueError(f"{collection_info} 指定的查询键'{query_key}'在传入的记录数据中不存在或其值为None")

            with self.rlock:
                existing_document = self.collection.find_one({query_key: query_value})

            if existing_document is not None:
                # 合并现有记录和新数据
                update_data = {**existing_document, **data_dict}
                # 去掉 _id 字段以避免 MongoDB 错误
                update_data.pop('_id', None)
                update_filter = {query_key: query_value}
                with self.rlock:
                    result = self.collection.update_one(update_filter, {'$set': update_data})
                operation_result = f"数据成功更新到mongodb {collection_info}, 耗时: {time.perf_counter() - start_time:.6f} 秒"
                logger.info(f"{operation_result}, {update_data}")
                return result.modified_count  # 返回修改的记录数
            else:
                logger.info(f"{collection_info} 没有找到匹配的记录, 不进行更新操作")
                return 0  # 返回0表示没有更新任何记录
        except pymongo.errors.PyMongoError as e:
            logger.error(f"更新数据失败: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"更新数据时发生未知错误: {e}")
            raise

    @logger.catch
    def save_dict_to_collection(self, data_dict: dict, query_key: str = None):
        """
        根据传入的字典的某个key的值进行查询，判断是否已经存在相同记录，
        如果存在则更新，否则插入新记录。

        Args:
            data_dict (dict): 待保存或更新的数据字典。
            query_key (str, optional): 用于查询和判断重复的键名，默认为None。
                                      如果为None，则直接插入新记录，不进行查询和更新操作。
        """
        if not isinstance(data_dict, dict):
            raise TypeError("data_dict 必须是一个字典")
        if query_key is not None and not isinstance(query_key, str):
            raise TypeError("query_key 必须是一个字符串")
        if data_dict == {}:
            logger.warning("传入的data_dict为空字典")
            return
        collection_info = f"{self.db_name}:{self.collection_name}"
        result = None
        _id = 0
        start_time = time.perf_counter()
        try:
            if query_key is None:
                with self.rlock:
                    try:
                        result = self.collection.insert_one(data_dict)
                        operation_result = f"1条数据成功保存到mongodb {collection_info}, 耗时: {time.perf_counter() - start_time:.6f} 秒"
                        _id = result.inserted_id
                    except Exception as e:
                        operation_result = f"1条数据保存到mongodb {collection_info} 失败: {str(e)}, 可能已存在"
                if self.log_enabled:
                    logger.info(f"{operation_result}, {data_dict}")
            elif isinstance(query_key, str) and query_key:
                if query_key != '_id' and data_dict.get('_id'):
                    data_dict.pop('_id')
                query_value = data_dict[query_key]
                if query_value is None:
                    raise ValueError(f"{collection_info} 指定的查询键'{query_key}'在传入的记录数据中不存在")
                with self.rlock:
                    existing_document = self.collection.find_one({query_key: query_value}, projection={'_id': 0})
                if existing_document is not None:
                    # 更新已有记录
                    update_filter = {
                        query_key: query_value,
                    }
                    with self.rlock:
                        result = self.collection.update_one(update_filter, {'$set': data_dict}, upsert=True)
                    _id = result.upserted_id
                    operation_result = f"数据成功更新到mongodb {collection_info}, 耗时: {time.perf_counter() - start_time:.6f} 秒"
                    if self.log_enabled:
                        logger.info(f"{operation_result}, {data_dict}")
                else:
                    # 插入新记录
                    with self.rlock:
                        result = self.collection.insert_one(data_dict)
                    operation_result = f"1条数据成功保存到mongodb {collection_info}, 耗时: {time.perf_counter() - start_time:.6f} 秒"
                    if self.log_enabled:
                        logger.info(f"{operation_result}, {data_dict}")
                    _id = result.inserted_id
            if result:
                return _id
            else:
                logger.error("保存数据失败")
        except Exception as e:
            logger.error(f"保存数据失败: {e}")

    @logger.catch
    def save_dict_list_to_collection(self, dict_list: List[dict], query_key: str = None):
        """
        将字典列表批量保存至 MongoDB。
        """
        if not isinstance(dict_list, list):
            raise TypeError("dict_list 必须是一个列表")
        if len(dict_list) == 0:
            logger.warning("dict_list 为空")
            return []
        start_time = time.perf_counter()
        collection_info = f"{self.db_name}:{self.collection_name}"

        try:
            if query_key is None:
                # 直接批量插入，不进行查询和更新
                with self.rlock:
                    result = self.collection.insert_many(dict_list)  # 批量插入
                if self.log_enabled:
                    logger.info(f"{len(result.inserted_ids)} 条数据成功保存到mongodb {collection_info}, "
                                f"耗时: {time.perf_counter() - start_time:.6f} 秒")
                return result.inserted_ids  # 返回插入的ID列表
            else:
                if not isinstance(query_key, str):
                    raise ValueError("query_key 必须是一个字符串")
                # 根据query_key查询出所有的数据的query_key存入list，
                with self.rlock:
                    if query_key == '_id':
                        existing_query_keys = set(
                            str(doc[query_key]) for doc in self.collection.find({}, {query_key: 1}))
                    else:
                        existing_query_keys = set(
                            doc[query_key] for doc in
                            self.collection.find({query_key: {"$exists": True}}, {query_key: 1}))
                # 分割新数据和已存在数据
                new_data = [data for data in dict_list if data[query_key] not in existing_query_keys]
                update_data = [data for data in dict_list if data[query_key] in existing_query_keys]
                logger.info(
                    f"{collection_info} 查询到 {len(existing_query_keys)} 条记录 新数据: {len(new_data)} 条, 已存在数据: {len(update_data)} 条")
                # 插入新数据
                new_result = []
                if new_data:
                    with self.rlock:
                        new_result = self.collection.insert_many(new_data)
                    if self.log_enabled:
                        logger.info(f"{len(new_result.inserted_ids)} 条新数据成功保存到mongodb {collection_info}, "
                                    f"耗时: {time.perf_counter() - start_time:.6f} 秒")
                # 更新已存在数据
                if update_data:
                    for data in update_data:
                        self.save_dict_to_collection(data, query_key)
                return new_result.inserted_ids if new_data else []  # 返回新数据的插入ID列表
        except pymongo.errors.BulkWriteError as e:
            logger.error(f"Failed to save data: {str(e.details)}")
            raise
        # except Exception as e:
        #     logger.error(f"保存数据失败: {e}")

    def md5_encrypt(self, text):
        text = str(text)
        md5 = hashlib.md5()
        md5.update(text.encode('utf-8'))
        return md5.hexdigest()

    def delete_documents(self, query: dict = None, skip: int = None, limit: int = None, recyclable: bool = False,
                         drop_if_empty: bool = False):
        """
        删除满足条件的文档并根据需要将其移至回收站。
        :param query: 查询条件，字典格式
        :param skip: 跳过指定数量的文档，用于分页。
        :param limit: 返回结果的最大数量，默认返回所有匹配的文档。
        :param recyclable: 是否将文档移至回收站，默认为False
        :param drop_if_empty: 是否在删除所有满足条件的文档后，如果集合为空则删除集合，默认为False
        :return: 删除的文档数量

        Args:
            limit:
            skip:
        """

        if query is None:
            query = {}
        if self.collection is None:
            raise Exception("未选择集合")
        try:
            # 查找要删除的文档
            with self.rlock:
                if skip is not None and limit is not None:
                    documents_to_delete = list(self.collection.find(query).skip(skip).limit(limit))
                elif skip is not None:
                    documents_to_delete = list(self.collection.find(query).skip(skip))
                elif limit is not None:
                    documents_to_delete = list(self.collection.find(query).limit(limit))
                else:
                    documents_to_delete = list(self.collection.find(query))
            # 检查是否有文档需要删除
            if not documents_to_delete:
                logger.error("没有满足条件的文档需要删除。")
                return 0

            if recyclable:
                # 连接到回收站集合
                recycle_db = 'recycle_bin'
                recycle_collection_name = f"{recycle_db}:{str(self.db_name) + ' ' + str(self.collection_name)}"
                recycle_bin_collection = MongoDB(db_name=recycle_db)[recycle_collection_name]

                # 将要删除的文档移至回收站集合
                recycle_bin_collection.save_dict_list_to_collection(dict_list=documents_to_delete)
                logger.info(
                    f"已将 {len(documents_to_delete)} 个文档移至回收站 {recycle_db}:{recycle_collection_name}。")

            # 从原始集合中删除文档
            with self.rlock:
                result = self.collection.delete_many(query)
            logger.info(f"已删除 {result.deleted_count} 个文档。")

            # 检查集合是否为空并删除集合（如果需要）
            if drop_if_empty:
                with self.rlock:
                    remaining_documents = self.collection.count_documents({})
                    if remaining_documents == 0:
                        self.collection.drop()
                        logger.info(f"集合 {self.collection_name} 已删除, 因为它是空的。")

            return result.deleted_count
        except Exception as e:
            logger.error(f"删除文档时出错：{str(e)}")
            raise


class MongoDB:
    def __init__(
            self,
            uri='',
            host='localhost',
            port=27017,
            db_name: str = '',
            username: str = None,
            password: str = None,
            log_enabled: bool = True):
        """
        初始化 MongoDB 连接
        :param uri: uri
        :param host: MongoDB服务器地址
        :param port: MongoDB服务器端口
        :param db_name: 数据库名称
        :param username: 用户名
        :param password: 密码
        :param log_enabled: 是否开启日志
        """
        self.uri = uri
        self.host = host
        self.port = port
        self.log_enabled = log_enabled
        self.client = None
        self.db = None
        self.db_name = db_name
        # 先尝试从环境变量读取，如果环境变量没有，则使用传入的参数
        self.username = os.getenv("MONGO_USERNAME", username)
        self.password = os.getenv("MONGO_PASSWORD", password)
        self._connect_to_db()
        logger.info(f"已连接 MongoDB: {self.db_name}")

    def __getitem__(self, collection_name: str) -> CollectionWrapper:
        """
        获取指定的集合
        :param collection_name: 集合名称
        :return: 集合对象
        """
        if self.db is None:
            raise Exception("数据库未选择")
        if not isinstance(collection_name, str):
            raise TypeError("collection_name 必须为字符串")
        collection = self.db[collection_name]

        # 尝试获取集合统计信息以验证连接有效性
        try:
            collection_stats = collection.estimated_document_count()
            if self.log_enabled:
                logger.info(f"成功连接到集合 {self.db_name}:{collection_name}, 当前文档数: {collection_stats}")
        except Exception as e:
            logger.error(f"无法连接到集合 {self.db_name}:{collection_name}: {e}")
            raise
        return CollectionWrapper(self.db_name, self.db[collection_name], log_enabled=self.log_enabled)

    def _connect_to_db(self):
        if self.uri:
            self.client = MongoClient(self.uri)
            self.db = self.client[self.db_name]
            return
        try:
            if self.username and self.password:
                self.client = MongoClient(
                    f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.username}")
            else:
                self.client = MongoClient(f"mongodb://{self.host}:{self.port}")
            if self.db_name:
                self.db = self.client[self.db_name]
        except Exception as e:
            self._handle_connection_error(e)

    def _handle_connection_error(self, e):
        error_msg = f"无法连接到 MongoDB 数据库 ({self.db_name}), 请检查以下信息："
        if not self.username or not self.password:
            error_msg += "\n- 用户名和/或密码未提供或无效"
        error_msg += f"\n- 主机: {self.host}\n- 端口: {self.port}\n\n详细错误：{str(e)}"
        raise ConnectionError(error_msg)

    def close(self):
        """
        关闭与 MongoDB 的连接。
        """
        try:
            if self.client:
                self.client.close()
        except Exception as e:
            logger.error(f"关闭MongoDB连接时发生错误: {e}")
            raise
        logger.info("MongoDB 连接已关闭")


# 示例用法
if __name__ == "__main__":
    # 初始化MongoDB连接
    db = MongoDB(db_name="test_db")

    # 选择集合
    chapter_list = db['test_list']

    # 根据query_key更新
    info = {
        'name': '张三',
        'age': 20,
        'email': 'zhangsan@qq.com'
    }
    with ThreadPoolExecutor(max_workers=10) as executor:
        for i in range(10):
            executor.submit(chapter_list.save_dict_to_collection, info, query_key='name')
    # 保存数据字典
    info = [
        {
            'name': '张三',
            'age': 20,
            'email': 'zhangsan@example.com'
        },
        {
            'name': '李四',
            'age': 25,
            'email': 'lisi@example.com'
        }
    ]
    chapter_list.save_dict_list_to_collection(dict_list=info)
    # 查询集合所有数据
    chapter_list.find_documents()
    chapter_list.delete_documents()
    # 查询数据示例
    query = {"name": "John"}
    documents = chapter_list.find_documents(query=query)
    print(documents)
