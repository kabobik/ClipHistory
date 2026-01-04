#!/usr/bin/env python3
"""
ClipHistory Qt UI - современный дизайн как в Windows
"""

from PyQt5.QtWidgets import (QApplication, QWidget, QListWidget, QListWidgetItem,
                             QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, 
                             QFileDialog, QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QByteArray, QTimer
from PyQt5.QtGui import QPixmap, QIcon, QPalette, QColor, QFont, QPainter
from PyQt5.QtSvg import QSvgRenderer

import subprocess
import sqlite3
import json
import sys
import os
import shutil
from pathlib import Path
from PIL import Image

class ClipboardItemWidget(QFrame):
    """Виджет для отдельного элемента истории"""
    
    def __init__(self, item_id, mime_type, content_path, preview, is_dark, pinned, parent_window=None):
        super().__init__()
        self.item_id = item_id
        self.mime_type = mime_type
        self.content_path = content_path
        self.preview = preview
        self.is_dark = is_dark
        self.pinned = pinned
        self.parent_window = parent_window
        
        self.setFrameStyle(QFrame.NoFrame)
        self.setFixedHeight(240)
        self.setCursor(Qt.PointingHandCursor)
        
        # Фиксируем только высоту, ширина адаптивная
        from PyQt5.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)
        
        self.setup_ui(layout)
    
    def create_svg_icon(self, svg_path, color, size=48):
        """Создать иконку из SVG"""
        # SVG иконки Material Design Icons
        svg_icons = {
            'trash': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M9,3V4H4V6H5V19A2,2 0 0,0 7,21H17A2,2 0 0,0 19,19V6H20V4H15V3H9M7,6H17V19H7V6M9,8V17H11V8H9M13,8V17H15V8H13Z" /></svg>''',
            'pin': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M16,12V4H17V2H7V4H8V12L6,14V16H11.2V22H12.8V16H18V14L16,12Z" /></svg>''',
            'pin-off': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M2,5.27L3.28,4L20,20.72L18.73,22L12.8,16.07V22H11.2V16H6V14L8,12V11.27L2,5.27M16,12L18,14V16H17.82L8,6.18V4H7V2H17V4H16V12Z" /></svg>''',
            'download': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z" /></svg>''',
            'clipboard': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M19 3H14.82C14.4 1.84 13.3 1 12 1S9.6 1.84 9.18 3H5C3.9 3 3 3.9 3 5V19C3 20.1 3.9 21 5 21H19C20.1 21 21 20.1 21 19V5C21 3.9 20.1 3 19 3M12 3C12.55 3 13 3.45 13 4S12.55 5 12 5 11 4.55 11 4 11.45 3 12 3M7 7H17V5H19V19H5V5H7V7M7 9V11H17V9H7M7 13V15H17V13H7Z" /></svg>''',
            'close': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z" /></svg>'''
        }
        
        svg_data = svg_icons.get(svg_path, '').format(color=color)
        
        # Создаем QPixmap из SVG
        renderer = QSvgRenderer(QByteArray(svg_data.encode()))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        return pixmap
    
    def create_thumbnail(self, image_path, max_height):
        """Создать миниатюру изображения с учетом пропорций"""
        try:
            pixmap = QPixmap(str(image_path))
            if pixmap.isNull():
                return None
            
            # Масштабируем по высоте, ширина по пропорциям
            # Но не больше 800px по ширине
            max_width = 800
            if pixmap.height() > max_height or pixmap.width() > max_width:
                if pixmap.width() / pixmap.height() > max_width / max_height:
                    # Ограничиваем по ширине
                    return pixmap.scaledToWidth(max_width, Qt.SmoothTransformation)
                else:
                    # Ограничиваем по высоте
                    return pixmap.scaledToHeight(max_height, Qt.SmoothTransformation)
            return pixmap
        except Exception:
            return None
    
    def setup_ui(self, layout):
        """Настройка UI элемента"""
        mime_type = self.mime_type
        content_path = self.content_path
        preview = self.preview
        is_dark = self.is_dark
        
        # Для изображений - большое превью на всю ширину
        if mime_type.startswith('image/') and content_path:
            icon_label = QLabel()
            icon_label.setScaledContents(False)
            icon_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            icon_label.setStyleSheet(f"""
                background-color: {'#3a3a3a' if is_dark else '#f0f0f0'};
                border-radius: 8px;
            """)
            
            # Большая миниатюра с учетом пропорций
            pixmap = self.create_thumbnail(content_path, 220)
            if pixmap:
                icon_label.setPixmap(pixmap)
                # Устанавливаем размер по пропорциям изображения
                if pixmap.width() > pixmap.height():
                    # Широкое - на всю ширину
                    icon_label.setFixedSize(min(pixmap.width(), 800), pixmap.height())
                else:
                    # Высокое или квадратное
                    icon_label.setFixedSize(pixmap.width(), pixmap.height())
            
            layout.addWidget(icon_label)
            layout.addStretch()
        else:
            # Для текста - просто большой текст без иконки
            if mime_type.startswith('text/plain'):
                # Текст большим шрифтом
                preview_label = QLabel(preview)
                preview_label.setWordWrap(True)
                preview_label.setMaximumHeight(220)
                preview_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
                preview_label.setStyleSheet(f"""
                    color: {'#e0e0e0' if is_dark else '#333333'};
                    font-size: 32px;
                    font-weight: 300;
                    padding: 10px;
                """)
                layout.addWidget(preview_label)
            else:
                # Для других типов - иконка + текст
                icon_label = QLabel()
                icon_label.setFixedSize(80, 80)
                icon_label.setScaledContents(True)
                icon_label.setStyleSheet(f"""
                    background-color: {'#3a3a3a' if is_dark else '#f0f0f0'};
                    border-radius: 8px;
                """)
                
                # Иконка по типу
                icon_name = '🌐' if mime_type.startswith('text/html') else '📁' if mime_type.startswith('text/uri-list') else '❓'
                
                icon_label.setText(icon_name)
                icon_label.setAlignment(Qt.AlignCenter)
                icon_label.setFont(QFont('Sans', 42))
                
                layout.addWidget(icon_label)
                
                # Текст (справа)
                text_container = QVBoxLayout()
                text_container.setSpacing(4)
                
                preview_label = QLabel(preview)
                preview_label.setWordWrap(True)
                preview_label.setMaximumHeight(200)
                preview_label.setStyleSheet(f"""
                    color: {'#e0e0e0' if is_dark else '#333333'};
                    font-size: 16px;
                """)
                text_container.addWidget(preview_label)
                
                # Тип для неизвестных
                type_label = QLabel(mime_type)
                type_label.setStyleSheet(f"""
                    color: {'#888888' if is_dark else '#666666'};
                    font-size: 12px;
                """)
                text_container.addWidget(type_label)
                text_container.addStretch()
                
                layout.addLayout(text_container, 1)
        
        # Кнопки справа (удалить, закрепить, скачать)
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(8)
        buttons_layout.setAlignment(Qt.AlignTop)
        
        # Кнопка удаления
        delete_btn = QLabel()
        icon_color = '#e0e0e0' if is_dark else '#333333'
        delete_icon = self.create_svg_icon('trash', icon_color, 40)
        delete_btn.setPixmap(delete_icon)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setFixedSize(56, 56)
        delete_btn.setAlignment(Qt.AlignCenter)
        delete_btn.setFocusPolicy(Qt.NoFocus)
        def on_delete(e):
            if e.button() == Qt.LeftButton:
                e.accept()
                self.delete_item()
        delete_btn.mousePressEvent = on_delete
        buttons_layout.addWidget(delete_btn)
        
        # Кнопка закрепления (по умолчанию не закреплено)
        pin_btn = QLabel()
        pin_icon_name = 'pin' if self.pinned else 'pin-off'
        pin_icon = self.create_svg_icon(pin_icon_name, icon_color, 40)
        pin_btn.setPixmap(pin_icon)
        pin_btn.setCursor(Qt.PointingHandCursor)
        pin_btn.setFixedSize(56, 56)
        pin_btn.setAlignment(Qt.AlignCenter)
        pin_btn.setFocusPolicy(Qt.NoFocus)
        def on_pin(e):
            if e.button() == Qt.LeftButton:
                e.accept()
                self.toggle_pin()
        pin_btn.mousePressEvent = on_pin
        buttons_layout.addWidget(pin_btn)
        self.pin_btn = pin_btn  # Сохраняем ссылку для обновления иконки
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        
        # Стиль карточки - фиксированный, без изменений
        if self.is_dark:
            bg = '#2b2b2b'
            border = '#3a3a3a'
        else:
            bg = '#ffffff'
            border = '#e0e0e0'
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
        """)
        """Создать миниатюру изображения с учетом пропорций"""
        try:
            pixmap = QPixmap(str(image_path))
            if pixmap.isNull():
                return None
            
            # Масштабируем по высоте, ширина по пропорциям
            # Но не больше 800px по ширине
            max_width = 800
            if pixmap.height() > max_height or pixmap.width() > max_width:
                if pixmap.width() / pixmap.height() > max_width / max_height:
                    # Ограничиваем по ширине
                    return pixmap.scaledToWidth(max_width, Qt.SmoothTransformation)
                else:
                    # Ограничиваем по высоте
                    return pixmap.scaledToHeight(max_height, Qt.SmoothTransformation)
            return pixmap
        except Exception:
            return None
    
    def delete_item(self):
        """Удалить элемент из истории"""
        # Передаем сигнал родительскому окну
        if self.parent_window and hasattr(self.parent_window, 'delete_item_from_db'):
            self.parent_window.delete_item_from_db(self.item_id)
    
    def save_item(self):
        """Сохранить элемент в файл"""
        if self.parent_window and hasattr(self.parent_window, 'save_item_to_file'):
            self.parent_window.save_item_to_file(self.item_id, self.mime_type, self.content_path, self.preview)
    
    def toggle_pin(self):
        """Закрепить/открепить элемент"""
        if self.parent_window and hasattr(self.parent_window, 'toggle_pin_item'):
            self.parent_window.toggle_pin_item(self.item_id, self.pinned)


class ClipHistoryWindow(QWidget):
    """Главное окно истории"""
    
    def __init__(self):
        super().__init__()
        
        # Проверка единственного экземпляра
        self.lock_file = Path.home() / '.cache' / 'cliphistory' / '.ui.lock'
        if not self.acquire_lock():
            print("UI уже запущен")
            sys.exit(0)
        
        self.cache_dir = Path.home() / '.cache' / 'cliphistory'
        self.db_path = self.cache_dir / 'history.db'
        self.config = self.load_config()
        self.is_dark = self.is_dark_theme()
        self.drag_position = None
        self.prev_window_id = None
        
        # Константы размеров
        self.scale = self.config.get('ui_scale', 1.0)
        self.scrollbar_width = int(28 * self.scale)
        self.content_width = int(595 * self.scale)  # Ширина контента
        self.window_width = self.content_width + self.scrollbar_width  # Общая ширина окна
        self.window_height = int(700 * self.scale)
        
        self.init_ui()
        self.load_history()
        self.position_near_cursor()
        self.setup_auto_refresh()
    
    def acquire_lock(self):
        """Проверка что UI не запущен"""
        try:
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            if self.lock_file.exists():
                # Проверяем что процесс с PID из файла существует
                try:
                    with open(self.lock_file) as f:
                        pid = int(f.read().strip())
                    # Проверяем существование процесса
                    os.kill(pid, 0)
                    return False  # Процесс существует
                except (ProcessLookupError, ValueError):
                    # Процесс не существует, удаляем старый lock
                    self.lock_file.unlink()
            
            # Создаем lock файл с текущим PID
            with open(self.lock_file, 'w') as f:
                f.write(str(os.getpid()))
            return True
        except Exception:
            return True  # В случае ошибки разрешаем запуск
    
    def release_lock(self):
        """Освободить lock"""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
        except Exception:
            pass
    
    def load_config(self):
        """Загрузка конфигурации"""
        config_path = Path(__file__).parent / 'config.json'
        try:
            with open(config_path) as f:
                return json.load(f)
        except Exception:
            return {'auto_paste': True, 'ui_scale': 1.5}
    
    def is_dark_theme(self):
        """Определить тёмную тему"""
        try:
            result = subprocess.run(
                ['gsettings', 'get', 'org.cinnamon.theme', 'name'],
                capture_output=True, text=True, timeout=0.5
            )
            theme = result.stdout.strip().strip("'").lower()
            return 'dark' in theme or 'noir' in theme or 'black' in theme
        except Exception:
            return True
    
    def create_svg_icon(self, svg_path, size, color):
        """Создать иконку из SVG"""
        svg_icons = {
            'trash': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M9,3V4H4V6H5V19A2,2 0 0,0 7,21H17A2,2 0 0,0 19,19V6H20V4H15V3H9M7,6H17V19H7V6M9,8V17H11V8H9M13,8V17H15V8H13Z" /></svg>''',
            'pin': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M16,12V4H17V2H7V4H8V12L6,14V16H11.2V22H12.8V16H18V14L16,12Z" /></svg>''',
            'pin-off': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M2,5.27L3.28,4L20,20.72L18.73,22L12.8,16.07V22H11.2V16H6V14L8,12V11.27L2,5.27M16,12L18,14V16H17.82L8,6.18V4H7V2H17V4H16V12Z" /></svg>''',
            'download': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z" /></svg>''',
            'clipboard': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M19 3H14.82C14.4 1.84 13.3 1 12 1S9.6 1.84 9.18 3H5C3.9 3 3 3.9 3 5V19C3 20.1 3.9 21 5 21H19C20.1 21 21 20.1 21 19V5C21 3.9 20.1 3 19 3M12 3C12.55 3 13 3.45 13 4S12.55 5 12 5 11 4.55 11 4 11.45 3 12 3M7 7H17V5H19V19H5V5H7V7M7 9V11H17V9H7M7 13V15H17V13H7Z" /></svg>''',
            'close': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z" /></svg>'''
        }
        
        svg_data = svg_icons.get(svg_path, '').format(color=color)
        renderer = QSvgRenderer(QByteArray(svg_data.encode()))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap
    
    def setup_tray_icon(self):
        """Создать иконку в системном трее"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        
        # Создаем иконку для трея
        tray_icon_pixmap = self.create_svg_icon('clipboard', 64, '#ffffff' if self.is_dark else '#000000')
        
        self.tray_icon = QSystemTrayIcon(QIcon(tray_icon_pixmap), self)
        self.tray_icon.setToolTip('ClipHistory - История буфера обмена')
        
        # Создаем меню трея
        tray_menu = QMenu()
        
        show_action = QAction('Показать историю', self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction('Выход', self)
        quit_action.triggered.connect(self.close)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
    
    def on_tray_activated(self, reason):
        """Обработка клика по иконке в трее"""
        if reason == QSystemTrayIcon.Trigger:  # Левый клик
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.position_near_cursor()
    
    def setup_auto_refresh(self):
        """Настроить автообновление истории"""
        self.last_item_count = 0
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.check_for_updates)
        self.refresh_timer.start(1000)  # Проверка каждую секунду
    
    def check_for_updates(self):
        """Проверить новые элементы в истории"""
        if not self.isVisible():
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM items')
            current_count = cursor.fetchone()[0]
            conn.close()
            
            if self.last_item_count == 0:
                self.last_item_count = current_count
            elif current_count != self.last_item_count:
                # Есть новые элементы - обновляем список
                self.list_widget.setUpdatesEnabled(False)
                self.list_widget.clear()
                self.load_history()
                self.list_widget.setUpdatesEnabled(True)
                self.last_item_count = current_count
        except Exception:
            pass
    
    def init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle("История буфера обмена")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        
        # Используем переменные размеров из __init__
        self.setFixedSize(self.window_width, self.window_height)
        
        # Главный layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Заголовок
        header = QFrame()
        header.setFixedHeight(int(80 * self.scale))
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(int(20 * self.scale), 0, int(20 * self.scale), 0)
        header_layout.setSpacing(int(12 * self.scale))
        
        # Иконка приложения
        icon_color = '#ffffff' if self.is_dark else '#000000'
        app_icon = QLabel()
        app_icon.setPixmap(self.create_svg_icon('clipboard', int(48 * self.scale), icon_color))
        app_icon.setFixedSize(int(48 * self.scale), int(48 * self.scale))
        header_layout.addWidget(app_icon)
        
        title = QLabel("История буфера обмена")
        title.setFont(QFont('Sans', int(12 * self.scale), QFont.Bold))
        title.setAlignment(Qt.AlignVCenter)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Кнопка закрытия
        close_btn = QPushButton()
        close_btn.setFixedSize(int(48 * self.scale), int(48 * self.scale))
        close_btn.setIcon(QIcon(self.create_svg_icon('close', int(32 * self.scale), icon_color)))
        close_btn.setIconSize(QSize(int(32 * self.scale), int(32 * self.scale)))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        
        # Стиль кнопки
        if self.is_dark:
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 24px;
                }
                QPushButton:hover {
                    background-color: #555555;
                }
                QPushButton:pressed {
                    background-color: #666666;
                }
            """)
        else:
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 24px;
                }
                QPushButton:hover {
                    background-color: #dddddd;
                }
                QPushButton:pressed {
                    background-color: #bbbbbb;
                }
            """)
        
        header_layout.addWidget(close_btn)
        
        # Делаем заголовок перетаскиваемым
        self.header_widget = header
        
        if self.is_dark:
            header.setStyleSheet(f"""
                background-color: #333333;
                color: #ffffff;
                border-bottom: 1px solid #404040;
            """)
        else:
            header.setStyleSheet(f"""
                background-color: #f5f5f5;
                color: #000000;
                border-bottom: 1px solid #d0d0d0;
            """)
        
        main_layout.addWidget(header)
        
        # Список элементов
        self.list_widget = QListWidget()
        self.list_widget.setFrameStyle(QFrame.NoFrame)
        self.list_widget.setSpacing(int(4 * self.scale))
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        
        if self.is_dark:
            self.list_widget.setStyleSheet("""
                QListWidget {
                    background-color: #2b2b2b;
                    border: none;
                    padding: 0px;
                }
                QListWidget::item {
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }
                QListWidget::item:selected {
                    background-color: transparent;
                }
                QScrollBar:vertical {
                    border: none;
                    background: #2b2b2b;
                    width: 28px;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background: #555555;
                    border-radius: 0px;
                    min-height: 30px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #666666;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
            """)
        else:
            self.list_widget.setStyleSheet("""
                QListWidget {
                    background-color: #ffffff;
                    border: none;
                    padding: 0px;
                }
                QListWidget::item {
                    background-color: transparent;
                    border: none;
                    padding: 0;
                }
                QListWidget::item:selected {
                    background-color: transparent;
                }
                QScrollBar:vertical {
                    border: none;
                    background: #f5f5f5;
                    width: 28px;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background: #cccccc;
                    border-radius: 0px;
                    min-height: 30px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #aaaaaa;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
            """)
        
        main_layout.addWidget(self.list_widget)
        
        # Общий стиль окна
        if self.is_dark:
            self.setStyleSheet("""
                QWidget {
                    background-color: #2b2b2b;
                    color: #e0e0e0;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: #ffffff;
                    color: #333333;
                }
            """)
        
        # Тень окна (через стиль)
        self.setGraphicsEffect(None)  # Qt не поддерживает тени напрямую для frameless
    
    def position_near_cursor(self):
        """Позиционировать рядом с курсором с умной проверкой границ"""
        try:
            # Сохраняем ID активного окна для возврата фокуса
            result = subprocess.run(
                ['xdotool', 'getactivewindow'],
                capture_output=True, text=True, timeout=0.5
            )
            self.prev_window_id = result.stdout.strip()
            
            # Получаем размер экрана
            from PyQt5.QtWidgets import QDesktopWidget
            screen = QDesktopWidget().screenGeometry()
            screen_width = screen.width()
            screen_height = screen.height()
            
            # Получаем позицию курсора
            result = subprocess.run(
                ['xdotool', 'getmouselocation', '--shell'],
                capture_output=True, text=True, timeout=0.5
            )
            pos = {}
            for line in result.stdout.strip().split('\n'):
                if '=' in line:
                    key, val = line.split('=')
                    pos[key] = int(val)
            
            cursor_x, cursor_y = pos.get('X', screen_width // 2), pos.get('Y', screen_height // 2)
            
            margin = 20  # Отступ от края экрана и от курсора
            
            # Пробуем разместить справа-снизу от курсора (по умолчанию)
            x = cursor_x + margin
            y = cursor_y + margin
            
            # Проверяем правую границу - если не влезает, размещаем СЛЕВА
            if x + self.width() > screen_width - margin:
                x = cursor_x - self.width() - margin
            
            # Проверяем нижнюю границу - если не влезает, размещаем СВЕРХУ
            if y + self.height() > screen_height - margin:
                y = cursor_y - self.height() - margin
            
            # Если всё равно вылезает за границы (курсор в углу) - прижимаем к краям
            if x < margin:
                x = margin
            if y < margin:
                y = margin
            if x + self.width() > screen_width - margin:
                x = screen_width - self.width() - margin
            if y + self.height() > screen_height - margin:
                y = screen_height - self.height() - margin
            
            self.move(x, y)
        except Exception:
            self.prev_window_id = None
    
    def load_history(self):
        """Загрузить историю"""
        if not self.db_path.exists():
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, mime_type, content_path, preview, COALESCE(pinned, 0) as pinned
            FROM items 
            ORDER BY pinned DESC, timestamp DESC
            LIMIT 50
        ''')
        items = cursor.fetchall()
        conn.close()
        
        for item_id, mime_type, content_path, preview, pinned in items:
            widget = ClipboardItemWidget(item_id, mime_type, content_path, preview[:150], 
                                        self.is_dark, pinned, parent_window=self)
            # Устанавливаем максимальную ширину = ширина окна без скроллбара
            widget.setMaximumWidth(self.content_width)
            
            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(self.content_width, 240))
            item.setData(Qt.UserRole, (item_id, mime_type, content_path, preview))
            
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
    
    def on_item_clicked(self, item):
        """Обработка клика"""
        item_id, mime_type, content_path, preview = item.data(Qt.UserRole)
        self.restore_to_clipboard(mime_type, content_path, preview)
        
        if self.config.get('auto_paste', True):
            # Выполняем вставку до закрытия окна
            self.auto_paste()
        else:
            # Если авто-вставка отключена, просто закрываем
            self.close()
    
    def restore_to_clipboard(self, mime_type, content_path, preview):
        """Восстановить в clipboard"""
        if content_path:
            with open(content_path, 'rb') as f:
                content = f.read()
        else:
            content = preview.encode('utf-8')
        
        try:
            subprocess.run(
                ['xclip', '-selection', 'clipboard', '-t', mime_type],
                input=content, timeout=1.0, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass
    
    def auto_paste(self):
        """Автовставка"""
        try:
            import time
            # Скрываем окно сразу
            self.hide()
            time.sleep(0.05)
            
            # Возвращаем фокус на предыдущее окно
            if self.prev_window_id:
                subprocess.run(['xdotool', 'windowactivate', self.prev_window_id], 
                             timeout=0.5, stderr=subprocess.DEVNULL)
                time.sleep(0.15)  # Ждем активации окна
            
            # Вставляем
            subprocess.run(['xdotool', 'key', 'ctrl+v'], timeout=1.0, stderr=subprocess.DEVNULL)
            
            # Закрываем окно
            self.close()
        except Exception as e:
            print(f"Auto-paste error: {e}")
            self.close()
    
    def keyPressEvent(self, event):
        """Обработка клавиш"""
        if event.key() == Qt.Key_Escape:
            self.close()
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        self.release_lock()
        event.accept()
    
    def mousePressEvent(self, event):
        """Начало перетаскивания окна - только при клике на заголовок"""
        if event.button() == Qt.LeftButton:
            # Проверяем что клик был в области заголовка
            if hasattr(self, 'header_widget') and self.header_widget.geometry().contains(event.pos()):
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
            else:
                event.ignore()
    
    def mouseMoveEvent(self, event):
        """Перетаскивание окна"""
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Остановка перетаскивания"""
        if event.button() == Qt.LeftButton:
            self.drag_position = None
            event.accept()
    
    def delete_item_from_db(self, item_id):
        """Удалить элемент из базы и обновить UI"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем не закреплен ли элемент
            cursor.execute('SELECT pinned FROM items WHERE id = ?', (item_id,))
            row = cursor.fetchone()
            if row and row[0] == 1:
                print(f"Нельзя удалить закрепленный элемент {item_id}")
                conn.close()
                return
            
            # Удаляем файл если есть
            cursor.execute('SELECT content_path FROM items WHERE id = ?', (item_id,))
            row = cursor.fetchone()
            if row and row[0]:
                try:
                    Path(row[0]).unlink()
                except Exception:
                    pass
            
            # Удаляем из БД
            cursor.execute('DELETE FROM items WHERE id = ?', (item_id,))
            conn.commit()
            conn.close()
            
            # Обновляем список с отключением обновления
            self.list_widget.setUpdatesEnabled(False)
            self.list_widget.clear()
            self.load_history()
            self.list_widget.setUpdatesEnabled(True)
        except Exception as e:
            print(f"Delete error: {e}")
    
    def save_item_to_file(self, item_id, mime_type, content_path, preview):
        """Сохранить элемент в файл"""
        from PyQt5.QtWidgets import QFileDialog
        import shutil
        
        try:
            # Определяем расширение по MIME
            ext = ''
            if mime_type.startswith('image/png'):
                ext = '.png'
            elif mime_type.startswith('image/jpeg'):
                ext = '.jpg'
            elif mime_type.startswith('image/'):
                ext = '.png'
            elif mime_type.startswith('text/'):
                ext = '.txt'
            
            # Диалог сохранения
            filename, _ = QFileDialog.getSaveFileName(
                self, 
                'Сохранить элемент', 
                str(Path.home() / f'clipboard{ext}'),
                f'Все файлы (*)'
            )
            
            if filename:
                if content_path:
                    # Копируем файл
                    shutil.copy2(content_path, filename)
                else:
                    # Сохраняем текст
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(preview)
        except Exception as e:
            print(f"Save error: {e}")
    
    def toggle_pin_item(self, item_id, current_pinned):
        """Закрепить/открепить элемент"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            new_pinned = 0 if current_pinned else 1
            
            # Если закрепляем, проверяем лимит (90% от total)
            if new_pinned == 1:
                cursor.execute('SELECT COUNT(*) FROM items')
                total_items = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM items WHERE pinned = 1')
                pinned_count = cursor.fetchone()[0]
                
                max_pinned = int(total_items * 0.9)
                if pinned_count >= max_pinned:
                    print(f"Нельзя закрепить больше {max_pinned} элементов (90% от {total_items})")
                    conn.close()
                    return
            
            # Обновляем статус
            cursor.execute('UPDATE items SET pinned = ? WHERE id = ?', (new_pinned, item_id))
            conn.commit()
            conn.close()
            
            # Обновляем список с отключением обновления
            self.list_widget.setUpdatesEnabled(False)
            self.list_widget.clear()
            self.load_history()
            self.list_widget.setUpdatesEnabled(True)
        except Exception as e:
            print(f"Pin error: {e}")

def main():
    app = QApplication(sys.argv)
    window = ClipHistoryWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
