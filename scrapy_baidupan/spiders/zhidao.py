# -*- coding: utf-8 -*-
from urllib import urlencode

import scrapy
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors import LinkExtractor
from scrapy.exceptions import DropItem

from scrapy_baidupan.items import PanLinkItem


class ZhidaoSpider(CrawlSpider):
    """从百度知道中查找word相关的百度云资源"""

    BAIDU_YUN_KEY = "百度云"

    name = "zhidao"

    allowed_domains = ["zhidao.baidu.com", "pan.baidu.com"]

    def __init__(self, word="", *args, **kwargs):
        super(ZhidaoSpider, self).__init__(*args, **kwargs)
        self.start_urls = [
            'http://zhidao.baidu.com/search?{0}'.format(
                urlencode({'word': word + " " + ZhidaoSpider.BAIDU_YUN_KEY})),
        ]
        # 记录已经处理过的项，用于查重
        self.processed_items = set()

    rules = (
        Rule(LinkExtractor(allow=(r'/question/\d+\.html',),
                           restrict_xpaths='//div[@id="wgt-list"]'),
             callback='parse_answer'),
    )

    def parse_answer(self, response):
        answer = response.css('.answer')

        for item in self._find_2(answer):
            if item['link'] not in self.processed_items:
                self.processed_items.add(item['link'])
                yield scrapy.Request(item['link'], callback=self.parse_url_validity, meta={'item': item})

        for item in self._find_3(answer):
            if item['link'] not in self.processed_items:
                self.processed_items.add(item['link'])
                yield scrapy.Request(item['link'], callback=self.parse_url_validity, meta={'item': item})

    def _find_2(self, answer):
        """查找格式 'http://pan.baidu.com/s/1ntDVLih 密码:ttsx'"""
        finder = answer.re(ur'(<[^>]+>([^<]+)<[^>]+>)\s?密码[：:]\s?([a-zA-z0-9]{4})')

        n = len(finder) / 3
        for i in range(n):
            link = finder[i * 3 + 1]
            item = PanLinkItem()
            item['link'] = link
            item['pwd'] = finder[i * 3 + 2]

            yield item

    def _find_3(self, answer):
        """查找格式 'http://pan.baidu.com/s/1ntDVLih'"""
        finder = answer.re(ur'(http://pan\.baidu\.com/s/\w{8})')

        for link in finder:
            item = PanLinkItem()
            item['link'] = link

            yield item

    def parse_url_validity(self, response):
        """打开百度云盘地址，查看是否有效"""
        title = response.xpath("//title/text()").extract()[0]

        item = response.meta['item']
        if title.find(u"链接不存在") == -1:
            yield item
        else:
            yield DropItem("链接不存在 %s" % item)
