import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QEvent

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        layout = QVBoxLayout()
        layout.addWidget(QLabel('Click outside me (Tool)'))
        self.setLayout(layout)
        self.resize(300, 200)

    def changeEvent(self, e):
        print("changeEvent:", e.type())
        if e.type() == QEvent.ActivationChange and not self.isActiveWindow():
            print('Lost focus via ActivationChange!')
        super().changeEvent(e)

app = QApplication(sys.argv)
w = TestWindow()
w.show()
sys.exit(app.exec_())
