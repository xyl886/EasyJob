#!usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author:18034
@file: BaiduAction.py
@time: 2025/04/21
"""
import os

from Core.JobBase import JobBase


class ZzgczAction(JobBase):
    job_id = [700001, 700002]
    folder = os.path.dirname(os.path.abspath(__file__))

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.json_headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,ja;q=0.5',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
            'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Microsoft Edge";v="122"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        self.text_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,ja;q=0.5',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
            'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Microsoft Edge";v="122"',
            'sec-ch-ua-mobile': '?0',
        }

    def on_run(self):
        if self.job_id == 700001:
            self.collect(1)

    def collect(self, pgn):
        self.logger.info(f"Starting web pgn: {pgn}")
        json_data = {
            'scene': 'all',
            'title': '',
            'page': pgn,
            'pageSize': 24,
        }
        res_json = self.send_request(
            'https://zzgcz.com/api/search',
            'post',
            headers=self.json_headers,
            json_data=json_data,
            dump_file_name=f'{self.job_id}_{pgn}.json',
            res_type='json')

        # 使用自定义集合
        results = res_json.get('results')
        self.db['pages'].save_dict_list_to_collection(results, 'id')
