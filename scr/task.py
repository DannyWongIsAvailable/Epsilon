from PyQt6.QtCore import QThread, pyqtSignal
from scr.read_data import ExcelProcessor
from scr.weibo import WeiboScraper
from scr.qzone import QQZoneScraper
import pandas as pd
from datetime import datetime
import os

# 定义一个后台工作线程类，用于处理文件
class Worker(QThread):
    progress = pyqtSignal(int)
    result = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self._is_running = True

    def run(self):
        try:
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            root_folder_path = os.path.join(os.getcwd(), f"Processed_{current_time}")
            os.makedirs(root_folder_path, exist_ok=True)

            files_to_process = []
            for root, _, files in os.walk(self.folder_path):
                for file_name in files:
                    if file_name.endswith(".xlsx") or file_name.endswith(".xls"):
                        files_to_process.append(os.path.join(root, file_name))

            total_files = len(files_to_process)
            for index, file_path in enumerate(files_to_process):
                if not self._is_running:
                    break
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
            self.result.emit("头信息:\n")
            self.result.emit(str(header_dict))
            self.result.emit("\n数据:\n")
            self.result.emit(str(data))

            weibo = WeiboScraper()
            qzone = QQZoneScraper()

            base_folder_path = os.path.join(root_folder_path, f"School_{school_id}")
            grade_folder_path = os.path.join(base_folder_path, f"Grade_{grade}")
            class_folder_path = os.path.join(grade_folder_path, f"Class_{class_name}")

            os.makedirs(class_folder_path, exist_ok=True)

            for index, row in data.iterrows():
                if not self._is_running:
                    break
                student_folder_path = os.path.join(class_folder_path, row['姓名'])
                os.makedirs(student_folder_path, exist_ok=True)

                weibo_id = row['微博']
                if not pd.isna(weibo_id):
                    try:
                        posts = weibo.fetch_posts(weibo_id)
                        weibo_filename = os.path.join(student_folder_path, "weibo.txt")
                        weibo.save_posts_to_file(posts, weibo_filename)
                        self.result.emit(
                            f"\n已保存学生 {row['姓名']} 的微博 (ID: {weibo_id}) 的帖子到 {weibo_filename}")
                    except Exception as e:
                        self.result.emit(f"\n⚠获取学生 {row['姓名']} 微博 ID {weibo_id} 的帖子时出错: {str(e)}")

                qzone_id = row['qq空间']
                if not pd.isna(qzone_id):
                    try:
                        messages = qzone.fetch_messages(qzone_id)
                        qzone_filename = os.path.join(student_folder_path, "qzone.txt")
                        qzone.save_posts_to_file(messages, qzone_filename)
                        self.result.emit(f"\n已保存学生 {row['姓名']} 的QQ(ID: {qzone_id}) 的帖子到 {qzone_filename}")
                    except Exception as e:
                        self.result.emit(f"\n⚠获取学生 {row['姓名']}  QQ(ID: {qzone_id}) 的帖子时出错: {str(e)}")

            self.result.emit(f"\n{file_path} 的所有帖子已保存到 {class_folder_path}")
        except Exception as e:
            self.result.emit(f"Error processing file {file_path}: {str(e)}")
