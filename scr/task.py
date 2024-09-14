from PyQt6.QtCore import QThread, pyqtSignal
from datetime import datetime, timedelta
import random
import time
import os
import pandas as pd
import json
from scr.read_data import ExcelProcessor
from scr.weibo import WeiboScraper
from scr.qzone import QQZoneScraper, TooManyRequestsError


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
        self.retry_later = {}  # 用于存储需要稍后重试的ID
        self.weibo = WeiboScraper()
        self.qzone = QQZoneScraper()

    def run(self):
        try:
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            root_folder_path = os.path.join(self.save_folder_path, f"Spider_{current_time}")
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

            # 重新处理之前失败的ID
            self.retry_failed_ids()

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

            school_id = str(header_dict['学校编号'])  # 确保转换为字符串
            grade = str(header_dict['年级'])  # 确保转换为字符串
            class_name = str(header_dict['班级'])  # 确保转换为字符串

            self.result.emit(f"正在处理文件: {file_path}")
            self.result.emit("\n头信息:")
            self.result.emit(str(header_dict))
            self.result.emit("数据:")
            self.result.emit(str(data))



            # 创建文件夹路径
            school_folder_path = os.path.join(root_folder_path, f"School_{school_id}")
            grade_folder_path = os.path.join(school_folder_path, f"Grade_{grade}")
            os.makedirs(grade_folder_path, exist_ok=True)

            # 创建班级信息JSON结构
            class_info = {
                "班级信息": {
                    "学校编号": school_id,
                    "年级": grade,
                    "班级": class_name
                },
                "学生动态": {}
            }

            for index, row in data.iterrows():
                if not self._is_running:
                    return
                student_name = str(row['学号']) + str(row['姓名'])  # 确保转换为字符串

                class_info["学生动态"][student_name] = []

                weibo_id = row['微博']
                if not pd.isna(weibo_id):
                    weibo_id = str(weibo_id)  # 确保转换为字符串
                    weibo_posts = self.retry_fetch_and_save(self.weibo, "微博", weibo_id, student_name)
                    class_info["学生动态"][student_name].extend(weibo_posts)

                qzone_id = row['qq空间']
                if not pd.isna(qzone_id):
                    qzone_id = str(qzone_id)  # 确保转换为字符串
                    qzone_posts = self.retry_fetch_and_save(self.qzone, 'qq空间', qzone_id, student_name)
                    class_info["学生动态"][student_name].extend(qzone_posts)

            # 保存班级信息到JSON文件
            class_filename = os.path.join(grade_folder_path, f"{class_name}班.json")
            with open(class_filename, 'w', encoding='utf-8') as f:
                json.dump(class_info, f, ensure_ascii=False, indent=4)

            self.result.emit(f"\n{file_path} 的所有帖子已保存到 {class_filename}")
        except Exception as e:
            self.result.emit(f"Error processing file {file_path}: {str(e)}")

    def retry_fetch_and_save(self, scraper, platform, id, student_name):
        retry_count = 0
        success = False
        max_retries = 5
        posts = []
        while retry_count < max_retries and not success:
            try:
                # sleep_time = round(random.uniform(1, 2), 2)
                # time.sleep(sleep_time)
                # 随机休息1-2秒再爬
                posts = scraper.fetch_messages(id)
                if not posts:
                    raise ValueError("No messages to save.")
                self.result.emit(f"\n已保存学生 {student_name}(ID: {id}) 的{platform}动态")
                success = True
            except TooManyRequestsError as e:
                self.result.emit(f"\n⚠获取学生 {student_name} ID {id} 的{platform}数据时出错: {str(e)}。将稍后重试。")
                self.add_to_retry_later(platform, id, student_name)
                break
            except Exception as e:
                if str(e) == "No messages to save.":
                    self.result.emit(f"\n⚠学生 {student_name} ID {id} 的{platform}没有动态可保存，跳过此学生。")
                    break  # 跳过，不重试
                retry_count += 1
                if retry_count < max_retries:
                    if platform == '微博':
                        delay = random.uniform(3 * 60, 5 * 60)  # 微博随机延迟3到5分钟
                    else:
                        delay = random.uniform(10 * 60, 15 * 60)  # QQ空间随机延迟10到15分钟
                    self.result.emit(
                        f"\n⚠获取学生 {student_name} ID {id} 的{platform}数据时出错: {str(e)}。将在 {delay / 60:.2f} 分钟后重试 (第 {retry_count} 次重试)。")

                    # 非阻塞等待
                    wait_until = datetime.now() + timedelta(seconds=delay)
                    while datetime.now() < wait_until:
                        if not self._is_running:
                            return []  # 如果在等待期间点击了“停止”，立即返回
                        time.sleep(1)  # 等待1秒后检查一次
                else:
                    self.result.emit(
                        f"\n⚠获取学生 {student_name} ID {id} 的{platform}数据时出错: {str(e)}。已达到最大重试次数。")
        return posts

    def add_to_retry_later(self, platform, id, student_name):
        if platform not in self.retry_later:
            self.retry_later[platform] = []
        self.retry_later[platform].append({
            'id': id,
            'student_name': student_name
        })

    def retry_failed_ids(self):
        if not any(self.retry_later.values()):
            self.result.emit("\n没有需要重试的任务，跳过重试步骤。")
            return

        self.result.emit("\n等待15分钟后开始重新处理由于使用人数过多而失败的任务...")

        # 等待15分钟
        time.sleep(15 * 60)

        retry_results = {}  # 用于存储重试成功的结果

        for platform, tasks in self.retry_later.items():
            for task in tasks:
                self.result.emit(f"\n重新处理: {task['student_name']} (ID: {task['id']}) 的{platform}动态")
                scraper = WeiboScraper() if platform == "微博" else QQZoneScraper()
                posts = self.retry_fetch_and_save(scraper, platform, task['id'], task['student_name'])

                if posts:  # 如果重试成功获取到动态
                    if task['student_name'] not in retry_results:
                        retry_results[task['student_name']] = []
                    retry_results[task['student_name']].extend(posts)

        # 将重试成功的结果保存到一个单独的文件中
        if retry_results:
            retry_results_filename = os.path.join(self.save_folder_path, "retry_results.json")
            with open(retry_results_filename, 'w', encoding='utf-8') as f:
                json.dump(retry_results, f, ensure_ascii=False, indent=4)
            self.result.emit(f"\n重试成功的任务结果已保存到 {retry_results_filename}")
        else:
            self.result.emit("\n重试后没有成功获取到任何任务的动态。")

        self.result.emit("\n所有失败的任务已重新处理。")
