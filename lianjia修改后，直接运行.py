import json
import scrapy
import logging
import copy
import pymysql
import threading
from multiprocessing import Process, Manager
from scrapy.crawler import CrawlerProcess
logger = logging.getLogger(__name__)
class LianjiaSpider(scrapy.Spider):
    name = 'lianjia'
    allowed_domains = ['sh.lianjia.com']
    start_urls = ['https://sh.lianjia.com/zufang/rs/']
    page = 2
    Q=None
    def parse(self, response):
        divs = response.xpath('//div[@class="content__list--item"]')
        item = {}
        for div in divs:
            address = div.xpath('.//div/p[2]/a/text()').extract()
            address = ''.join(address)
            item['房屋地址'] = address
            item['所在区'] = address[:2] + '区'
            href = 'https://sh.lianjia.com' + div.xpath('.//a[@class="twoline"]/@href').extract_first()
            item['详情页'] = href
            yield scrapy.Request(href, callback=self.detail_page_parse, dont_filter=True, meta={'item': copy.deepcopy(item)})
        # print("####################################下一页##########################################", self.page)
        # url = 'https://sh.lianjia.com/zufang/pg' + str(self.page) + '/#contentList'  # 构造URL
        # self.page = self.page + 1
        # if self.page > 3:  # 设置当前页面大于5，结束运行
        #     print("结束")
        #     return
        # yield scrapy.Request(url, callback=self.parse)  # 翻页跳转
    def detail_page_parse(self,response):
        item = response.meta['item']
        #户型
        type = response.xpath('.//ul[@class="content__aside__list"]/li[2]/text()').extract()
        if type==[]:
            return
        type=type[0]
        type_list = type.split()
        htype = type_list[0]
        harea = type_list[1]
        item['面积'] = harea
        item['户型'] = htype
        #租金
        price = response.xpath('//*[@id="aside"]/div[1]/span/text()').extract_first()
        price = price + '元/月'
        item['租金'] = price
        #楼层
        height_total = response.xpath('//*[@id="info"]/ul[1]/li[8]/text()').extract_first()
        height = height_total.split('：')[1]
        item['楼层'] = height
        #朝向
        towards_total = response.xpath('//*[@id="info"]/ul[1]/li[3]/text()').extract_first()
        htowards = towards_total.split('：')[1]
        item['朝向'] = htowards
        #电梯
        lift_total = response.xpath('//*[@id="info"]/ul[1]/li[9]/text()').extract_first()
        lift = lift_total.split('：')[1]
        item['电梯'] = lift
        #车位
        car_total = response.xpath('//*[@id="info"]/ul[1]/li[11]/text()').extract_first()
        car = car_total.split('：')[1]
        item['车位'] = car
        #租期
        RentTime_total = response.xpath('//*[@id="info"]/ul[1]/li[11]/text()').extract_first()
        RentTime = RentTime_total.split('：')[1]
        item['租期'] = RentTime
        #附近地铁
        try:
            subway = response.xpath('//*[@id="around"]/ul[2]/li/span[1]/text()').extract()[0]
        except:
            subway = '无'
        subway = subway.replace(" ", "")
        item['附近地铁'] = subway
        result=(item['房屋地址'],item['所在区'],item['租金'],item['户型'],item['面积'],item['朝向'],item['楼层'],item['电梯'],item['附近地铁'],item['车位'],item['租期'],item['详情页'])
        self.Q.put(json.dumps(result).encode())
                # logger.warn(item)
###########################################
############下面是新增内容############
def crawl(Q, is_obey):
    process = CrawlerProcess(settings={
        'ROBOTSTXT_OBEY': is_obey
    })
    process.crawl(LianjiaSpider, Q=Q)
    process.start()

class LogThread(threading.Thread):
    def __init__(self, Q):
        super(LogThread, self).__init__()
        self.Q = Q
        self.init_mysql()
    def init_mysql(self):#初始化数据库连接
        self.mydb = pymysql.connect(
            host="localhost",  # 默认用主机名
            user="root",  # 默认用户名
            password="030725",  # mysql密码
            database='house',  # 库名
        )
        self.cur = self.mydb.cursor()
    def run(self):
        while True:
            if not self.Q.empty():
                data=json.loads(self.Q.get().decode())
                self.write_data_to_mysql(data)
    def write_data_to_mysql(self,data):
        sql = " Insert into RentalInfo(`房屋地址`,`所在区`,`租金`,`户型`,`面积`,`朝向`,`楼层`,`电梯`,`地铁`,`车位`,`租期`,`详情页面`) values('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')"%tuple(data)
        print(sql)
        self.cur.execute(sql)
        self.mydb.commit()
if __name__ == "__main__":
    Q = Manager().Queue()#创建消息队列
    log_thread = LogThread(Q)
    p = Process(target=crawl, args=(Q, False))#执行爬虫线程
    p.start()
    log_thread.start() 