#!/usr/bin/env python3
"""
ClipHistory Qt UI - современный дизайн как в Windows
"""

import os
os.environ['QT_QPA_PLATFORM'] = 'xcb'

from PyQt5.QtWidgets import (QApplication, QWidget, QListWidget, QListWidgetItem,
                             QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, 
                             QFileDialog, QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QByteArray, QTimer, QEvent
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
    
    def __init__(self, item_id, mime_type, content_path, preview, is_dark, pinned, parent_window=None, scale=1.0, timestamp=None, text_max_lines=6, font_family='Noto Sans'):
        super().__init__()
        self.item_id = item_id
        self.mime_type = mime_type
        self.content_path = content_path
        self.preview = preview
        self.is_dark = is_dark
        self.pinned = pinned
        self.parent_window = parent_window
        self.scale = scale
        self.timestamp = timestamp
        self.text_max_lines = text_max_lines
        self.font_family = font_family
        
        # Размеры и отступы элемента
        self.element_margin = int(4 * self.scale)
        self.element_min_height = int(48 * self.scale)
        self.element_max_height = int(188 * self.scale)
        self.element_spacing = int(6 * self.scale)
        
        # Размеры контента
        self.image_max_height = int(180 * self.scale)
        self.border_radius = int(8 * self.scale)
        self.content_padding = int(6 * self.scale)
        
        # Размеры иконок и кнопок
        self.icon_size = int(40 * self.scale)
        self.icon_border_radius = int(6 * self.scale)
        self.button_size = int(20 * self.scale)
        self.button_icon_size = int(14 * self.scale)
        
        # Размеры шрифтов
        self.preview_font_size = int(11 * self.scale)
        self.small_preview_font_size = int(9 * self.scale)
        
        # Рассчитываем высоту текста на основе количества строк
        # CSS padding добавляется ВНУТРЬ, поэтому нужно учесть его дважды
        from PyQt5.QtGui import QFontMetrics
        font = QFont(self.font_family, self.preview_font_size, QFont.Light)
        metrics = QFontMetrics(font)
        line_height = metrics.lineSpacing()
        # Высота = строки + двойной padding (верх+низ в CSS)
        self.preview_max_height = int(line_height * self.text_max_lines + self.content_padding * 4)
        self.preview_min_height = int(52 * self.scale)
        
        small_font = QFont(self.font_family, self.small_preview_font_size, QFont.Normal)
        small_metrics = QFontMetrics(small_font)
        small_line_height = small_metrics.lineSpacing()
        self.small_preview_max_height = int(small_line_height * self.text_max_lines + self.content_padding * 4)
        self.small_preview_min_height = int(42 * self.scale)
        
        # Overlay (время и иконка типа)
        self.overlay_margin_h = int(4 * self.scale)
        self.overlay_margin_v = int(2 * self.scale)
        self.overlay_spacing = int(3 * self.scale)
        self.overlay_border_radius = int(4 * self.scale)
        self.type_icon_size = int(12 * self.scale)
        self.time_font_size = int(7 * self.scale)
        
        # Кнопки
        self.buttons_spacing = int(4 * self.scale)

        self.width = 230
        
        self.setFrameStyle(QFrame.NoFrame)
        self.setCursor(Qt.PointingHandCursor)
        
        # Динамическая высота с ограничениями
        from PyQt5.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.setMinimumHeight(self.element_min_height)
        self.setMaximumHeight(self.element_max_height)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(self.element_margin, self.element_margin, self.element_margin, self.element_margin)
        layout.setSpacing(self.element_spacing)
        
        self.setup_ui(layout)
    
    def format_time_ago(self):
        """Форматировать время относительно текущего момента"""
        if not self.timestamp:
            return ""
        
        import time
        from datetime import datetime, timedelta
        
        now = time.time()
        diff = now - self.timestamp
        
        if diff < 60:
            return "только что"
        elif diff < 3600:
            mins = int(diff / 60)
            return f"{mins} мин\nназад"
        elif diff < 86400:  # меньше суток
            hours = int(diff / 3600)
            return f"{hours} ч\nназад"
        elif diff < 172800:  # меньше 2 суток
            return "вчера"
        elif diff < 604800:  # меньше недели
            days = int(diff / 86400)
            return f"{days} дн назад"
        else:
            # Показываем дату
            dt = datetime.fromtimestamp(self.timestamp)
            return dt.strftime("%d.%m.%Y")
    
    def get_mime_icon(self):
        """Получить название SVG иконки для типа MIME"""
        if self.mime_type.startswith('text/') or self.mime_type in ['UTF8_STRING', 'STRING', 'TEXT']:
            if 'html' in self.mime_type:
                return 'web'
            elif 'uri-list' in self.mime_type:
                return 'link-variant'
            else:
                return 'text'
        elif self.mime_type.startswith('image/'):
            return 'image'
        else:
            return 'file'
    
    def create_svg_icon(self, svg_path, color, size=48):
        """Создать иконку из SVG"""
        # SVG иконки Material Design Icons
        svg_icons = {
            'trash': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M9,3V4H4V6H5V19A2,2 0 0,0 7,21H17A2,2 0 0,0 19,19V6H20V4H15V3H9M7,6H17V19H7V6M9,8V17H11V8H9M13,8V17H15V8H13Z" /></svg>''',
            'pin': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M16,12V4H17V2H7V4H8V12L6,14V16H11.2V22H12.8V16H18V14L16,12Z" /></svg>''',
            'pin-off': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M2,5.27L3.28,4L20,20.72L18.73,22L12.8,16.07V22H11.2V16H6V14L8,12V11.27L2,5.27M16,12L18,14V16H17.82L8,6.18V4H7V2H17V4H16V12Z" /></svg>''',
            'download': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z" /></svg>''',
            'clipboard': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M19 3H14.82C14.4 1.84 13.3 1 12 1S9.6 1.84 9.18 3H5C3.9 3 3 3.9 3 5V19C3 20.1 3.9 21 5 21H19C20.1 21 21 20.1 21 19V5C21 3.9 20.1 3 19 3M12 3C12.55 3 13 3.45 13 4S12.55 5 12 5 11 4.55 11 4 11.45 3 12 3M7 7H17V5H19V19H5V5H7V7M7 9V11H17V9H7M7 13V15H17V13H7Z" /></svg>''',
            'close': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z" /></svg>''',
            'text': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M14,17H7V15H14M17,13H7V11H17M17,9H7V7H17M19,3H5C3.89,3 3,3.89 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V5C21,3.89 20.1,3 19,3Z" /></svg>''',
            'image': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M8.5,13.5L11,16.5L14.5,12L19,18H5M21,19V5C21,3.89 20.1,3 19,3H5A2,2 0 0,0 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19Z" /></svg>''',
            'link': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M10.59,13.41C11,13.8 11,14.44 10.59,14.83C10.2,15.22 9.56,15.22 9.17,14.83C7.22,12.88 7.22,9.71 9.17,7.76V7.76L12.71,4.22C14.66,2.27 17.83,2.27 19.78,4.22C21.73,6.17 21.73,9.34 19.78,11.29L18.29,12.78C18.3,11.96 18.17,11.14 17.89,10.36L18.36,9.88C19.54,8.71 19.54,6.81 18.36,5.64C17.19,4.46 15.29,4.46 14.12,5.64L10.59,9.17C9.41,10.34 9.41,12.24 10.59,13.41M13.41,9.17C13.8,8.78 14.44,8.78 14.83,9.17C16.78,11.12 16.78,14.29 14.83,16.24V16.24L11.29,19.78C9.34,21.73 6.17,21.73 4.22,19.78C2.27,17.83 2.27,14.66 4.22,12.71L5.71,11.22C5.7,12.04 5.83,12.86 6.11,13.65L5.64,14.12C4.46,15.29 4.46,17.19 5.64,18.36C6.81,19.54 8.71,19.54 9.88,18.36L13.41,14.83C14.59,13.66 14.59,11.76 13.41,10.59C13,10.2 13,9.56 13.41,9.17Z" /></svg>''',
            'link-variant': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M3.9,12C3.9,10.29 5.29,8.9 7,8.9H11V7H7A5,5 0 0,0 2,12A5,5 0 0,0 7,17H11V15.1H7C5.29,15.1 3.9,13.71 3.9,12M8,13H16V11H8V13M17,7H13V8.9H17C18.71,8.9 20.1,10.29 20.1,12C20.1,13.71 18.71,15.1 17,15.1H13V17H17A5,5 0 0,0 22,12A5,5 0 0,0 17,7Z" /></svg>''',
            'web': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M16.36,14C16.44,13.34 16.5,12.68 16.5,12C16.5,11.32 16.44,10.66 16.36,10H19.74C19.9,10.64 20,11.31 20,12C20,12.69 19.9,13.36 19.74,14M14.59,19.56C15.19,18.45 15.65,17.25 15.97,16H18.92C17.96,17.65 16.43,18.93 14.59,19.56M14.34,14H9.66C9.56,13.34 9.5,12.68 9.5,12C9.5,11.32 9.56,10.65 9.66,10H14.34C14.43,10.65 14.5,11.32 14.5,12C14.5,12.68 14.43,13.34 14.34,14M12,19.96C11.17,18.76 10.5,17.43 10.09,16H13.91C13.5,17.43 12.83,18.76 12,19.96M8,8H5.08C6.03,6.34 7.57,5.06 9.4,4.44C8.8,5.55 8.35,6.75 8,8M5.08,16H8C8.35,17.25 8.8,18.45 9.4,19.56C7.57,18.93 6.03,17.65 5.08,16M4.26,14C4.1,13.36 4,12.69 4,12C4,11.31 4.1,10.64 4.26,10H7.64C7.56,10.66 7.5,11.32 7.5,12C7.5,12.68 7.56,13.34 7.64,14M12,4.03C12.83,5.23 13.5,6.57 13.91,8H10.09C10.5,6.57 11.17,5.23 12,4.03M18.92,8H15.97C15.65,6.75 15.19,5.55 14.59,4.44C16.43,5.07 17.96,6.34 18.92,8M12,2C6.47,2 2,6.5 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z" /></svg>''',
            'file': '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="{color}" d="M13,9V3.5L18.5,9M6,2C4.89,2 4,2.89 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2H6Z" /></svg>'''
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
    
    def create_thumbnail(self, image_path, max_height, max_width=None):
        """Создать миниатюру изображения с учетом пропорций"""
        try:
            pixmap = QPixmap(str(image_path))
            if pixmap.isNull():
                return None
            
            # Если max_width не передан, вычисляем из max_height
            if max_width is None:
                max_width = int(max_height * 6.67)
            
            print(f"[DEBUG] Исходное изображение: {pixmap.width()}x{pixmap.height()}")
            print(f"[DEBUG] Ограничения: max_width={max_width}, max_height={max_height}")
            
            if pixmap.height() > max_height or pixmap.width() > max_width:
                # Используем scaled с KeepAspectRatio - масштабирует до первой границы
                scaled_pixmap = pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                print(f"[DEBUG] Масштабированное: {scaled_pixmap.width()}x{scaled_pixmap.height()}")
                return scaled_pixmap
            
            print(f"[DEBUG] Изображение не масштабируется (меньше лимитов)")
            return pixmap
        except Exception as e:
            print(f"[DEBUG] Ошибка: {e}")
            return None
    
    def setup_ui(self, layout):
        """Настройка UI элемента"""
        mime_type = self.mime_type
        content_path = self.content_path
        preview = self.preview
        is_dark = self.is_dark
        
        # Контейнер для контента с относительным позиционированием
        content_container = QWidget()
        content_container.setMinimumHeight(self.element_min_height)
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Для изображений - большое превью на всю ширину
        if mime_type.startswith('image/') and content_path:
            # Загружаем изображение для расчета пропорций
            from PyQt5.QtGui import QPixmap
            import tempfile
            pixmap = QPixmap(str(content_path))
            
            if not pixmap.isNull():
                # Доступная ширина = content_width - margins (left+right)
                available_width = self.parent_window.content_width - (self.element_margin * 2)
                aspect_ratio = pixmap.height() / pixmap.width() if pixmap.width() > 0 else 1
                scaled_height = int(available_width * aspect_ratio)
                
                # Ограничиваем высоту
                container_height = max(self.element_min_height, min(scaled_height, self.image_max_height))
                
                # Масштабируем изображение до размера контейнера
                scaled_pixmap = pixmap.scaled(available_width, container_height,
                                             Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                # Сохраняем масштабированное изображение во временный файл
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                scaled_pixmap.save(temp_file.name, 'PNG')
                temp_file.close()
                
                # Контейнер для изображения - используем background-image с масштабированным файлом
                safe_path = temp_file.name.replace('\\', '/').replace('"', '\\"')
                image_container = QFrame()
                image_container.setFixedHeight(container_height)
                image_container.setStyleSheet(f"""
                    QFrame {{
                        background-color: {'#3a3a3a' if is_dark else '#f0f0f0'};
                        background-image: url("{safe_path}");
                        background-repeat: no-repeat;
                        background-position: center;
                        background-size: contain;
                        border-radius: {self.border_radius}px;
                    }}
                """)
                
                # Сохраняем путь для последующей очистки
                image_container.setProperty('temp_image', temp_file.name)
                
                content_layout.addWidget(image_container)
            else:
                # Если изображение не загрузилось - пустой контейнер
                pass
        else:
            # Для текста - просто большой текст без иконки
            if mime_type.startswith('text/plain') or mime_type in ['UTF8_STRING', 'STRING', 'TEXT']:
                # Рассчитываем максимальную высоту и обрезаем текст
                from PyQt5.QtGui import QFontMetrics
                from PyQt5.QtCore import QRect
                
                font = QFont(self.font_family, self.preview_font_size, QFont.Light)
                metrics = QFontMetrics(font)
                
                # Доступная ширина для текста
                available_width = self.parent_window.content_width - (self.element_margin * 2) - (self.content_padding * 2)
                
                # Разбиваем текст на строки учитывая переносы
                lines = []
                for paragraph in preview.split('\n'):
                    if not paragraph.strip():
                        lines.append('')
                        if len(lines) >= self.text_max_lines:
                            break
                        continue
                    
                    words = paragraph.split(' ')
                    current_line = ''
                    
                    for word in words:
                        test_line = current_line + (' ' if current_line else '') + word
                        if metrics.horizontalAdvance(test_line) <= available_width:
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                                if len(lines) >= self.text_max_lines:
                                    break
                            # Если слово слишком длинное - берём его целиком как строку
                            current_line = word
                    
                    if len(lines) >= self.text_max_lines:
                        break
                    if current_line:
                        lines.append(current_line)
                
                # Берём только первые N строк
                truncated_text = '\n'.join(lines[:self.text_max_lines])
                
                line_height = metrics.lineSpacing()
                max_height = int(line_height * self.text_max_lines + self.content_padding * 2)
                
                # Текст большим шрифтом с ограничением по строкам
                preview_label = QLabel(truncated_text)
                preview_label.setWordWrap(True)
                preview_label.setMaximumHeight(max_height)
                preview_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
                preview_label.setStyleSheet(f"""
                    color: {'#e0e0e0' if is_dark else '#333333'};
                    font-size: {self.preview_font_size}px;
                    font-weight: 300;
                    padding: {self.content_padding}px;
                    background-color: {'#3a3a3a' if is_dark else '#f0f0f0'};
                    border-radius: {self.border_radius}px;
                """)
                preview_label.setTextFormat(Qt.PlainText)
                content_layout.addWidget(preview_label)
            else:
                # Для других типов - иконка + текст
                icon_label = QLabel()
                icon_label.setFixedSize(self.icon_size, self.icon_size)
                icon_label.setScaledContents(True)
                icon_label.setStyleSheet(f"""
                    background-color: {'#3a3a3a' if is_dark else '#f0f0f0'};
                    border-radius: {self.icon_border_radius}px;
                """)
                
                # Иконка по типу
                icon_name = '🌐' if mime_type.startswith('text/html') else '📁' if mime_type.startswith('text/uri-list') else '❓'
                
                icon_label.setText(icon_name)
                icon_label.setAlignment(Qt.AlignCenter)
                icon_label.setFont(QFont('Sans', int(self.icon_size * 0.35)))
                
                content_layout.addWidget(icon_label)
                
                # Текст (справа)
                text_container = QVBoxLayout()
                text_container.setSpacing(self.buttons_spacing)
                
                # Рассчитываем и обрезаем текст для маленького preview
                from PyQt5.QtGui import QFontMetrics
                small_font = QFont(self.font_family, self.small_preview_font_size, QFont.Normal)
                small_metrics = QFontMetrics(small_font)
                
                # Доступная ширина меньше из-за иконки
                available_width = self.parent_window.content_width - (self.element_margin * 2) - self.icon_size - self.element_spacing
                
                # Разбиваем текст на строки учитывая переносы
                lines = []
                for paragraph in preview.split('\n'):
                    if not paragraph.strip():
                        lines.append('')
                        if len(lines) >= self.text_max_lines:
                            break
                        continue
                    
                    words = paragraph.split(' ')
                    current_line = ''
                    
                    for word in words:
                        test_line = current_line + (' ' if current_line else '') + word
                        if small_metrics.horizontalAdvance(test_line) <= available_width:
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                                if len(lines) >= self.text_max_lines:
                                    break
                            current_line = word
                    
                    if len(lines) >= self.text_max_lines:
                        break
                    if current_line:
                        lines.append(current_line)
                
                truncated_text = '\n'.join(lines[:self.text_max_lines])
                
                small_line_height = small_metrics.lineSpacing()
                max_height = int(small_line_height * self.text_max_lines)
                
                preview_label = QLabel(truncated_text)
                preview_label.setWordWrap(True)
                preview_label.setMaximumHeight(max_height)
                preview_label.setStyleSheet(f"""
                    color: {'#e0e0e0' if is_dark else '#333333'};
                    font-size: {self.small_preview_font_size}px;
                    padding: {self.content_padding}px;
                """)
                preview_label.setTextFormat(Qt.PlainText)
                text_container.addWidget(preview_label)
                text_container.addStretch()
                
                content_layout.addLayout(text_container, 1)
        
        # Добавляем контейнер в основной layout
        layout.addWidget(content_container, 1)
        
        # Метка времени и иконки типа поверх контента (оверлей)
        if self.timestamp:
            # Используем frame с абсолютным позиционированием через stylesheet
            overlay_container = QFrame(content_container)
            overlay_layout = QHBoxLayout(overlay_container)
            overlay_layout.setContentsMargins(self.overlay_margin_h, self.overlay_margin_v, self.overlay_margin_h, self.overlay_margin_v)
            overlay_layout.setSpacing(self.overlay_spacing)
            
            # Иконка типа (маленькая)
            icon_color = '#ffffff' if is_dark else '#000000'
            type_icon = self.create_svg_icon(self.get_mime_icon(), icon_color, self.type_icon_size)
            type_icon_label = QLabel()
            type_icon_label.setPixmap(type_icon)
            type_icon_label.setFixedSize(self.type_icon_size, self.type_icon_size)
            overlay_layout.addWidget(type_icon_label)
            
            # Время (компактное)
            time_text = self.format_time_ago().replace('\n', ' ')
            time_label = QLabel(time_text)
            time_label.setStyleSheet(f"""
                color: {'#ffffff' if is_dark else '#000000'};
                font-size: {self.time_font_size}px;
                background: transparent;
                border: none;
            """)
            overlay_layout.addWidget(time_label)
            
            # Стиль оверлея с фиксированной позицией
            # Используем цвет фона элемента с прозрачностью
            if is_dark:
                bg_r, bg_g, bg_b = 43, 43, 43  # #2b2b2b
            else:
                bg_r, bg_g, bg_b = 255, 255, 255  # #ffffff
            
            overlay_container.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba({bg_r}, {bg_g}, {bg_b}, 0.85);
                    border-top-left-radius: {self.overlay_border_radius}px;
                    border-top-right-radius: 0px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 0px;
                    border: none;
                }}
            """)
            
            # Размещаем в правом нижнем углу через geometry
            overlay_container.adjustSize()
            # Сохраняем ссылку для обновления позиции при ресайзе
            self.time_overlay = overlay_container
            self.time_overlay_parent = content_container
        
        # Кнопки справа (только удалить и закрепить)
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(self.buttons_spacing)
        buttons_layout.setAlignment(Qt.AlignTop)
        
        # Кнопка удаления
        delete_btn = QLabel()
        icon_color = '#e0e0e0' if is_dark else '#333333'
        delete_icon = self.create_svg_icon('trash', icon_color, self.button_icon_size)
        delete_btn.setPixmap(delete_icon)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setFixedSize(self.button_size, self.button_size)
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
        pin_icon_name = 'pin-off' if self.pinned else 'pin'
        pin_icon = self.create_svg_icon(pin_icon_name, icon_color, self.button_icon_size)
        pin_btn.setPixmap(pin_icon)
        pin_btn.setCursor(Qt.PointingHandCursor)
        pin_btn.setFixedSize(self.button_size, self.button_size)
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
                border-radius: {self.border_radius}px;
            }}
        """)
        
        # Обновляем позицию оверлея после создания виджета
        if hasattr(self, 'time_overlay'):
            QTimer.singleShot(0, self.update_overlay_position)
    
    def update_overlay_position(self):
        """Обновить позицию оверлея времени в правом нижнем углу"""
        if hasattr(self, 'time_overlay') and hasattr(self, 'time_overlay_parent'):
            parent = self.time_overlay_parent
            overlay = self.time_overlay
            
            # Позиционируем в правом нижнем углу родителя без отступов
            x = parent.width() - overlay.width()
            y = parent.height() - overlay.height()
            overlay.move(x, y)
            overlay.raise_()  # Поднимаем на передний план
    
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
        
        # Проверка и запуск демона если не запущен
        self.check_and_start_daemon()
        
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
        self.border = int(2 * self.scale)
        self.scrollbar_width = int(12 * self.scale)
        self.content_width = int(320 * self.scale)
        self.window_width = self.content_width + self.scrollbar_width + self.border 
        self.window_height = int(450 * self.scale)
        self.window_max_height = int(900 * self.scale)
        self.window_min_width = self.content_width - self.scrollbar_width
        
        # Размеры header
        self.header_height = int(33 * self.scale)
        self.header_margin_h = int(10 * self.scale)
        self.header_spacing = int(8 * self.scale)
        self.app_icon_size = int(18 * self.scale)
        self.title_font_size = int(10 * self.scale)
        self.close_button_size = int(32 * self.scale)
        self.close_icon_size = int(20 * self.scale)
        
        # Resize
        self.resize_margin = int(8 * self.scale)
        self.resize_handle_height = int(4 * self.scale)
        
        # List
        self.list_spacing = int(2 * self.scale)
        self.list_item_gap = int(2 * self.scale)
        
        self.init_ui()
        self.load_history()
        self.position_near_cursor()
        self.setup_auto_refresh()
    
    def check_and_start_daemon(self):
        """Проверка и запуск демона если не запущен"""
        daemon_running = False
        lock_file = Path.home() / '.cache' / 'cliphistory' / '.daemon.lock'
        
        if lock_file.exists():
            try:
                with open(lock_file) as f:
                    pid = int(f.read().strip())
                os.kill(pid, 0)
                
                # Исключаем зомби-процессы
                is_zombie = False
                try:
                    with open(f"/proc/{pid}/stat", "r") as f:
                        stat = f.read().split()
                        if len(stat) > 2 and stat[2] == 'Z':
                            is_zombie = True
                except:
                    pass
                    
                if not is_zombie:
                    daemon_running = True
            except (ProcessLookupError, ValueError, FileNotFoundError):
                pass
                
        if not daemon_running:
            print("⚠️  Демон не запущен, запускаем...")
            try:
                subprocess.Popen(
                    ['/usr/local/bin/cliphistory'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                import time
                time.sleep(1)  # Даем время демону запуститься
            except Exception as e:
                print(f"Ошибка запуска демона: {e}")
    
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
                    
                    # Проверяем имя процесса, чтобы избежать переиспользования PID
                    is_valid_ui = False
                    try:
                        with open(f"/proc/{pid}/cmdline", "r") as cmdf:
                            cmd = cmdf.read().replace('\x00', ' ')
                            if 'cliphistory' in cmd or 'python' in cmd or 'clipshow' in cmd:
                                is_valid_ui = True
                    except:
                        pass
                        
                    if is_valid_ui:
                        return False  # Процесс существует и это наш UI
                    else:
                        # PID переиспользован, удаляем lock
                        self.lock_file.unlink()
                except (ProcessLookupError, ValueError, PermissionError):
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
    
    def get_config_path(self):
        """Возвращает путь к пользовательскому конфигу (копируя дефолтный если нужно)"""
        user_config_dir = Path.home() / '.config' / 'cliphistory'
        user_config_path = user_config_dir / 'config.json'
        system_config_path = Path(__file__).parent / 'config.json'
        
        if not user_config_path.exists():
            user_config_dir.mkdir(parents=True, exist_ok=True)
            if system_config_path.exists():
                import shutil
                shutil.copy2(system_config_path, user_config_path)
            else:
                user_config_path.write_text('{}')
        return user_config_path

    def load_config(self):
        """Загрузка конфигурации"""
        config_path = self.get_config_path()
        try:
            with open(config_path) as f:
                config = json.load(f)
                # Дефолтные значения для отсутствующих параметров
                config.setdefault('auto_paste', True)
                config.setdefault('close_on_focus_loss', False)
                config.setdefault('ui_scale', 1.5)
                config.setdefault('window_width', 320)
                config.setdefault('window_height', 350)
                config.setdefault('text_max_lines', 6)
                config.setdefault('font_family', 'Noto Sans')
                return config
        except Exception:
            return {
                'auto_paste': True,
                'close_on_focus_loss': False,
                'ui_scale': 1.5,
                'window_width': 320,
                'window_height': 350,
                'text_max_lines': 6,
                'font_family': 'Noto Sans'
            }
    
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
    
    def create_svg_icon(self, svg_path, color, size):
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
                # Сохраняем позицию скролла
                scroll_position = self.list_widget.verticalScrollBar().value()
                
                self.list_widget.setUpdatesEnabled(False)
                self.list_widget.clear()
                self.load_history()
                
                # Восстанавливаем позицию скролла
                self.list_widget.verticalScrollBar().setValue(scroll_position)
                self.list_widget.setUpdatesEnabled(True)
                self.last_item_count = current_count
        except Exception:
            pass
    
    def init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle("История буфера обмена")
        
        # Используем Qt.Tool, чтобы окно не появлялось на панели задач.
        # Для закрытия при потере фокуса мы используем события деактивации и focusChanged.
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        
        # Используем переменные размеров из __init__
        self.setMinimumWidth(self.window_min_width)
        self.setMinimumHeight(self.window_height)
        self.setMaximumHeight(self.window_max_height)
        self.resize(self.window_width, self.window_height)
        
        # Для изменения размера
        self.resizing = False
        self.resize_direction = None
        
        # Главный layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Полоска для изменения размера сверху
        resize_handle = QFrame()
        resize_handle.setFixedHeight(self.resize_handle_height)
        resize_handle.setCursor(Qt.SizeVerCursor)
        if self.is_dark:
            resize_handle.setStyleSheet("""
                background-color: #404040;
                border: none;
            """)
        else:
            resize_handle.setStyleSheet("""
                background-color: #d0d0d0;
                border: none;
            """)
        self.resize_handle = resize_handle
        main_layout.addWidget(resize_handle)
        
        # Заголовок
        header = QFrame()
        header.setFixedHeight(self.header_height)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(self.header_margin_h, 0, self.header_margin_h, 0)
        header_layout.setSpacing(self.header_spacing)
        
        # Иконка приложения
        icon_color = '#ffffff' if self.is_dark else '#000000'
        app_icon = QLabel()
        app_icon.setPixmap(self.create_svg_icon('clipboard', icon_color, self.app_icon_size))
        app_icon.setFixedSize(self.app_icon_size, self.app_icon_size)
        header_layout.addWidget(app_icon)
        
        title = QLabel("История буфера обмена")
        title.setFont(QFont('Sans', self.title_font_size, QFont.Bold))
        title.setAlignment(Qt.AlignVCenter)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Кнопка закрытия
        close_btn = QPushButton()
        close_btn.setFixedSize(self.close_button_size, self.close_button_size)
        close_btn.setIcon(QIcon(self.create_svg_icon('close', icon_color, self.close_icon_size)))
        close_btn.setIconSize(QSize(self.close_icon_size, self.close_icon_size))
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
        self.list_widget.setSpacing(self.list_spacing)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        
        if self.is_dark:
            self.list_widget.setStyleSheet("""
                QListWidget {
                    background-color: #2b2b2b;
                    border: none;
                    padding: 0px 0px """ + str(int(10 * self.scale)) + """px 0px;
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
                    width: """ + str(self.scrollbar_width) + """px;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background: #555555;
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
                    padding: 0px 0px """ + str(int(10 * self.scale)) + """px 0px;
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
                    width: """ + str(self.scrollbar_width) + """px;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background: #cccccc;
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
            
            # Получаем позицию курсора через Qt
            from PyQt5.QtGui import QCursor
            cursor_pos = QCursor.pos()
            cursor_x, cursor_y = cursor_pos.x(), cursor_pos.y()

            # Получаем размер экрана, на котором находится курсор
            from PyQt5.QtWidgets import QApplication
            desktop = QApplication.desktop()
            screen_number = desktop.screenNumber(cursor_pos)
            screen = desktop.screenGeometry(screen_number)
            screen_width = screen.width()
            screen_height = screen.height()
            screen_x = screen.x()
            screen_y = screen.y()
            
            margin = 20  # Отступ от края экрана и от курсора
            
            # Пробуем разместить справа-снизу от курсора (по умолчанию)
            x = cursor_x + margin
            y = cursor_y + margin
            
            # Проверяем правую границу - если не влезает, размещаем СЛЕВА
            if x + self.width() > screen_x + screen_width - margin:
                x = cursor_x - self.width() - margin
            
            # Проверяем нижнюю границу - если не влезает, размещаем СВЕРХУ
            if y + self.height() > screen_y + screen_height - margin:
                y = cursor_y - self.height() - margin
            
            # Если всё равно вылезает за границы (курсор в углу) - прижимаем к краям
            if x < screen_x + margin:
                x = screen_x + margin
            if y < screen_y + margin:
                y = screen_y + margin
            if x + self.width() > screen_x + screen_width - margin:
                x = screen_x + screen_width - self.width() - margin
            if y + self.height() > screen_y + screen_height - margin:
                y = screen_y + screen_height - self.height() - margin
            
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
            SELECT id, mime_type, content_path, preview, COALESCE(pinned, 0) as pinned, timestamp
            FROM items 
            ORDER BY pinned DESC, timestamp DESC
            LIMIT 50
        ''')
        items = cursor.fetchall()
        conn.close()
        
        for item_id, mime_type, content_path, preview, pinned, timestamp in items:
            widget = ClipboardItemWidget(item_id, mime_type, content_path, preview[:1000], 
                                        self.is_dark, pinned, parent_window=self, scale=self.scale, timestamp=timestamp,
                                        text_max_lines=self.config.get('text_max_lines', 6),
                                        font_family=self.config.get('font_family', 'Noto Sans'))
            # Устанавливаем максимальную ширину = ширина контента - скроллбар - отступ
            # widget.setMaximumWidth(self.content_width - self.scrollbar_width - self.list_item_gap)
            widget.setMaximumWidth(self.content_width - self.list_item_gap)
            item = QListWidgetItem(self.list_widget)
            # Динамическая высота элемента - используем sizeHint виджета
            item.setSizeHint(widget.sizeHint())
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

    def hideEvent(self, event):
        """При скрытии окна (например, Popup по клику мимо) вызываем закрытие для снятия блокировок"""
        self.close()
        super().hideEvent(event)
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        self.release_lock()
        event.accept()

    def changeEvent(self, event):
        """Обработка смены состояния окна"""
        # Если окно теряет фокус (выходит на задний план)
        if event.type() == QEvent.ActivationChange:
            if not self.isActiveWindow() and self.config.get('close_on_focus_loss', False):
                self.close()
        super().changeEvent(event)
    
    def get_resize_direction(self, pos):
        """Определить направление изменения размера"""
        rect = self.rect()
        y = pos.y()
        
        # Только верхняя граница (полоска + небольшая область)
        if y <= self.resize_handle_height + self.resize_margin:
            return 'top'
        return None
    
    def mousePressEvent(self, event):
        """Начало перетаскивания окна или изменения размера"""
        if event.button() == Qt.LeftButton:
            # Проверяем изменение размера
            resize_dir = self.get_resize_direction(event.pos())
            if resize_dir:
                self.resizing = True
                self.resize_direction = resize_dir
                self.resize_start_pos = event.globalPos()
                self.resize_start_geometry = self.geometry()
                event.accept()
                return
            
            # Проверяем что клик был в области заголовка для перетаскивания
            if hasattr(self, 'header_widget') and self.header_widget.geometry().contains(event.pos()):
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
            else:
                event.ignore()
    
    def mouseMoveEvent(self, event):
        """Перетаскивание окна или изменение размера"""
        # Изменение курсора при наведении на верхнюю границу
        if not self.resizing and not self.drag_position:
            resize_dir = self.get_resize_direction(event.pos())
            if resize_dir == 'top':
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        
        # Изменение высоты через верх (меняем и Y позицию, и высоту)
        if event.buttons() == Qt.LeftButton and self.resizing:
            delta = event.globalPos() - self.resize_start_pos
            geo = self.resize_start_geometry
            
            # Новая высота (при движении вверх delta.y отрицательный, высота увеличивается)
            new_height = max(self.minimumHeight(), min(self.maximumHeight(), geo.height() - delta.y()))
            # Если высота изменилась, сдвигаем окно
            if new_height != geo.height():
                new_y = geo.y() + (geo.height() - new_height)
                self.setGeometry(geo.x(), new_y, self.width(), new_height)
            event.accept()
        # Перетаскивание окна
        elif event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Остановка перетаскивания или изменения размера"""
        if event.button() == Qt.LeftButton:
            self.drag_position = None
            self.resizing = False
            self.resize_direction = None
            self.setCursor(Qt.ArrowCursor)
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
            
            # Сохраняем позицию скролла
            scroll_position = self.list_widget.verticalScrollBar().value()
            
            # Обновляем список с отключением обновления
            self.list_widget.setUpdatesEnabled(False)
            self.list_widget.clear()
            self.load_history()
            
            # Восстанавливаем позицию скролла
            self.list_widget.verticalScrollBar().setValue(scroll_position)
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
            
            # Сохраняем позицию скролла
            scroll_position = self.list_widget.verticalScrollBar().value()
            
            # Обновляем список с отключением обновления
            self.list_widget.setUpdatesEnabled(False)
            self.list_widget.clear()
            self.load_history()
            
            # Восстанавливаем позицию скролла
            self.list_widget.verticalScrollBar().setValue(scroll_position)
            self.list_widget.setUpdatesEnabled(True)
        except Exception as e:
            print(f"Pin error: {e}")

def main():
    # Возвращаем стандартное масштабирование Qt,
    # так как теперь мы запускаем UI корректно через системный лаунчер.
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    window = ClipHistoryWindow()
    window.show()
    window.raise_()
    window.activateWindow()
    
    # Для Linux/X11: отлавливаем изменение фокуса приложения в целом
    def check_focus():
        # Если включена опция закрытия и нет активного окна Qt
        if window.config.get('close_on_focus_loss', False):
            if QApplication.activeWindow() is None:
                window.close()

    if window.config.get('close_on_focus_loss', False):
        # Начинаем следить за фокусом через 500мс после запуска окна (чтобы дать время WM выдать фокус)
        poll_timer = QTimer()
        poll_timer.timeout.connect(check_focus)
        QTimer.singleShot(500, lambda: poll_timer.start(250))
        window.poll_timer = poll_timer

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
