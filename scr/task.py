# task.py
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
from openpyxl.reader.excel import load_workbook


class Worker(QThread):
    progress = pyqtSignal(int)
    result = pyqtSignal(str)
    finished = pyqtSignal()
    stopped = pyqtSignal()  # 新增的信号，用于用户手动停止

    def __init__(self, folder_path):
        super().__init__()

        self.folder_path = folder_path
        self._is_running = True
        self.retry_later = {}  # 用于存储需要稍后重试的ID
        self.weibo = WeiboScraper()
        self.qzone = QQZoneScraper()

    def run(self):
        try:
            # 创建输出目录
            output_folder = os.path.join(os.path.dirname(self.folder_path), "输出——社交指数评分")
            os.makedirs(output_folder, exist_ok=True)

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
                self.process_file(file_path, output_folder)
                self.progress.emit((index + 1) * 100 // total_files)

            # 重新处理之前失败的ID
            self.retry_failed_ids()

            self.finished.emit()
        except Exception as e:
            self.result.emit(f"Error: {str(e)}")

    def stop(self):
        self._is_running = False

    def process_file(self, file_path, output_folder):
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

            # 获取当前时间
            current_time = datetime.now()
            # 创建班级信息JSON结构
            class_info = {
                "班级信息": {
                    "学校编号": school_id,
                    "年级": grade,
                    "班级": class_name,
                    "检测时间": current_time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "学生动态": {}
            }

            select_list = []  # 用于存储一个班级中每个学生的最低情感得分记录

            for index, row in data.iterrows():
                if not self._is_running:
                    return
                student_id = str(row['学号'])
                student_name = str(row['姓名'])  # 确保转换为字符串

                class_info["学生动态"][student_name] = []

                weibo_id = row['微博']
                if not pd.isna(weibo_id):
                    weibo_id = str(weibo_id)  # 确保转换为字符串
                    weibo_posts = self.retry_fetch_and_save(self.weibo, "微博", class_info, weibo_id, student_id, student_name)
                    class_info["学生动态"][student_name].extend(weibo_posts)

                qzone_id = row['qq空间']
                if not pd.isna(qzone_id):
                    qzone_id = str(qzone_id)  # 确保转换为字符串
                    qzone_posts = self.retry_fetch_and_save(self.qzone, 'qq空间', class_info, qzone_id, student_id, student_name)
                    class_info["学生动态"][student_name].extend(qzone_posts)

                # 保留最低情感得分的动态
                if class_info["学生动态"][student_name]:
                    min_score_post = min(class_info["学生动态"][student_name], key=lambda x: int(x.get("情感得分", "100")))
                    select_list.append({
                        "学号": student_id,
                        "姓名": student_name,
                        **min_score_post  # 包含post里的所有键
                    })
                else:
                    # 如果没有动态，保留学生信息，但不包含动态
                    select_list.append({
                        "学号": student_id,
                        "姓名": student_name
                    })

            # 为每个班级的学生保存 Excel
            if select_list:
                base_name = os.path.basename(file_path)
                class_filename = os.path.join(output_folder, f"{os.path.splitext(base_name)[0]}.xlsx")
                select_df = pd.DataFrame(select_list)

                # 添加“社交预警”列
                if '情感得分' in select_df.columns:
                    select_df['社交预警'] = select_df['情感得分'].apply(
                        lambda x: '紧急关注' if pd.notnull(x) and int(x) < 20 else ''
                    )
                else:
                    select_df['社交预警'] = ''

                sheet_name = f"社交原表"

                # 保存DataFrame到Excel
                select_df.to_excel(class_filename, index=False, sheet_name=sheet_name)
                self.result.emit(f"\n{file_path} 的每人最低分数据已保存到 {class_filename}")

                try:
                    # 打开已存在的Excel文件
                    wb = load_workbook(class_filename)
                    ws = wb.active

                    # 插入数据字典内容到Excel顶部
                    start_row = 1
                    for key, value in class_info["班级信息"].items():
                        ws.insert_rows(start_row)
                        ws.cell(row=start_row, column=1, value=key)
                        ws.cell(row=start_row, column=2, value=value)  # 直接将值写入第2列
                        start_row += 1

                    # 保存修改后的Excel文件
                    wb.save(class_filename)
                except Exception as e:
                    self.result.emit(f"\n保存表格失败")

                finally:
                    # 确保工作簿被关闭
                    wb.close()

            # 保存班级信息和header_dict到JSON文件，文件名为输入的Excel文件名
            json_filename = os.path.splitext(base_name)[0] + ".json"
            class_filename = os.path.join(output_folder, json_filename)
            class_info["header"] = header_dict  # 将header_dict信息也保存进去
            with open(class_filename, 'w', encoding='utf-8') as f:
                json.dump(class_info, f, ensure_ascii=False, indent=4, default=str)

            self.result.emit(f"\n{file_path} 的所有帖子已保存到 {class_filename}")
        except Exception as e:
            self.result.emit(f"Error processing file {file_path}: {str(e)}")

    def retry_fetch_and_save(self, scraper, platform, class_info, id, student_id, student_name):
        retry_count = 0
        success = False
        max_retries = 7
        posts = []
        while retry_count < max_retries and not success:
            try:
                posts = scraper.fetch_messages(id)
                if not posts:
                    raise ValueError("No messages to save.")
                self.result.emit(f"\n已保存学生 {student_name}(ID: {id}) 的{platform}动态")
                success = True
            except TooManyRequestsError as e:
                self.result.emit(f"\n⚠获取学生 {student_name} ID {id} 的{platform}数据时出错: {str(e)}。将稍后重试。")
                self.add_to_retry_later(platform, id, student_id, student_name)
                break
            except Exception as e:
                if str(e) == "No messages to save.":
                    self.result.emit(f"\n⚠学生 {student_name} ID {id} 的{platform}没有动态可保存，跳过此学生。")
                    break  # 跳过，不重试
                retry_count += 1
                if retry_count < max_retries:
                    if platform == '微博':
                        delay = random.uniform(1 * 60, 3 * 60)  # 微博随机延迟3到5分钟
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

    def add_to_retry_later(self, platform, id, student_id, student_name):
        if platform not in self.retry_later:
            self.retry_later[platform] = []
        self.retry_later[platform].append({
            'id': id,
            'student_id': student_id,
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
                posts = self.retry_fetch_and_save(scraper, platform, task['id'], task['student_id'], task['student_name'])

                if posts:  # 如果重试成功获取到动态
                    if task['student_name'] not in retry_results:
                        retry_results[task['student_name']] = []
                    retry_results[task['student_name']].extend(posts)

        # 将重试成功的结果保存到一个单独的文件中
        if retry_results:
            retry_results_filename = os.path.join(self.folder_path, "retry_results.json")
            with open(retry_results_filename, 'w', encoding='utf-8') as f:
                json.dump(retry_results, f, ensure_ascii=False, indent=4)
            self.result.emit(f"\n重试成功的任务结果已保存到 {retry_results_filename}")
        else:
            self.result.emit("\n重试后没有成功获取到任何任务的动态。")

        self.result.emit("\n所有失败的任务已重新处理。")