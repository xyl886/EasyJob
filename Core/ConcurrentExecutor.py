#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: xyl
@file:  ConcurrentExecutor.py
@time: 2025/08/17
"""


class ConcurrentExecutor:
    def ThreadRun(self, _fun, run_list, chunk_size=16, *args, **kwargs):
        """
         使用线程池并发执行任务
         该函数创建一个线程池，将任务列表中的每个元素分配给不同的线程执行。
         支持传递自定义参数给任务函数，并自动管理线程池的生命周期。
         :param _fun: 要执行的任务函数，第一个参数必须接收run_list中的元素
         :param run_list: 任务数据列表，每个元素将作为参数传递给任务函数，必须接受 run_info
         :param chunk_size: 线程池最大工作线程数，默认16
         """
        from concurrent.futures import ThreadPoolExecutor
        run_list = list(run_list)
        with ThreadPoolExecutor(max_workers=chunk_size) as executor:
            for run_info in run_list:
                executor.submit(_fun, run_info, *args, **kwargs)

    def ProcessRun(self, _fun, run_list, chunk_size=16, *args, **kwargs):
        """
        使用进程池并发执行任务
        适合CPU密集型任务，避免GIL限制
        :param _fun: 要执行的任务函数
        :param run_list: 任务数据列表
        :param chunk_size: 进程池最大工作进程数，默认16
        """
        from concurrent.futures import ProcessPoolExecutor
        run_list = list(run_list)
        with ProcessPoolExecutor(max_workers=chunk_size) as executor:
            for run_info in run_list:
                executor.submit(_fun, run_info, *args, **kwargs)

    async def AsyncRun(self, _fun, run_list, chunk_size=16, *args, **kwargs):
        """
        使用asyncio实现协程并发
        适合IO密集型任务
        :param _fun: 异步任务函数(需用async定义)
        :param run_list: 任务数据列表
        :param chunk_size: 最大并发数，默认16
        """
        import asyncio
        semaphore = asyncio.Semaphore(chunk_size)

        async def limited_task(run_info):
            async with semaphore:
                return await _fun(run_info, *args, **kwargs)

        tasks = [limited_task(run_info) for run_info in run_list]
        await asyncio.gather(*tasks)

    def MultiProcessRun(self, _fun, run_list, chunk_size=16, *args, **kwargs):
        """
        使用multiprocessing.Pool实现多进程
        :param _fun: 要执行的任务函数
        :param run_list: 任务数据列表
        :param chunk_size: 进程池大小，默认16
        """
        from multiprocessing import Pool

        with Pool(processes=chunk_size) as pool:
            results = [pool.apply_async(_fun, (run_info, *args), kwargs)
                       for run_info in run_list]
            [result.get() for result in results]  # 等待所有任务完成

    def JoblibRun(self, _fun, run_list, chunk_size=16, *args, **kwargs):
        """
        使用joblib实现并行计算
        适合科学计算和机器学习任务
        :param _fun: 要执行的任务函数
        :param run_list: 任务数据列表
        :param chunk_size: 并行工作数，默认16
        """
        from joblib import Parallel, delayed

        Parallel(n_jobs=chunk_size)(delayed(_fun)(run_info, *args, **kwargs) for run_info in run_list)

    def GeventRun(self, _fun, run_list, chunk_size=16, *args, **kwargs):
        """
        使用gevent实现协程并发
        适合高IO密集型任务
        :param _fun: 要执行的任务函数
        :param run_list: 任务数据列表
        :param chunk_size: 协程池大小，默认16
        """
        from gevent.pool import Pool as GeventPool
        from gevent import monkey
        monkey.patch_all()  # 打补丁替换标准库中的阻塞式IO
        pool = GeventPool(chunk_size)
        for run_info in run_list:
            pool.spawn(_fun, run_info, *args, **kwargs)
        pool.join()

    def MultiTabs(self, _fun, tab_list, chunk_size=10, *args, **kwargs):
        """
        通用的 DrissionPage 多标签页并发处理函数
        :param _fun: 处理单个任务的函数，必须接受两个参数：tab(ChromiumTab) 和 tab_info
        :param tab_list: 待处理的任务列表（每个元素会传递给_fun）
        :param chunk_size: 每组并发任务数（默认10）
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from DrissionPage import ChromiumPage

        tab_list = list(tab_list)
        grouped = [
            tab_list[i:i + chunk_size]
            for i in range(0, len(tab_list), chunk_size)
        ]
        for group in grouped:
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
            for future in as_completed(futures):
                try:
                    future.result()  # 获取结果（会抛出异常）
                except Exception as e:
                    print(f"Task failed: {e}")
            self.page.close_tabs(tabs)
