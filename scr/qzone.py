import requests
import re
import json
import yaml
import logging

# 设置日志记录，只输出到控制台，不保存到文件
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class QQZoneScraper:
    def __init__(self):
        self.session = requests.Session()
        config = self.load_config()
        self.headers = config['qzone_headers']
        self.headers['cookie'] = config['qzone_headers']['cookie']
        self.g_tk = self.gen_gtk(self.headers['cookie'])
        self.pages = config['qzone_pages']

    @staticmethod
    def load_config():
        with open("./config.yaml", 'r', encoding='utf-8') as ymlfile:
            return yaml.safe_load(ymlfile)

    def gen_gtk(self, cookie):
        p_skey_pattern = re.compile(r'p_skey=(.*?);')
        match = p_skey_pattern.search(cookie)
        if match:
            p_skey_value = match.group(1)
        else:
            raise ValueError("p_skey not found in cookie")

        t = 5381
        for i in p_skey_value:
            t += (t << 5) + ord(i)
        return t & 2147483647

    def fetch_messages(self, user_id, messages_per_page=20):
        base_url = 'https://user.qzone.qq.com/proxy/domain/taotao.qq.com/cgi-bin/emotion_cgi_msglist_v6'
        all_messages = []

        for pos in range(0, self.pages * messages_per_page, messages_per_page):
            params = {
                'uin': user_id,
                'ftype': '0',
                'sort': '0',
                'pos': str(pos),
                'num': str(messages_per_page),
                'replynum': '100',
                'g_tk': self.g_tk,
                'callback': '_preloadCallback',
                'code_version': '1',
                'format': 'jsonp',
                'need_private_comment': '1',
            }

            try:
                response = self.session.get(base_url, headers=self.headers, params=params, timeout=10)
                if response.ok:
                    data = response.text
                    jsonp_pattern = re.compile(r"_preloadCallback\((.*)\);")
                    match = jsonp_pattern.search(data)
                    if match:
                        json_data = match.group(1)
                        parsed_data = json.loads(json_data)

                        if parsed_data.get('msglist'):
                            for item in parsed_data['msglist']:
                                text_html = item.get('content', '')
                                createTime = item.get('createTime', '')
                                text_clean = re.sub(r'<.*?>', '', text_html).replace('&nbsp;', ' ')
                                all_messages.append({
                                    'createTime': createTime,
                                    'content': text_clean
                                })
                        else:
                            return all_messages
                    else:
                        raise ValueError("Failed to parse JSONP response")
                else:
                    logging.error(f"Request failed with status code: {response.status_code}")
                    raise ConnectionError(f"Request failed with status code: {response.status_code}")
            except Exception as e:
                logging.error(f"An error occurred: {e}")
                raise

        return all_messages

    def save_posts_to_file(self, messages, filename='qzone_posts.txt'):
        if not messages:
            return  # 如果messages为空，则不保存
        with open(filename, 'w', encoding='utf-8') as f:
            for message in messages:
                f.write(f"╔═════════{message['createTime']}════════╗\n")
                f.write(message['content'] + "\n")
                f.write("╚═══════════════════════════╝\n")

if __name__ == "__main__":
    try:
        user_id = '374749536'
        scraper = QQZoneScraper()
        messages = scraper.fetch_messages(user_id)
        scraper.save_posts_to_file(messages, 'qzone_posts.txt')
    except Exception as e:
        logging.error(f"An error occurred: {e}")
