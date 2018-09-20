# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class LianjiaItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    district = scrapy.Field() # 区域
    street = scrapy.Field() # 街道
    position_info = scrapy.Field()  # 位置信息补充
    community = scrapy.Field()  # 小区
    community_url = scrapy.Field()  # 小区URL
    latitude = scrapy.Field()  # 小区纬度
    longtitude = scrapy.Field()  # 小区经度
    house_url = scrapy.Field()  # 租房网址
    title = scrapy.Field()  # 租房信息标题
    total_price = scrapy.Field()  # 房屋总价
    unit_price = scrapy.Field()  # 每平方单价
    shoufu = scrapy.Field()  # 首付
    tax = scrapy.Field()  # 税费
    house_id = scrapy.Field()  # 房屋链家ID
    community_id = scrapy.Field()  # 社区ID
    bulid_year = scrapy.Field()  # 房屋建造年代
    base_info=scrapy.Field()  # 基本信息，包括基本属性和交易属性
    broker = scrapy.Field()  # 经纪人姓名
    broker_id = scrapy.Field()  # 经纪人ID
    broker_url = scrapy.Field()  # 经纪人URL
    broker_score = scrapy.Field()  # 经纪人评分
    commit_num = scrapy.Field()  # 评价人数
    broker_commit_url = scrapy.Field()  # 经纪人评价URL
    broker_phone = scrapy.Field()  # 经纪人电话
    CommunityInfo=scrapy.Field()
    community_unit_price = scrapy.Field()  # 小区均价