import sys
from PyQt6.QtWidgets import QApplication
from scr.window import MainWindow

app = QApplication(sys.argv)
window = MainWindow()
window.show()

# 从外部文件加载 QSS 样式
try:
    with open('styles.qss', 'r', encoding='utf-8') as f:
        qss = f.read()
    app.setStyleSheet(qss)
except FileNotFoundError:
    print("样式文件 'styles.qss' 未找到。请确保它与 run.py 位于同一目录下。")
sys.exit(app.exec())

