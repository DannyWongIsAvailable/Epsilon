from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, QWidget, \
    QTextEdit, QMessageBox, QProgressBar
from scr.task import Worker
from datetime import datetime
import sys


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("动态内容爬取")
        self.resize(800, 600)

        self.layout = QVBoxLayout()
        self.upload_button = QPushButton("上传文件夹")
        self.upload_button.setFixedSize(150, 40)
        self.upload_button.clicked.connect(self.upload_folder)

        self.save_button = QPushButton("选择保存位置")
        self.save_button.setFixedSize(150, 40)
        self.save_button.clicked.connect(self.select_save_folder)

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

        self.folder_path = None
        self.save_folder_path = None
        self.worker = None
        self.start_time = None

    def upload_folder(self):
        file_dialog = QFileDialog()
        selected_folder = file_dialog.getExistingDirectory(self, "选择文件夹", "")
        if selected_folder:
            self.folder_path = selected_folder
            self.result_text.append(f"选择的文件夹: {self.folder_path}")
        else:
            self.result_text.append("未选择文件夹")

    def select_save_folder(self):
        file_dialog = QFileDialog()
        selected_folder = file_dialog.getExistingDirectory(self, "选择保存位置", "")
        if selected_folder:
            self.save_folder_path = selected_folder
            self.result_text.append(f"选择的保存位置: {self.save_folder_path}")
        else:
            self.result_text.append("未选择保存位置")

    def toggle_get_data(self):
        if self.get_data_button.text() == "获取数据":
            self.start_get_data()
        else:
            self.stop_get_data()

    def start_get_data(self):
        if not self.folder_path:
            self.show_error_message("请先选择文件夹")
            return

        if not self.save_folder_path:
            self.show_error_message("请先选择保存位置")
            return

        self.progress_bar.setVisible(True)
        self.get_data_button.setText("停止")

        self.worker = Worker(self.folder_path, self.save_folder_path)
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
