import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.resize(300, 200)

app = QApplication(sys.argv)
w = TestWindow()
w.show()
w.setWindowState(w.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
w.activateWindow()
w.raise_()

def on_focus_changed(old, new):
    print(f"Focus changed: {old} -> {new}")
    if new is None:
        print("Closing!")
        w.close()

app.focusChanged.connect(on_focus_changed)
sys.exit(app.exec_())
