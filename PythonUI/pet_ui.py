import sys
import os
import random
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter

class JinxPet(QWidget):
    def __init__(self):
        super().__init__()
        self.pet_width = 250
        self.pet_height = 300
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.current_pixmap = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.resize(self.pet_width, self.pet_height)

        self.expressions = [
            os.path.join(self.base_dir, "expressions/jinxsmirkleft.png"),
            os.path.join(self.base_dir, "expressions/jinxsmirkright.png"),
            os.path.join(self.base_dir, "expressions/jinxsmirkstraight.png"),
            os.path.join(self.base_dir, "expressions/jinxsmirkclosed.png"),
            os.path.join(self.base_dir, "expressions/jinxpoutclosed.png"),
            os.path.join(self.base_dir, "expressions/jinxpoutright.png"),
            os.path.join(self.base_dir, "expressions/jinxpoutleft.png"),
            os.path.join(self.base_dir, "expressions/jinxpoutstraight.png")
        ]
        self.reactions = [
            os.path.join(self.base_dir, "expressions/jinxdragged.png")
        ]

        self.update_image(self.expressions[2])
        self.move_to_bottom_right()
        self.old_pos = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.change_expression)
        self.timer.start(2000)

    def move_to_bottom_right(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(20, screen.height() - self.pet_height - 20)

    def update_image(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            print(f"Error: Could not load image at {path}", file=sys.stderr)
            return
        self.current_pixmap = pixmap.scaled(
            self.pet_width,
            self.pet_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.update()  # Trigger paintEvent

    def paintEvent(self, event):
        if self.current_pixmap is None:
            return
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)  # Clear to fully transparent
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        # Center the pixmap
        x = (self.width() - self.current_pixmap.width()) // 2
        y = (self.height() - self.current_pixmap.height()) // 2
        painter.drawPixmap(x, y, self.current_pixmap)
        painter.end()

    def change_expression(self):
        if self.old_pos is None:
            self.update_image(random.choice(self.expressions))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            current_pos = event.globalPosition().toPoint()
            delta = current_pos - self.old_pos
            if delta.manhattanLength() > 1:
                self.move(self.pos() + delta)
                self.update_image(self.reactions[0])
                self.old_pos = current_pos

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = None
            self.change_expression()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = JinxPet()
    pet.show()
    sys.exit(app.exec())