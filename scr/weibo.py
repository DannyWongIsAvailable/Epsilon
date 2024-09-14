import requests
from requests.exceptions import RequestException, HTTPError, ConnectionError, Timeout
import yaml
import logging
from scr.emotional_prediction import ModelInference  # 导入你实现的情感分析模型类
from datetime import datetime


# 解析微博的 create_time 格式
def parse_weibo_time(weibo_time_str):
    return datetime.strptime(weibo_time_str, '%a %b %d %H:%M:%S %z %Y')


# 设置日志记录，只输出到控制台，不保存到文件
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class WeiboScraper:
    def __init__(self, config_file='./config.yaml'):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        self.url = 'https://weibo.com/ajax/statuses/mymblog'
        self.headers = config.get('weibo_headers', {})
        self.pages = config.get('weibo_pages', 1)  # Default to 1 if not set in config

        # 初始化情感分析模型
        self.model_inference = ModelInference()  # 实例化情感分析模型

    def fetch_messages(self, uid):
        results = []

        for page in range(1, self.pages + 1):
            params = {
                'uid': uid,
                'page': page,
                'feature': '0'
            }

            try:
                response = requests.get(self.url, headers=self.headers, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                if 'data' in data and 'list' in data['data']:
                    for item in data['data']['list']:
                        text_raw = item.get('text_raw', '')
                        create_time_str = item.get('created_at', '')  # create_time 字符串

                        # 解析微博创建时间为 datetime 对象
                        try:
                            create_time = parse_weibo_time(create_time_str)
                        except ValueError:
                            logging.warning(f"无法解析日期格式: {create_time_str}")
                            continue

                        # 获取当前时间并计算日期差异
                        current_time = datetime.now(create_time.tzinfo)  # 使用相同的时区信息
                        if (current_time - create_time).days > 2:
                            # logging.info(f"消息时间 {create_time_str} 超过2天，不保存该消息")
                            continue

                        # 调用情感分析模型，获取预测结果
                        predicted_label, predicted_score = self.model_inference.predict(text_raw)

                        # 将微博信息和情感分析结果添加到结果中
                        post = {
                            '时间': create_time_str,  # 保留原始字符串表示
                            '内容': text_raw,
                            '平台': '微博',
                            '情感类别': predicted_label,  # 添加情感类别
                            '情感得分': predicted_score  # 添加情感得分
                        }
                        results.append(post)
            except (HTTPError, ConnectionError, Timeout, RequestException) as e:
                logging.error(f"Request failed: {e}")
                raise

        return results


# 使用示例
if __name__ == '__main__':
    scraper = WeiboScraper(config_file='../config.yaml')
    uid = '1782488734'  # 替换为目标用户的UID
    messages = scraper.fetch_messages(uid)

    # 打印结果
    for message in messages:
        print(f"时间: {message['时间']}, 内容: {message['内容']}, 平台: {message['平台']}, "
              f"情感类别: {message['情感类别']}, 情感得分: {message['情感得分']}")
