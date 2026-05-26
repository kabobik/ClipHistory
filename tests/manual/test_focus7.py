import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.resize(300, 200)

app = QApplication(sys.argv)
w = TestWindow()
w.show()

def check():
    print("activeWindow:", QApplication.activeWindow())

t = QTimer()
t.timeout.connect(check)
t.start(500)

sys.exit(app.exec_())
