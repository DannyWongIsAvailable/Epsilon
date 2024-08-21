import requests
import re
import json
import yaml
import logging

# 设置日志记录，只输出到控制台，不保存到文件
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TooManyRequestsError(Exception):
    """自定义异常，用于表示请求过多导致的错误"""
    pass

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

                        if parsed_data.get('code') == -10000:
                            raise TooManyRequestsError("使用人数过多，请稍后再试")

                        if parsed_data.get('msglist'):
                            for item in parsed_data['msglist']:
                                text_html = item.get('content', '')
                                create_time = item.get('createTime', '')
                                text_clean = re.sub(r'<.*?>', '', text_html).replace('&nbsp;', ' ')
                                all_messages.append({
                                    '时间': create_time,
                                    '内容': text_clean,
                                    '平台': 'QQ空间'
                                })
                        else:
                            return all_messages
                    else:
                        raise ValueError("Failed to parse JSONP response")
                else:
                    logging.error(f"Request failed with status code: {response.status_code}")
                    raise ConnectionError(f"Request failed with status code: {response.status_code}")
            except TooManyRequestsError as e:
                logging.warning(str(e))
                raise  # 重新抛出异常，以便在上层代码中处理
            except Exception as e:
                logging.error(f"An error occurred: {e}")
                raise

        return all_messages
