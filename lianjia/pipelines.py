# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

import pymongo
from scrapy.conf import settings
from .items import LianjiaItem

class LianjiaPipeline(object):
    def __init__(self):
        host = settings['MONGODB_HOST']
        port = settings['MONGODB_PORT']
        db_name = settings['MONGODB_DBNAME']
        # 链接数据库
        client = pymongo.MongoClient(host=host,port=port)
        # 数据库登录需要帐号密码的话
        # self.client.admin.authenticate(settings['MINGO_USER'], settings['MONGO_PSW'])
        tdb = client[db_name]
        self.post = tdb[settings['MONGODB_DOCNAME']]
        # self.db = self.client[settings['MONGO_DB']]  # 获得数据库的句柄
        # self.coll = self.db[settings['MONGO_COLL']]  # 获得collection的句柄

    def process_item(self, item, spider):
        if isinstance(item,LianjiaItem):
            try:
                info = dict(item)  # 把item转化成字典形式
                if self.post.insert(info):  # 向数据库插入一条记录
                    print('bingo')
                else:
                    print('fail:')
                    print(info)
            except Exception:
                pass
        # return item  # 会在控制台输出原item数据，可以选择不写