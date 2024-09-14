import time
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
import re
from lxml import etree

class Tieba_spider:
    def __init__(self, url, max_pages=None, csv_file='output.csv', max_retries=5):
        # 设置 Edge 浏览器的无头模式
        edge_options = Options()
        # edge_options.add_argument("--headless")  # 初始调试阶段关闭无头模式，以便观察行为
        edge_options.add_argument('--disable-gpu')
        edge_options.add_argument('--no-sandbox')

        # 使用 Edge 浏览器驱动程序
        edge_service = Service(r'F:\Programs\edgedriver\msedgedriver.exe')  # 替换为你的 msedgedriver 路径
        self.driver = webdriver.Edge(service=edge_service, options=edge_options)

        # 初始化参数
        self.url = url
        self.max_pages = max_pages
        self.csv_file = csv_file
        self.max_retries = max_retries  # 最大重试次数

        # 存储已抓取的帖子链接，避免重复
        self.scraped_links = set()
        # 页数计数
        self.page_count = 0
        # 帖子数量计数
        self.post_count = 0
        # 初始化 CSV 文件
        self.init_csv()

    def init_csv(self):
        # 初始化 CSV 文件，写入标题行
        with open(self.csv_file, mode='w', encoding='utf-8-sig', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['text'])

    def save_to_csv(self, item):
        # 如果链接已经存在于集合中，跳过保存
        if item.get('link', '') in self.scraped_links:
            return
        # 否则，将链接添加到集合中，并保存数据到 CSV 文件
        self.scraped_links.add(item.get('link', ''))
        with open(self.csv_file, mode='a', encoding='utf-8-sig', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([item.get('text', '')])

    # 采集百度贴吧的数据
    def spider_tieba(self):
        # 从传入的 URL 开始爬取
        self.spider_tieba_list(self.url)

    # 采集百度贴吧列表数据
    def spider_tieba_list(self, url):
        retries = 0
        while retries < self.max_retries:
            print(f"Fetching URL: {url} (Attempt {retries + 1}/{self.max_retries})")
            self.driver.get(url)

            # 等待页面加载
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@class="t_con cleafix"]'))
                )
            except Exception as e:
                print("等待页面加载时出错：", e)
                retries += 1
                self.driver.refresh()  # 刷新页面
                continue

            # 检查页面是否加载了帖子
            response_txt = self.driver.page_source
            html = etree.HTML(response_txt)
            post_containers = html.xpath('//div[@class="t_con cleafix"]')

            if not post_containers:
                print("未找到帖子内容，重试...")
                retries += 1
                self.driver.refresh()  # 刷新页面
                continue  # 重试加载页面
            else:
                # 如果找到内容，退出重试循环
                break

        if retries == self.max_retries:
            print("超过最大重试次数，停止爬取。")
            return

        # 增加页数计数，避免无限递归
        self.page_count += 1
        if self.max_pages and self.page_count > self.max_pages:
            print("达到最大页数限制，停止爬取。")
            return

        # 处理帖子数据
        for post in post_containers:
            item = dict()

            # 提取标题
            title_element = post.xpath('.//div[@class="threadlist_title pull_left j_th_tit "]/a')
            if title_element:
                title = title_element[0].get('title')
                item['link'] = 'https://tieba.baidu.com' + title_element[0].get('href')
            else:
                title = 'N/A'
                item['link'] = 'N/A'

            # 检查帖子是否已抓取
            if item['link'] in self.scraped_links:
                continue  # 如果已经抓取过，跳过此帖子

            # 提取帖子内容
            content_element = post.xpath('.//div[@class="threadlist_abs threadlist_abs_onlyline "]/text()')
            content = content_element[0].strip() if content_element else 'N/A'

            # 拼接标题和内容成为文本
            text = f"{title}。{content}"
            item['text'] = self.filter_emoji(text)

            # 增加已抓取的帖子计数
            self.post_count += 1

            print(f"Text: {item['text']}")  # 调试输出

            # 保存帖子数据到 CSV
            self.save_to_csv(item)

        # 输出当前已抓取的帖子数量
        print(f"当前已获取的帖子数量: {self.post_count}")

        # 查找下一页链接并继续抓取
        self.go_to_next_page(html)

    # 处理下一页的逻辑
    def go_to_next_page(self, html):
        # 查找下一页按钮
        nex_page = html.xpath('//div[@id="frs_list_pager"]//a[@class="next pagination-item "]/@href')
        if len(nex_page) > 0:
            next_url = 'https:' + nex_page[0]
            print(f"下一页的 URL: {next_url}")
            self.spider_tieba_list(next_url)
        else:
            print("没有找到下一页按钮，或已到达最后一页。")

    # 过滤表情
    def filter_emoji(self, desstr, restr=''):
        try:
            co = re.compile(u'[\U00010000-\U0010ffff]')
        except re.error:
            co = re.compile(u'[\uD800-\uDBFF][\uDC00-\uDFFF]')
        return co.sub(restr, desstr)

    def close(self):
        self.driver.quit()

if __name__ == "__main__":
    # 初始化参数
    url = 'https://tieba.baidu.com/f?kw=%E5%AD%99%E7%AC%91%E5%B7%9D&ie=utf-8'
    max_pages = 100  # 不传入最大页数，默认一直爬取直到尾页
    csv_file = 'test.csv'

    # 记录开始时间
    start_time = time.time()

    # 创建爬虫实例并开始爬取
    spider = Tieba_spider(url, max_pages, csv_file)
    spider.spider_tieba()

    # 记录结束时间
    end_time = time.time()

    spider.close()

    # 计算爬取时长（以秒为单位）
    duration = end_time - start_time

    # 转换为小时和分钟
    hours = int(duration // 3600)
    minutes = int((duration % 3600) // 60)

    # 输出爬取时长
    if hours == 0:
        print(f"爬取时长: {minutes}分钟")
    else:
        print(f"爬取时长: {hours}小时{minutes}分钟")
