import sys
from PyQt5.QtWidgets import QApplication, QWidget

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(300, 200)

app = QApplication(sys.argv)
w = TestWindow()
w.show()
w.raise_()
w.activateWindow()

def on_focus(old, new):
    print("focusChanged:", old, "->", new)

app.focusChanged.connect(on_focus)
sys.exit(app.exec_())
