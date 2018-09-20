import scrapy
import requests
import re
import time
import json
from fake_useragent import UserAgent
import random
import socket
from urllib import request, error
from bs4 import BeautifulSoup as BS
from lxml import etree
from xpinyin import Pinyin
from scrapy.mail import MailSender
from scrapy.conf import settings
from lianjia.items import LianjiaItem


class Myspider(scrapy.Spider):
    name = 'lianjia'
    start_urls = 'https://hf.lianjia.com/ershoufang/'
    GLOBAL_start_urls = start_urls.rstrip('ershoufang/')

    def start_requests(self):
        user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.22 \
                         Safari/537.36 SE 2.X MetaSr 1.0'
        headers = {'User-Agent': user_agent}
        yield scrapy.Request(url=self.start_urls, headers=headers, method='GET', callback=self.get_area_url)

    def get_area_url(self, response):
        user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.22 \
                                 Safari/537.36 SE 2.X MetaSr 1.0'
        headers = {'User-Agent': user_agent}
        page = response.body.decode('utf-8')  # 解码
        soup = BS(page, 'lxml')  # html解析
        city_name = re.search("city_name: '(.*?)',", soup.text).group(1)
        p = Pinyin()
        city_str = p.get_pinyin(city_name, ' ').title().replace(' ', '')
        print(city_name, city_str)
        area_list = soup.find('div', {'data-role': 'ershoufang'}).find_all("a")  # 地区列表
        for area in area_list:
            area_pin = area['href']
            area_url = self.start_urls.rstrip('/ershoufang/') + area_pin  # 地区URL列表
            # print(area_url)
            yield scrapy.Request(url=area_url, headers=headers, method='GET', callback=self.house_info,
                                 meta={'id': area_pin})

    # 获取经纬度信息
    # 方法二：通过网页URL本身信息获取
    def get_Geo(self, url):  # 进入每个房源链接抓经纬度
        p = requests.get(url)
        contents = etree.HTML(p.content.decode('utf-8'))
        temp = str(contents.xpath('// html / body / script/text()'))
        # print(latitude,type(latitude))
        time.sleep(3)
        regex = '''resblockPosition(.+)'''  # 匹配经纬度所在的位置
        items = re.search(regex, temp)
        content = items.group()[:-1]  # 经纬度
        lng_lat = content.split('\'')[1].split(',')
        longitude = lng_lat[0]
        latitude = lng_lat[1].split('\\')[0]
        return longitude, latitude

    # 获取列表页面
    def get_page(self, url):
        # 两种设置headers的方法，方法一：
        # headers = {
        #     'User-Agent':"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 "
        #                     "(KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1",
        #     'Referer': GLOBAL_start_urls+'/ershoufang/',
        #     'Host': GLOBAL_start_urls.split('//')[1],
        #     'Connection': 'keep-alive',
        # }
        # 方法二：使用fake-useragent第三方库
        headers = {
            'User-Agent': UserAgent().random,
            'Referer': self.start_urls,
            'Host': self.start_urls.split('//')[1].rstrip('/ershoufang/'),
            'Connection': 'keep-alive'
        }
        timeout = 60
        socket.setdefaulttimeout(timeout)  # 设置超时,设置socket层的超时时间为60秒
        try:
            req = request.Request(url, headers=headers)
            response = request.urlopen(req)
            page = response.read().decode('utf-8')
            response.close()  # 注意关闭response
        except error.URLError as e:
            print(e.reason)
        time.sleep(random.random() * 3)  # 自定义,设置sleep()等待一段时间后继续下面的操作
        return page

    # for 南京、广州、杭州、合肥、青岛
    def house_info(self, response):
        page = response.body.decode('utf-8')  # 解码
        soup = BS(page, 'lxml')  # html解析
        if soup.find('div', class_='page-box house-lst-page-box'):
            pn_num = json.loads(soup.find('div', class_='page-box house-lst-page-box')['page-data'])  # 获取最大页数以及当前页
            max_pn = pn_num['totalPage']  # 获取最大页数,'curPage'存放当前页
            # max_pn = 1 # for test
            for i in range(1, max_pn + 1):
                temp_url = ''.join(self.start_urls.rstrip('/ershoufang/') + response.meta['id']) + 'pg{}'.format(str(i))
                req = requests.get(temp_url)
                soup = BS(req.text, 'lxml')
                if soup.find('ul', class_='sellListContent'):
                    all_li = soup.find('ul', class_='sellListContent').find_all('li')
                    for li in all_li:
                        house_url = li.find('a')['href']
                        print(house_url)
                        try:
                            item = LianjiaItem()
                            page = self.get_page(house_url)
                            soup = BS(page, 'lxml')
                            temp = soup.find('div', class_='areaName').text.split('\xa0')
                            item['district'] = temp[0].strip('所在区域')  # 区域名
                            item['street'] = temp[1]  # 街道名
                            if temp[2]:
                                item['position_info'] = temp[2]  # 地理位置附加信息，有些二手房为空
                            item['community'] = soup.select('.communityName')[0].text.strip('小区名称').strip('地图')
                            # 社区名
                            try:  # 有些城市没有小区的信息
                                communityUrl = self.start_urls.rstrip('/ershoufang/') + \
                                               soup.find('div', class_='communityName').find('a')['href']
                            except Exception:
                                communityUrl = None
                            item['community_url'] = communityUrl
                            item['house_url'] = house_url  # 租房网址，当测试的时候注释掉，以提高执行结果的速度
                            item['title'] = soup.select('.main')[0].text  # 标题
                            item['total_price'] = soup.select('.total')[0].text + '万'  # 总价
                            item['unit_price'] = soup.select('.unitPriceValue')[0].text  # 单价
                            temp = soup.find('div', class_='tax').text.split()
                            if len(temp) > 1:
                                item['shoufu'] = temp[0].strip('首付')  # 首付
                                item['tax'] = temp[1].strip('税费').strip('(仅供参考)')  # 税费
                            else:
                                # temp=首付及税费情况请咨询经纪人
                                item['shoufu'] = temp[0]
                                item['tax'] = temp[0]
                            # 户型信息，此信息差异较大，不提取
                            # temp = soup.find('div', id='infoList').find_all('div', class_='col')
                            # for i in range(0, len(temp), 4):
                            #     item[temp[i].text] = {}
                            #     item[temp[i].text]['面积'] = temp[i + 1].text
                            #     item[temp[i].text]['朝向'] = temp[i + 2].text
                            #     item[temp[i].text]['窗户'] = temp[i + 3].text

                            hid = soup.select('.houseRecord')[0].text.strip('链家编号').strip('举报')
                            item['house_id'] = hid
                            # hid:链家编号
                            try:  # 有些城市没有小区的信息
                                rid = soup.find('div', class_='communityName').find('a')['href'].strip(
                                    '/xiaoqu/').strip('/')
                                item['community_id'] = rid
                            except Exception:
                                item['community_id'] = None
                            # rid:社区ID
                            # 以下为获取小区简介信息,方法一：
                            # temp_url = '{}/ershoufang/housestat?hid={}&rid={}'.format(GLOBAL_start_urls,hid, rid)
                            # temp = json.loads(requests.get(temp_url).text)
                            # item['小区均价'] = temp['data']['resblockCard']['unitPrice']
                            # item['小区建筑年代'] = temp['data']['resblockCard']['buildYear']
                            # item['小区建筑类型'] = temp['data']['resblockCard']['buildType']
                            # item['小区楼栋总数'] = temp['data']['resblockCard']['buildNum']
                            # item['小区挂牌房源在售'] = temp['data']['resblockCard']['sellNum']
                            # item['小区挂牌房源出租房源数'] = temp['data']['resblockCard']['rentNum']
                            # # 获取小区经纬度的第三种方法
                            # item['经度'],item['纬度'] = temp['data']['resblockPosition'].split(',')
                            item['bulid_year'] = soup.find('div', class_='area').find('div',
                                                                                      class_='subInfo').get_text()  # 建造年代

                            # # 以下提取基本信息中的基本属性：房屋户型、所在楼层、建筑面积、套内面积、房屋朝向、建筑结构、装修情况、别墅类型、产权年限
                            # all_li = soup.find('div', class_='base').find('div', class_='content').find_all('li')
                            # for li in all_li:
                            #     item[li.find('span').text] = li.text.split(li.find('span').text)[1]
                            # # 以下提取基本信息中的交易属性：挂牌时间、交易权属、上次交易、房屋用途、房屋年限、产权所属、抵押信息、房本备件
                            # all_li = soup.find('div', class_='transaction').find('div', class_='content').find_all('li')
                            # for li in all_li:
                            #     item[li.find('span').text] = li.text.split(li.find('span').text)[1]
                            # 以上两个部分可以合并，提取基本信息，包括基本属性和交易属性：
                            all_li = soup.find('div', class_='introContent').find_all('li')
                            temp_dict = {}
                            for li in all_li:
                                temp_dict[li.find('span').text] = li.text.split(li.find('span').text)[1]
                            item['base_info'] = temp_dict
                            # 经纪人信息,该信息有可能为空：
                            if soup.find('div', class_='brokerInfoText fr'):
                                # 姓名
                                item['broker'] = soup.find('div', class_='brokerInfoText fr').find('a',
                                                                                                   target='_blank').text
                                item['broker_id'] = soup.find('div', class_='brokerName').find('a')['data-el']
                                item['broker_url'] = soup.find('div', class_='brokerName').find('a')['href']
                                temp = soup.find('div', class_='brokerInfoText fr').find('div', class_='evaluate')
                                if temp.find('a'):
                                    item['broker_commit_url'] = temp.find('a')['href']
                                    # 评分
                                    item['broker_score'] = temp.text.split('/')[0].strip('评分:')
                                    # 评价人数
                                    item['commit_num'] = temp.text.split('/')[1].strip('人评价')
                                else:
                                    item['broker_commit_url'] = '暂无评价'
                                # 联系电话,输出结果：'phone': '4008896039转8120'
                                item['broker_phone'] = soup.find('div', class_='brokerInfoText fr').find('div',
                                                                                                         class_='phone').text
                            else:
                                print('无经纪人信息')
                            # 获取二手房经纬度的方法
                            item['longtitude'], item['latitude'] = self.get_Geo(house_url)
                            if communityUrl:  # 有些城市没有小区的信息,判断小区URL是否存在
                                soup2 = BS(self.get_page(communityUrl), 'lxml')
                                CommunityInfo = soup2.find_all('div', class_='xiaoquInfoItem')
                                if soup2.find('span', class_='xiaoquUnitPrice'):
                                    item['community_unit_price'] = soup2.find('span', class_='xiaoquUnitPrice').text
                                else:
                                    item['community_unit_price'] = '暂无参考均价'
                                # 以下为获取小区简介信息,方法二：
                                temp_dict = {}
                                for temp in CommunityInfo:
                                    temp_dict[temp.find('span', class_='xiaoquInfoLabel').text] = \
                                        temp.find('span', class_='xiaoquInfoContent').text
                                item['CommunityInfo'] = temp_dict
                            else:
                                item['community_unit_price'] = None
                                item['CommunityInfo'] = None
                        except Exception:
                            print('nothing!')
                        yield item
                        # break # for test
                # break # for test

    def closed(self, reason):  # 爬取结束的时候发送邮件
        mailer = MailSender.from_settings(settings)  # 两种方法都可以，在setting文件中设置比较方便
        # mailer = MailSender(
        #     smtphost = "smtp.163.com",  # 发送邮件的服务器
        #     mailfrom = "myprojtest@163.com",  # 邮件发送者
        #     smtpuser = "myprojtest@163.com",  # 用户名
        #     smtppass = "1w3R5y7I",  # 发送邮箱的密码不是你注册时的密码，而是授权码！！！切记！
        #     smtpport = 25  # 端口号
        # )
        body = """
        二手房数据抓取完成！
        """
        subject = '二手房数据抓取完成！'
        # 如果说发送的内容太过简单的话，很可能会被当做垃圾邮件给禁止发送。
        to_receiver = ["myprojtest@163.com", "1575090938@qq.com"]
        sendRes = mailer.send(to=to_receiver, subject=subject, body=body)
        print(sendRes)


        # # for test:
        # def start_requests(self):
        #     user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.22 \
        #                      Safari/537.36 SE 2.X MetaSr 1.0'
        #     headers = {'User-Agent': user_agent}
        #     total_url = ['https://nj.lianjia.com/ershoufang/103101164368.html',
        #                  'https://nj.lianjia.com/ershoufang/103102024868.html',
        #                  'https://nj.lianjia.com/ershoufang/103100612985.html',
        #                  'https://nj.lianjia.com/ershoufang/103101701213.html',
        #                  'https://nj.lianjia.com/ershoufang/103101658043.html',
        #                  'https://nj.lianjia.com/ershoufang/103101501151.html']
        #     for url in total_url:
        #         print(url)
        #         yield scrapy.Request(url=url, headers=headers, method='GET', callback=self.hou_info,meta={'url':url})
        #
        # def hou_info(self, response):
        #         try:
        #             item = LianjiaItem()
        #             page = response.body.decode('utf-8')  # 解码
        #             soup = BS(page, 'lxml')
        #             house_url = response.meta['url']
        #             temp = soup.find('div', class_='areaName').text.split('\xa0')
        #             item['district'] = temp[0].strip('所在区域')  # 区域名
        #             item['street'] = temp[1]  # 街道名
        #             if temp[2]:
        #                 item['position_info'] = temp[2]
        #             item['community'] = soup.select('.communityName')[0].text.strip('小区名称').strip('地图')
        #             # 社区名
        #             communityUrl = self.start_urls.rstrip('/ershoufang/') + \
        #                            soup.find('div', class_='communityName').find('a')['href']
        #             item['community_url'] = communityUrl
        #             #
        #             # 以下获取租房所在经纬度
        #             # 方法一：通过百度地图获得
        #             # address = soup.find('div', class_='fl l-txt').find('a').text.strip('链家网').strip('站')
        #             # address = address + item['areaName'] + item['streetName'] + \
        #             #           item['communityName']
        #             # # print(address) # address为小区地址
        #             # item['latitude'] = getlnglat(address)['lng']  # 经度
        #             # item['longtitude'] = getlnglat(address)['lat']  # 维度
        #             # 方法二：通过网页链接本身信息获得
        #             # item['latitude'], item['longtitude'] = get_Geo(url)
        #             item['house_url'] = house_url  # 租房网址
        #             item['title'] = soup.select('.main')[0].text  # 标题
        #             item['total_price'] = soup.select('.total')[0].text + '万'  # 总价
        #             item['unit_price'] = soup.select('.unitPriceValue')[0].text  # 单价
        #             temp = soup.find('div', class_='tax').find('span').text.split()
        #             if len(temp) > 1:
        #                 item['shoufu'] = temp[0].strip('首付')  # 首付
        #                 item['tax'] = temp[1].strip('税费').strip('(仅供参考)')  # 税费
        #             else:
        #                 # temp=首付及税费情况请咨询经纪人
        #                 item['shoufu'] = temp
        #                 item['tax'] = temp
        #             # 户型信息，此信息差异较大，不提取
        #             # temp = soup.find('div', id='infoList').find_all('div', class_='col')
        #             # for i in range(0, len(temp), 4):
        #             #     item[temp[i].text] = {}
        #             #     item[temp[i].text]['面积'] = temp[i + 1].text
        #             #     item[temp[i].text]['朝向'] = temp[i + 2].text
        #             #     item[temp[i].text]['窗户'] = temp[i + 3].text
        #             # # 以下提取基本信息中的基本属性：房屋户型、所在楼层、建筑面积、套内面积、房屋朝向、建筑结构、装修情况、别墅类型、产权年限
        #             # all_li = soup.find('div', class_='base').find('div', class_='content').find_all('li')
        #             # for li in all_li:
        #             #     item[li.find('span').text] = li.text.split(li.find('span').text)[1]
        #             # # 以下提取基本信息中的交易属性：挂牌时间、交易权属、上次交易、房屋用途、房屋年限、产权所属、抵押信息、房本备件
        #             # all_li = soup.find('div', class_='transaction').find('div', class_='content').find_all('li')
        #             # for li in all_li:
        #             #     item[li.find('span').text] = li.text.split(li.find('span').text)[1]
        #             # 以上两个部分可以合并，提取基本信息，包括基本属性和交易属性：
        #             all_li = soup.find('div', class_='introContent').find_all('li')
        #             temp_dict = {}
        #             for li in all_li:
        #                 temp_dict[li.find('span').text] = li.text.split(li.find('span').text)[1]
        #             item['base_info'] = temp_dict
        #             hid = soup.select('.houseRecord')[0].text.strip('链家编号').strip('举报')
        #             item['house_id'] = hid
        #             # hid:链家编号
        #             rid = soup.find('div', class_='communityName').find('a')['href'].strip('/xiaoqu/').strip(
        #                 '/')
        #             item['community_id'] = rid
        #             # rid:社区ID
        #             # 以下为获取小区简介信息,方法一：
        #             # temp_url = '{}/ershoufang/housestat?hid={}&rid={}'.format(GLOBAL_start_urls,hid, rid)
        #             # temp = json.loads(requests.get(temp_url).text)
        #             # item['小区均价'] = temp['data']['resblockCard']['unitPrice']
        #             # item['小区建筑年代'] = temp['data']['resblockCard']['buildYear']
        #             # item['小区建筑类型'] = temp['data']['resblockCard']['buildType']
        #             # item['小区楼栋总数'] = temp['data']['resblockCard']['buildNum']
        #             # item['小区挂牌房源在售'] = temp['data']['resblockCard']['sellNum']
        #             # item['小区挂牌房源出租房源数'] = temp['data']['resblockCard']['rentNum']
        #             # # 获取小区经纬度的第三种方法
        #             # item['经度'],item['纬度'] = temp['data']['resblockPosition'].split(',')
        #             item['bulid_year'] = soup.find('div', class_='area').find('div',
        #                                                                       class_='subInfo').get_text()  # 建造年代
        #             # 经纪人信息,该信息有可能为空：
        #             if soup.find('div', class_='brokerInfoText fr'):
        #                 # 姓名
        #                 item['broker'] = soup.find('div', class_='brokerInfoText fr').find('a',
        #                                                                                    target='_blank').text
        #                 item['broker_id'] = soup.find('div', class_='brokerName').find('a')['data-el']
        #                 temp = soup.find('div', class_='brokerInfoText fr').find('span', class_='tag first')
        #                 if temp.find('a'):
        #                     item['broker_commit_url'] = temp.find('a')['href']
        #                     # 评分
        #                     item['broker_score'] = temp.text.split('/')[0].strip('评分:')
        #                     # 评价人数
        #                     item['commit_num'] = temp.text.split('/')[1].strip('人评价')
        #                 else:
        #                     item['broker_commit_url'] = '暂无评价'
        #                 # 联系电话,输出结果：'phone': '4008896039转8120'
        #                 item['broker_phone'] = soup.find('div', class_='brokerInfoText fr').find('div',
        #                                                                                   class_='phone').text
        #                 soup2 = BS(self.get_page(communityUrl), 'lxml')
        #                 CommunityInfo = soup2.find_all('div', class_='xiaoquInfoItem')
        #             else:
        #                 print('无经纪人信息')
        #             # 以下为获取小区简介信息,方法二：
        #             temp_dict={}
        #             for temp in CommunityInfo:
        #                 temp_dict[temp.find('span', class_='xiaoquInfoLabel').text] = \
        #                     temp.find('span', class_='xiaoquInfoContent').text
        #             item['CommunityInfo'] = temp_dict
        #             # 获取小区经纬度的第四种方法
        #             if temp.find('span', class_='actshowMap'):
        #                 lng_lat = temp.find('span', class_='actshowMap')['xiaoqu'].lstrip('[').rstrip(
        #                     ']').split(',')
        #                 # 附近门店的经纬度信息需要替换为temp.find('span', class_='actshowMap')['mendian'].split(',')
        #                 item['latitude'] = lng_lat[0]
        #                 item['longtitude'] = lng_lat[1]
        #             else:  # 没有则通过小区地址获得小区经纬度
        #                 self.house = house_url
        #                 item['latitude'], item['longtitude'] = self.get_Geo(self.house)
        #             if soup2.find('span', class_='xiaoquUnitPrice'):
        #                 item['community_unit_price'] = soup2.find('span', class_='xiaoquUnitPrice').text + '元/㎡'
        #             else:
        #                 item['community_unit_price'] = '暂无参考均价'
        #             # self.url_detail = house.xpath('div[1]/div[1]/a/@href').pop()
        #             # item['Latitude'] = self.get_latitude(self.url_detail)
        #
        #
        #             # print(item)
        #         except Exception:
        #             pass
        #         yield item
