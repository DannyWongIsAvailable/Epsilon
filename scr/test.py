import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QWidget, QTextEdit, QMessageBox
from datetime import datetime
from wechat import WeChatPyQReader  # 确保你已经正确引入WeChatPyQReader类

class WeChatReaderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("获取朋友圈动态")
        self.resize(600, 400)

        self.layout = QVBoxLayout()

        self.save_button = QPushButton("选择保存位置")
        self.save_button.setFixedSize(200, 50)
        self.save_button.clicked.connect(self.select_save_folder)
        self.layout.addWidget(self.save_button)

        self.get_wechat_button = QPushButton("获取朋友圈动态")
        self.get_wechat_button.setFixedSize(200, 50)
        self.get_wechat_button.clicked.connect(self.get_wechat_data)
        self.layout.addWidget(self.get_wechat_button)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.layout.addWidget(self.result_text)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        self.save_folder_path = None

    def select_save_folder(self):
        file_dialog = QFileDialog()
        selected_folder = file_dialog.getExistingDirectory(self, "选择保存位置", "")
        if selected_folder:
            self.save_folder_path = selected_folder
            self.result_text.append(f"选择的保存位置: {self.save_folder_path}")
        else:
            self.result_text.append("未选择保存位置")

    def get_wechat_data(self):
        if not self.save_folder_path:
            self.show_error_message("请先选择保存位置")
            return

        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        root_folder_path = os.path.join(self.save_folder_path, f"WeChat_{current_time}")
        os.makedirs(root_folder_path, exist_ok=True)

        wechat = WeChatPyQReader()
        try:
            self.result_text.append("正在获取朋友圈动态...")
            df = wechat.get_pyq_data()
            path = os.path.join(root_folder_path, "wechat_data.xlsx")
            wechat.save_to_excel(df, path)
            self.result_text.append(f"朋友圈动态已保存到: {path}")
        except Exception as e:
            self.show_error_message(f"获取朋友圈动态时出错: {str(e)}")
            self.result_text.append(f"获取朋友圈动态时出错: {str(e)}")

    def show_error_message(self, message):
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Icon.Critical)
        error_dialog.setWindowTitle("错误")
        error_dialog.setText(message)
        error_dialog.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WeChatReaderWindow()
    window.show()
    sys.exit(app.exec())
