import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, QWidget, \
    QTextEdit, QMessageBox, QProgressBar
from scr.task import Worker
from datetime import datetime


# 定义主窗口类
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("动态内容爬取")
        self.resize(800, 600)

        self.layout = QVBoxLayout()
        # 上传文件夹按钮
        self.upload_button = QPushButton("上传文件夹")
        self.upload_button.setFixedSize(150, 40)
        self.upload_button.clicked.connect(self.upload_folder)
        # 选择保存位置按钮
        self.save_button = QPushButton("选择保存位置")
        self.save_button.setFixedSize(150, 40)
        self.save_button.clicked.connect(self.select_save_folder)
        # 获取数据按钮
        self.get_data_button = QPushButton("获取数据")
        self.get_data_button.setFixedSize(150, 40)
        self.get_data_button.clicked.connect(self.toggle_get_data)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.upload_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.get_data_button)
        button_layout.addStretch()
        self.layout.addLayout(button_layout)

        # 用于显示结果的文本框
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.layout.addWidget(self.result_text)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # 初始化时隐藏进度条
        self.layout.addWidget(self.progress_bar)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        self.folder_path = None
        self.save_folder_path = None
        self.worker = None
        self.start_time = None  # 新增用于记录开始时间

    # 上传文件夹的函数
    def upload_folder(self):
        file_dialog = QFileDialog()
        self.folder_path = file_dialog.getExistingDirectory(self, "选择文件夹", "")
        if self.folder_path:
            self.result_text.append(f"选择的文件夹: {self.folder_path}")

    # 选择保存位置的函数
    def select_save_folder(self):
        file_dialog = QFileDialog()
        self.save_folder_path = file_dialog.getExistingDirectory(self, "选择保存位置", "")
        if self.save_folder_path:
            self.result_text.append(f"选择的保存位置: {self.save_folder_path}")

    # 获取数据和停止获取数据的切换函数
    def toggle_get_data(self):
        if self.get_data_button.text() == "获取数据":
            self.start_get_data()
        else:
            self.stop_get_data()

    # 开始获取数据的函数
    def start_get_data(self):
        if not self.folder_path:
            self.show_error_message("请先选择文件夹")
            return

        if not self.save_folder_path:
            self.show_error_message("请先选择保存位置")
            return

        self.progress_bar.setVisible(True)  # 开始处理前显示进度条
        self.get_data_button.setText("停止")  # 按钮文本变为“停止”

        self.worker = Worker(self.folder_path, self.save_folder_path)
        self.worker.progress.connect(self.update_progress)
        self.worker.result.connect(self.update_result_text)
        self.worker.finished.connect(self.process_finished)
        self.start_time = datetime.now()  # 记录开始时间
        self.worker.start()

    # 停止获取数据的函数
    def stop_get_data(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
            self.get_data_button.setText("获取数据")  # 按钮文本变回“获取数据”

    # 更新进度条的函数
    def update_progress(self, value):
        self.progress_bar.setValue(value)

    # 更新结果文本框的函数
    def update_result_text(self, text):
        self.result_text.append(text)

    # 处理完成时的函数
    def process_finished(self):
        self.progress_bar.setVisible(False)
        self.get_data_button.setText("获取数据")  # 处理完成后按钮文本变回“获取数据”
        elapsed_time = datetime.now() - self.start_time  # 计算耗时

        total_seconds = elapsed_time.total_seconds()
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            elapsed_str = f"{int(hours)}小时{int(minutes)}分钟{int(seconds)}秒"
        else:
            elapsed_str = f"{int(minutes)}分钟{int(seconds)}秒"

        self.result_text.append(f"\nCompleted! 耗时: {elapsed_str}")  # 输出耗时

    # 显示错误信息的函数
    def show_error_message(self, message):
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Icon.Critical)
        error_dialog.setWindowTitle("错误")
        error_dialog.setText(message)
        error_dialog.exec()


# 主程序入口
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
