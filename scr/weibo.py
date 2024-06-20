import requests
from requests.exceptions import RequestException, HTTPError, ConnectionError, Timeout
import yaml
import logging

# 设置日志记录，只输出到控制台，不保存到文件
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WeiboScraper:
    def __init__(self, config_file='./config.yaml'):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        self.url = 'https://weibo.com/ajax/statuses/mymblog'
        self.headers = config.get('weibo_headers', {})
        self.pages = config.get('weibo_pages', 1)  # Default to 1 if not set in config

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
                        post = {
                            'time': item.get('created_at', ''),
                            'text': item.get('text_raw', '')
                        }
                        results.append(post)
            except (HTTPError, ConnectionError, Timeout, RequestException) as e:
                logging.error(f"Request failed: {e}")
                raise

        return results

    def save_posts_to_file(self, posts, filename):
        if not posts:
            return  # 如果messages为空，则不保存
        with open(filename, 'w', encoding='utf-8') as f:
            for post in posts:
                f.write(f"╔═════════{post['time']}════════╗\n")
                f.write(post['text'] + "\n")
                f.write("╚═════════════════════════════════════╝\n")

