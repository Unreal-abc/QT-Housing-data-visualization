import json
import scrapy
import logging
from PySide2.QtUiTools import QUiLoader
from PySide2.QtGui import QStandardItemModel, QStandardItem
from PySide2 import QtCore
from PySide2.QtCore import *
from PySide2.QtWidgets import (
    QApplication, QHBoxLayout, QItemDelegate, QPushButton, QTableView, QWidget)
from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtWebEngineWidgets import QWebEngineView
from PySide2.QtCore import QObject, Signal, Slot
from multiprocessing import Process, Manager
from scrapy.crawler import CrawlerProcess
import copy
class Form:
    Main_Form = None
logger = logging.getLogger(__name__)
class LianjiaSpider(scrapy.Spider):
    name = 'lianjia'
    allowed_domains = ['sh.lianjia.com']
    start_urls = ['https://sh.lianjia.com/zufang/rs/']
    page = 2  # 翻页 的页码
    Q=None
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
        self.Q.put(json.dumps(item).encode())
def crawl(Q, is_obey):
    process = CrawlerProcess(settings={
        'ROBOTSTXT_OBEY': is_obey
    })
    process.crawl(LianjiaSpider, Q=Q)
    process.start()
class Main_Form(QWidget):  # 
    def __init__(self):
        self.ui = QUiLoader().load('main.ui')  # 加载布局文件.ui
        # 连接信号
        self.ui.start.clicked.connect(self.start_clicked)
        self.ui.clear.clicked.connect(self.clear_clicked)
        self.myHtml = QWebEngineView(self.ui.label_2)
        self.myHtml.load(QUrl("file:///echarts.html"))
        self.myHtml.setGeometry(QtCore.QRect(0, 30, 1200, 920))
        self.log_thread = LogThread(self)
        self.log_thread.signal.connect(self.process_echarts)
    def process_echarts(self,temp_data):
        print("数据",temp_data)
        json_data=[]
        for key, value in temp_data.items():
            json_data.append({"value":value,"name":key})
        content=str( json.dumps(json_data, ensure_ascii=False)  ) 
        js_code="""
                var chartDom = document.getElementById('main');
        var myChart = echarts.init(chartDom);
        myChart.setOption({
            series: [
                {
                    data: """+content+"""
                }
            ]
        });
        """
        Form.Main_Form.myHtml.page().runJavaScript(js_code)     
    def start_clicked(self):
        self.Q = Manager().Queue()
        self.p = Process(target=crawl, args=(self.Q, False))
        self.p.start()
        self.log_thread.count=0
        self.log_thread.start()     
    def clear_clicked(self):
        Data.Model.removeRows(0, Data.Model.rowCount())
        js_code="""
                var chartDom = document.getElementById('main');
        var myChart = echarts.init(chartDom);
        myChart.setOption({
            series: [
                {
                    data:[{"value": 1, "name": "无"}]
                }
            ]
        });
        """
        Form.Main_Form.myHtml.page().runJavaScript(js_code)  
        Form.Main_Form.ui.text.setText("目前一共实时收集了0条数据")
        QMessageBox.information(Form.Main_Form.ui,"消息", "清除数据成功！")

class Data:
    Model = None
class LogThread(QThread):
    count=1
    temp_data={}
    signal = Signal(dict)    
    def __init__(self, gui):
        super(LogThread, self).__init__()
        self.gui = gui

    def run(self):
        while True:
            if not self.gui.Q.empty():
                data=json.loads(self.gui.Q.get().decode())
                print(data)
                self.read_data_to_tableview(data)
                # 睡眠10毫秒，否则太快会导致闪退或者显示乱码
                self.msleep(10)
    def read_data_to_tableview(self,data):
        item0 = QStandardItem(str(data["房屋地址"]))
        item1 = QStandardItem(str(data["详情页"]))
        item2 = QStandardItem(str(data["面积"]))
        item3 = QStandardItem(str(data["户型"]))
        item0.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        item1.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        item2.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        item3.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        Data.Model.appendRow([item0, item1, item2, item3])
        Form.Main_Form.ui.text.setText("目前一共实时收集了"+str(self.count)+"条数据")
        self.count=self.count+1
        if data["户型"] not in self.temp_data:
            self.temp_data[data["户型"]]=1
        else:
            self.temp_data[data["户型"]]=self.temp_data[data["户型"]]+1    
        self.signal.emit(copy.deepcopy(self.temp_data))
        print("数据加载成功！")
if __name__ == "__main__":
    app = QApplication([])
    Form.Main_Form = Main_Form()
    Form.Main_Form.ui.show()
    Data.Model = QStandardItemModel(0, 4)
    Data.Model.setHorizontalHeaderLabels(
        ["房屋地址", "详情页", "面积", "户型"])
    Form.Main_Form.ui.tableView.setModel(Data.Model)
    Form.Main_Form.ui.tableView.setColumnWidth(0,300)
    Form.Main_Form.ui.tableView.setColumnWidth(1,300)
    Form.Main_Form.ui.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)
    Form.Main_Form.ui.tableView.setEditTriggers(QAbstractItemView.NoEditTriggers)
    Form.Main_Form.ui.tableView.horizontalHeader().setFont(QFont('Microsoft YaHei', 18, QFont.Bold))
    app.exec_()
