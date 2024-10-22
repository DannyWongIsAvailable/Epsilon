# window.py
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, QWidget, \
    QTextEdit, QMessageBox, QProgressBar, QLabel, QLineEdit, QDialog, QFormLayout, QComboBox
from scr.task import Worker
from datetime import datetime
import sys
import os
import yaml


class SettingsDialog(QDialog):
    def __init__(self, config_path):
        super().__init__()
        self.setWindowTitle("设置")
        self.resize(400, 180)
        self.config_path = config_path
        self.layout = QFormLayout()

        # 加载配置文件
        with open(self.config_path, 'r', encoding='utf-8') as file:
            self.config = yaml.safe_load(file)

        # 设置根目录输入框
        self.root_directory_input = QLineEdit(self.config.get('root_directory', ''))
        self.root_directory_button = QPushButton("浏览")
        self.root_directory_button.clicked.connect(self.browse_root_directory)
        root_directory_layout = QHBoxLayout()
        root_directory_layout.addWidget(QLabel("设置根目录:"))  # 标签占1格
        root_directory_layout.addWidget(self.root_directory_input, 2)  # 输入框占2格
        root_directory_layout.addWidget(self.root_directory_button)  # 浏览按钮占1格
        self.layout.addRow(root_directory_layout)

        # 创建输入字段
        # 微博页数和微博抓取天数输入框放在同一行，每个标签和输入框分别占1格，共4列
        self.weibo_pages_input = QLineEdit(str(self.config.get('weibo_pages', '')))
        self.weibo_fetch_days_input = QLineEdit(str(self.config.get('weibo_fetch_days', '')))
        weibo_layout = QHBoxLayout()  # 创建一个水平布局，将页数和天数的标签和输入框放在同一行
        weibo_layout.addWidget(QLabel("微博抓取页数:"))  # 添加标签 "微博页数"
        weibo_layout.addWidget(self.weibo_pages_input)  # 添加页数输入框
        weibo_layout.addWidget(QLabel("微博抓取天数:"))  # 添加标签 "微博抓取天数"
        weibo_layout.addWidget(self.weibo_fetch_days_input)  # 添加抓取天数输入框
        self.layout.addRow(weibo_layout)  # 将水平布局添加到表单布局中

        # 微博Cookie输入框，Cookie输入框占3格
        self.weibo_cookie_input = QLineEdit(self.config.get('weibo_headers', {}).get('Cookie', ''))
        weibo_cookie_layout = QHBoxLayout()
        weibo_cookie_layout.addWidget(QLabel("微博Cookie:"))  # 标签占1格
        weibo_cookie_layout.addWidget(self.weibo_cookie_input, 3)  # 输入框占3格
        self.layout.addRow(weibo_cookie_layout)

        # QQ空间页数和QQ空间抓取天数输入框放在同一行，每个标签和输入框分别占1格，共4列
        self.qzone_pages_input = QLineEdit(str(self.config.get('qzone_pages', '')))
        self.qzone_fetch_days_input = QLineEdit(str(self.config.get('qzone_fetch_days', '')))
        qzone_layout = QHBoxLayout()  # 创建一个水平布局，将页数和天数的标签和输入框放在同一行
        qzone_layout.addWidget(QLabel("QQ空间抓取页数:"))  # 添加标签 "QQ空间页数"
        qzone_layout.addWidget(self.qzone_pages_input)  # 添加页数输入框
        qzone_layout.addWidget(QLabel("QQ空间抓取天数:"))  # 添加标签 "QQ空间抓取天数"
        qzone_layout.addWidget(self.qzone_fetch_days_input)  # 添加抓取天数输入框
        self.layout.addRow(qzone_layout)  # 将水平布局添加到表单布局中

        # QQ空间Cookie输入框，Cookie输入框占3格
        self.qzone_cookie_input = QLineEdit(self.config.get('qzone_headers', {}).get('cookie', ''))
        qzone_cookie_layout = QHBoxLayout()
        qzone_cookie_layout.addWidget(QLabel("QQ空间Cookie:"))  # 标签占1格
        qzone_cookie_layout.addWidget(self.qzone_cookie_input, 3)  # 输入框占3格
        self.layout.addRow(qzone_cookie_layout)

        # 添加保存和取消按钮
        self.save_button = QPushButton("保存")
        self.cancel_button = QPushButton("取消")
        self.save_button.clicked.connect(self.save_settings)
        self.cancel_button.clicked.connect(self.reject)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        self.layout.addRow(button_layout)

        self.setLayout(self.layout)

    def browse_root_directory(self):
        # 浏览文件夹以设置根目录
        file_dialog = QFileDialog()
        selected_folder = file_dialog.getExistingDirectory(self, "选择根目录", "")
        if selected_folder:
            self.root_directory_input.setText(selected_folder)

    def save_settings(self):
        # 更新配置数据
        self.config['root_directory'] = self.root_directory_input.text()
        self.config['weibo_pages'] = int(self.weibo_pages_input.text())
        self.config['weibo_fetch_days'] = int(self.weibo_fetch_days_input.text())
        self.config['weibo_headers'] = self.config.get('weibo_headers', {})
        self.config['weibo_headers']['Cookie'] = self.weibo_cookie_input.text()
        self.config['qzone_pages'] = int(self.qzone_pages_input.text())
        self.config['qzone_fetch_days'] = int(self.qzone_fetch_days_input.text())
        self.config['qzone_headers'] = self.config.get('qzone_headers', {})
        self.config['qzone_headers']['cookie'] = self.qzone_cookie_input.text()

        # 保存到配置文件
        try:
            with open(self.config_path, 'w', encoding='utf-8') as file:
                yaml.safe_dump(self.config, file, allow_unicode=True)
            QMessageBox.information(self, "成功", "设置已保存！")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法保存配置文件: {str(e)}")


class DirectorySelectionDialog(QDialog):
    def __init__(self, root_directory):
        super().__init__()
        self.setWindowTitle("选择数据所在目录")
        self.resize(400, 200)
        self.layout = QVBoxLayout()
        self.root_directory = root_directory

        # 创建下拉选择器用于选择目录
        self.combo_boxes = []
        initial_dirs = self.get_subdirectories(self.root_directory)
        self.add_combo_box(initial_dirs)

        # 确定和取消按钮
        self.confirm_button = QPushButton("开始获取")
        self.cancel_button = QPushButton("取消")
        self.confirm_button.clicked.connect(self.confirm_selection)
        self.cancel_button.clicked.connect(self.reject)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.confirm_button)
        button_layout.addWidget(self.cancel_button)

        self.layout.addLayout(button_layout)
        self.setLayout(self.layout)

    def add_combo_box(self, items):
        combo_box = QComboBox()
        combo_box.addItems(["选择目录"] + items)
        combo_box.currentIndexChanged.connect(self.update_combo_boxes)
        self.layout.insertWidget(len(self.combo_boxes), combo_box)
        self.combo_boxes.append(combo_box)

        # 默认选择特定子目录
        if "每日分析区" in items:
            combo_box.setCurrentText("每日分析区")
        elif "社交平台分析区" in items:
            combo_box.setCurrentText("社交平台分析区")
        elif "输入——账号excel表" in items:
            combo_box.setCurrentText("输入——账号excel表")

    def get_subdirectories(self, path):
        return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]

    def update_combo_boxes(self):
        # 获取上级目录的选定状态，如果改变，需要重新选择子目录
        sender = self.sender()
        sender_index = self.combo_boxes.index(sender)
        if sender.currentIndex() == 0:
            # 如果上级目录改为"选择目录"，移除所有下级选择框
            while len(self.combo_boxes) > sender_index + 1:
                combo_box = self.combo_boxes.pop()
                self.layout.removeWidget(combo_box)
                combo_box.deleteLater()
            return

        # 如果上级目录发生变化，移除后面的所有选择框
        while len(self.combo_boxes) > sender_index + 1:
            combo_box = self.combo_boxes.pop()
            self.layout.removeWidget(combo_box)
            combo_box.deleteLater()

        # 获取最新的选定路径
        selected_path = self.root_directory
        for combo_box in self.combo_boxes:
            if combo_box.currentIndex() > 0:
                selected_path = os.path.join(selected_path, combo_box.currentText())

        # 添加新的下拉框来选择下级目录
        subdirectories = self.get_subdirectories(selected_path)
        if subdirectories:
            self.add_combo_box(subdirectories)

    def confirm_selection(self):
        # 确认选择的目录路径
        selected_path = self.root_directory
        for combo_box in self.combo_boxes:
            if combo_box.currentIndex() > 0:
                selected_path = os.path.join(selected_path, combo_box.currentText())
        self.selected_path = selected_path
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("动态内容爬取")
        self.resize(800, 600)

        self.layout = QVBoxLayout()

        self.get_data_button = QPushButton("获取数据")
        self.get_data_button.setFixedSize(150, 40)
        self.get_data_button.clicked.connect(self.toggle_get_data)

        self.view_results_button = QPushButton("查看分析结果")
        self.view_results_button.setFixedSize(150, 40)
        self.view_results_button.clicked.connect(self.view_analysis_results)

        self.settings_button = QPushButton("设置")
        self.settings_button.setFixedSize(150, 40)
        self.settings_button.clicked.connect(self.open_settings)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.get_data_button)
        button_layout.addWidget(self.view_results_button)
        button_layout.addWidget(self.settings_button)
        button_layout.addStretch()
        self.layout.addLayout(button_layout)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.layout.addWidget(self.result_text)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.layout.addWidget(self.progress_bar)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        self.save_folder_path = None
        self.worker = None
        self.start_time = None

    def open_directory_selection(self):
        config_file_path = os.path.join(os.getcwd(), 'config.yaml')
        if os.path.exists(config_file_path):
            with open(config_file_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            root_directory = config.get('root_directory', '')
            if root_directory:
                dialog = DirectorySelectionDialog(root_directory)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self.save_folder_path = dialog.selected_path
                    # 在主窗口的 result_text 中打印"爬虫初始化中，请稍候……"
                    self.result_text.append("爬虫初始化中，请稍候……")
                    self.start_get_data()
            else:
                self.show_error_message("请先在设置中配置根目录。")
        else:
            self.show_error_message("未找到配置文件 config.yaml")

    def toggle_get_data(self):
        if self.get_data_button.text() == "获取数据":
            self.open_directory_selection()
        else:
            self.stop_get_data()

    def start_get_data(self):
        if not self.save_folder_path:
            self.show_error_message("请先选择数据所在目录")
            return

        self.progress_bar.setVisible(True)
        self.get_data_button.setText("停止")

        self.worker = Worker(self.save_folder_path)
        self.worker.progress.connect(self.update_progress)
        self.worker.result.connect(self.update_result_text)
        self.worker.finished.connect(self.process_finished)
        self.worker.stopped.connect(self.process_stopped)  # 连接用户手动停止信号
        self.start_time = datetime.now()
        self.worker.start()

    def stop_get_data(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.get_data_button.setText("获取数据")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_result_text(self, text):
        self.result_text.append(text)

    def process_finished(self):
        self.progress_bar.setVisible(False)
        self.get_data_button.setText("获取数据")
        elapsed_time = datetime.now() - self.start_time

        total_seconds = elapsed_time.total_seconds()
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            elapsed_str = f"{int(hours)}小时{int(minutes)}分钟{int(seconds)}秒"
        else:
            elapsed_str = f"{int(minutes)}分钟{int(seconds)}秒"

        self.result_text.append(f"\nCompleted! 耗时: {elapsed_str}")

    def process_stopped(self):
        self.progress_bar.setVisible(False)
        self.get_data_button.setText("获取数据")
        self.result_text.append("\n用户手动终止了任务。")

    def show_error_message(self, message):
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Icon.Critical)
        error_dialog.setWindowTitle("错误")
        error_dialog.setText(message)
        error_dialog.exec()

    def open_settings(self):
        config_file_path = os.path.join(os.getcwd(), 'config.yaml')
        if os.path.exists(config_file_path):
            settings_dialog = SettingsDialog(config_file_path)
            settings_dialog.exec()
        else:
            self.show_error_message("未找到配置文件 config.yaml")

    def view_analysis_results(self):
        if self.save_folder_path:
            # 查找同级目录下名为 "输出——社交指数评分" 的目录
            results_folder = os.path.join(os.path.dirname(self.save_folder_path),"..", "今日整合分析")
            if os.path.exists(results_folder):
                # 打开目录使用文件系统默认查看器
                os.startfile(results_folder)
            else:
                self.show_error_message("分析结果目录不存在。")
        else:
            self.show_error_message("请先获取数据，然后再查看分析结果。")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
