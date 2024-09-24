import requests
import re
import json
import yaml
import logging
from scr.emotional_prediction import ModelInference  # 导入你实现的情感分析模型类
from datetime import datetime, timedelta

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
        self.fetch_days = config['qzone_fetch_days']
        print("qzone page:", self.pages)
        print("qzone fetch days:", self.fetch_days)

        # 初始化情感分析模型
        self.model_inference = ModelInference()  # 实例化情感分析模型

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

    def parse_create_time(self, create_time_str):
        now = datetime.now()

        if "昨天" in create_time_str:
            time_str = create_time_str.replace("昨天", "").strip()
            create_time_obj = datetime.strptime(f"{(now - timedelta(days=1)).strftime('%Y年%m月%d日')} {time_str}",
                                                '%Y年%m月%d日 %H:%M')
            create_time_str = create_time_obj.strftime('%Y年%m月%d日 %H:%M')  # 转换为日期+时间格式
        elif "前天" in create_time_str:
            time_str = create_time_str.replace("前天", "").strip()
            create_time_obj = datetime.strptime(f"{(now - timedelta(days=2)).strftime('%Y年%m月%d日')} {time_str}",
                                                '%Y年%m月%d日 %H:%M')
            create_time_str = create_time_obj.strftime('%Y年%m月%d日 %H:%M')  # 转换为日期+时间格式
        elif re.match(r'^\d{2}:\d{2}$', create_time_str):  # 只有时间的情况
            create_time_obj = datetime.strptime(f"{now.strftime('%Y年%m月%d日')} {create_time_str}",
                                                '%Y年%m月%d日 %H:%M')
            create_time_str = create_time_obj.strftime('%Y年%m月%d日 %H:%M')  # 转换为日期+时间格式
        else:
            # 超过前天的情况，只有日期部分
            try:
                create_time_obj = datetime.strptime(create_time_str, '%Y年%m月%d日')  # 解析为日期对象
            except ValueError:
                logging.warning(f"Failed to parse date: {create_time_str}")
                return None, create_time_str  # 返回None用于跳过

            return create_time_obj, create_time_str  # 保留原始日期字符串

        return create_time_obj, create_time_str  # 返回日期对象和处理后的日期时间字符串

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

                        # 在解析msglist的时候
                        if parsed_data.get('msglist'):
                            for item in parsed_data['msglist']:
                                text_html = item.get('content', '')
                                create_time = item.get('createTime', '')
                                text_clean = re.sub(r'<.*?>', '', text_html).replace('&nbsp;', ' ')

                                # 解析日期格式，返回解析后的对象和原始字符串
                                create_time_obj, create_time_str = self.parse_create_time(create_time)

                                # 如果返回了时间对象，则判断是否超过2天
                                if create_time_obj:
                                    current_time = datetime.now()
                                    delta_days = (current_time - create_time_obj).days
                                    if delta_days > self.fetch_days:
                                        continue  # 跳过超过指定天数的消息
                                else:
                                    # 如果仍然无法解析日期，可以选择跳过或记录日志
                                    logging.warning(f"Failed to parse date: {create_time}")
                                    continue

                                # 调用情感分析模型，获取预测结果
                                predicted_label, predicted_score = self.model_inference.predict(text_clean)

                                # 将消息、情感分析结果添加到 all_messages
                                all_messages.append({
                                    '时间': create_time_str,  # 无论是否解析成功，都使用原始字符串
                                    '内容': text_clean,
                                    '平台': 'QQ空间',
                                    '情感分析': predicted_label,  # 添加情感类别
                                    '情感得分': predicted_score  # 添加情感得分
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

if __name__ == '__main__':
    scraper = QQZoneScraper()
    posts = scraper.fetch_messages('276578410')
    print(posts)
