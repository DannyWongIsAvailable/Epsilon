# -*- coding:utf-8 -*-
import time
import psutil
import pywinauto
from pywinauto.application import Application
import pandas as pd

class WeChatPyQReader:
    def __init__(self):
        self.app = None
        self.pyq_window = None

    def get_wechat_pid(self):
        """获取微信进程的PID"""
        for proc in psutil.process_iter():
            try:
                pinfo = proc.as_dict(attrs=['pid', 'name'])
            except psutil.NoSuchProcess:
                pass
            else:
                if 'WeChat.exe' == pinfo['name']:
                    return pinfo['pid']
        raise Exception("WeChat进程未找到")

    def connect_wechat(self, pid):
        """连接微信应用"""
        if pid:
            self.app = Application(backend='uia').connect(process=pid)
        else:
            raise Exception("WeChat进程未找到")

    def open_pyq(self):
        """打开朋友圈窗口"""
        win = self.app['微信']
        win.set_focus()  # 将微信窗口置于前台
        win.restore()    # 还原窗口（如果最小化）
        pyq_button = win.child_window(title='朋友圈', control_type="Button")
        pyq_button.draw_outline()
        coords = pyq_button.rectangle()
        pywinauto.mouse.click(button='left', coords=(coords.left + 10, coords.top + 10))
        self.pyq_window = self.app['朋友圈']
        self.pyq_window.draw_outline()

    def read_pyq(self, times=20):
        """读取朋友圈内容并返回DataFrame"""
        self.pyq_window.set_focus()
        data = []  # 用于存储朋友圈内容
        for i in range(times):
            pyq_list = self.pyq_window.child_window(title="朋友圈", control_type="List").children(control_type="ListItem")
            count = len(pyq_list)
            for k in range(count - 1):
                try:
                    pyq_item = self.pyq_window.child_window(control_type="ListItem", found_index=k)
                    text = [line for line in pyq_item.window_text().split('\n') if line]

                    publisher = text[0]  # 发布者
                    content = '\n'.join(text[1:-1])  # 内容
                    message_time = text[-1]  # 时间

                    data.append([publisher, content, message_time])
                except Exception as e:
                    raise Exception(f"读取错误: {e}")
            for j in range(2):
                pywinauto.keyboard.send_keys('{DOWN}')
                time.sleep(0.5)  # 增加时间间隔以提高稳定性
        self.pyq_window.close()  # 关闭朋友圈窗口
        return data

    def get_pyq_data(self):
        """主函数，获取朋友圈数据并返回DataFrame"""
        pid = self.get_wechat_pid()
        self.connect_wechat(pid)
        self.open_pyq()
        data = self.read_pyq()
        df = pd.DataFrame(data, columns=["发布者", "内容", "时间"])
        return df

    @staticmethod
    def save_to_excel(df, filename='wechat_pyq.xlsx'):
        """保存DataFrame到Excel文件"""
        df.to_excel(filename, index=False)

if __name__ == '__main__':
    wechat = WeChatPyQReader()
    df = wechat.get_pyq_data()
    print(df)
    wechat.save_to_excel(df)
