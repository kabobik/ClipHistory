import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.resize(300, 200)
    
    def hideEvent(self, e):
        print("hideEvent called!")
        self.close()
        super().hideEvent(e)

app = QApplication(sys.argv)
w = TestWindow()
w.show()
w.activateWindow()
w.raise_()

sys.exit(app.exec_())
