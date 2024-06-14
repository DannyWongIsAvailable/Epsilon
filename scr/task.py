from PyQt6.QtCore import QThread, pyqtSignal
from datetime import datetime, timedelta
import random
import time
import os
import pandas as pd
from scr.read_data import ExcelProcessor
from scr.weibo import WeiboScraper
from scr.qzone import QQZoneScraper


class Worker(QThread):
    progress = pyqtSignal(int)
    result = pyqtSignal(str)
    finished = pyqtSignal()
    stopped = pyqtSignal()  # 新增的信号，用于用户手动停止

    def __init__(self, folder_path, save_folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.save_folder_path = save_folder_path
        self._is_running = True

    def run(self):
        try:
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            root_folder_path = os.path.join(self.save_folder_path, f"Processed_{current_time}")
            os.makedirs(root_folder_path, exist_ok=True)

            files_to_process = []
            for root, _, files in os.walk(self.folder_path):
                for file_name in files:
                    if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
                        files_to_process.append(os.path.join(root, file_name))

            total_files = len(files_to_process)
            for index, file_path in enumerate(files_to_process):
                if not self._is_running:
                    self.stopped.emit()  # 用户手动停止时发射信号
                    return
                self.process_file(file_path, root_folder_path)
                self.progress.emit((index + 1) * 100 // total_files)

            self.finished.emit()
        except Exception as e:
            self.result.emit(f"Error: {str(e)}")

    def stop(self):
        self._is_running = False

    def process_file(self, file_path, root_folder_path):
        try:
            processor = ExcelProcessor(file_path)
            processor.read_excel()

            header_dict = processor.get_header_dict()
            data = processor.get_data()

            school_id = header_dict['学校编号']
            grade = header_dict['年级']
            class_name = header_dict['班级']

            self.result.emit(f"正在处理文件: {file_path}")
            self.result.emit("\n头信息:")
            self.result.emit(str(header_dict))
            self.result.emit("数据:")
            self.result.emit(str(data))

            weibo = WeiboScraper()
            qzone = QQZoneScraper()

            base_folder_path = os.path.join(root_folder_path, f"School_{school_id}")
            grade_folder_path = os.path.join(base_folder_path, f"Grade_{grade}")
            class_folder_path = os.path.join(grade_folder_path, f"Class_{class_name}")

            os.makedirs(class_folder_path, exist_ok=True)

            for index, row in data.iterrows():
                if not self._is_running:
                    return
                student_folder_path = os.path.join(class_folder_path, row['姓名'])
                os.makedirs(student_folder_path, exist_ok=True)

                weibo_id = row['微博']
                if not pd.isna(weibo_id):
                    self.retry_fetch_and_save(weibo, "微博", weibo_id, student_folder_path, row['姓名'], "weibo.txt")

                qzone_id = row['qq空间']
                if not pd.isna(qzone_id):
                    self.retry_fetch_and_save(qzone,'qq空间', qzone_id, student_folder_path, row['姓名'], "qzone.txt")

            self.result.emit(f"\n{file_path} 的所有帖子已保存到 {class_folder_path}")
        except Exception as e:
            self.result.emit(f"Error processing file {file_path}: {str(e)}")

    def retry_fetch_and_save(self, scraper, platform, id, folder_path, student_name, filename):
        retry_count = 0
        success = False
        max_retries = 5
        while retry_count < max_retries and not success:
            try:
                posts = scraper.fetch_messages(id)
                save_path = os.path.join(folder_path, filename)
                scraper.save_posts_to_file(posts, save_path)
                self.result.emit(f"\n已保存学生 {student_name}(ID: {id}) 的{platform}动态 到 {save_path}")
                success = True
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    delay = random.uniform(3 * 60, 10 * 60)  # 随机延迟3到10分钟
                    self.result.emit(
                        f"\n⚠获取学生 {student_name} ID {id} 的数据时出错: {str(e)}。将在 {delay / 60:.2f} 分钟后重试 (第 {retry_count} 次重试)。")

                    # 非阻塞等待
                    wait_until = datetime.now() + timedelta(seconds=delay)
                    while datetime.now() < wait_until:
                        if not self._is_running:
                            return  # 如果在等待期间点击了“停止”，立即返回
                        time.sleep(1)  # 等待1秒后检查一次
                else:
                    self.result.emit(f"\n⚠获取学生 {student_name} ID {id} 的数据时出错: {str(e)}。已达到最大重试次数。")
