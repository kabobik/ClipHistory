import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.resize(300, 200)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check)
        self.timer.start(200)

    def check(self):
        if not self.isActiveWindow():
            print("Not active!")
            self.close()

app = QApplication(sys.argv)
w = TestWindow()
w.show()
w.activateWindow()
w.raise_()

sys.exit(app.exec_())
