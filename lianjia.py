# import scrapy
# import logging

# logger = logging.getLogger(__name__)

# class LianjiaSpider(scrapy.Spider):
#     name = 'lianjia'
#     allowed_domains = ['sh.lianjia.com']
#     start_urls = ['https://sh.lianjia.com/zufang/rs/']

#     def parse(self, response):
#         divs = response.xpath('//div[@class="content__list--item"]')
#         for div in divs:
#             result=div.xpath("string(.)").extract()[0].replace(" ","").split("\n")
#             result = [i for i in result if i != '']#去除空元素
#             print(result)

import scrapy
import logging
import copy

logger = logging.getLogger(__name__)
class LianjiaSpider(scrapy.Spider):
    name = 'lianjia'
    allowed_domains = ['sh.lianjia.com']
    start_urls = ['https://sh.lianjia.com/zufang/rs/']
    page = 2  # 翻页 的页码

    def parse(self, response):
        divs = response.xpath('//div[@class="content__list--item"]')
        item = {}
        for div in divs:
            address = div.xpath('.//div/p[2]/a/text()').extract()
            address = ''.join(address)
            item['房屋地址'] = address
            href = 'https://sh.lianjia.com' + div.xpath('.//a[@class="twoline"]/@href').extract_first()
            item['详情页'] = href
            yield scrapy.Request(href, callback=self.detail_page_parse, dont_filter=True, meta={'item': copy.deepcopy(item)})

        # 翻页
        print("####################################下一页##########################################",self.page)
        url = 'https://sh.lianjia.com/zufang/pg' +str(self.page) + '/#contentList'  # 构造URL
        self.page = self.page+1
        if self.page > 5:#设置当前页面大于5，结束运行
            print("结束")
            return
        yield scrapy.Request(url, callback=self.parse)  # 翻页跳转

    def detail_page_parse(self, response):
        item = response.meta['item']
        type = response.xpath(
            './/ul[@class="content__aside__list"]/li[2]/text()').extract()
        if type == []:
            return
        type = type[0]
        type_list = type.split()
        htype = type_list[0]
        harea = type_list[1]
        item['面积'] = harea
        item['户型'] = htype
        logger.warn(item)
