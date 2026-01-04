#!/usr/bin/env python3
"""
ClipHistory UI - Показывает историю и вставляет выбранный элемент
"""

import subprocess
import sqlite3
import json
import sys
from pathlib import Path

class ClipShow:
    def __init__(self):
        self.cache_dir = Path.home() / '.cache' / 'cliphistory'
        self.db_path = self.cache_dir / 'history.db'
        self.config = self.load_config()
        
    def load_config(self):
        """Загрузка конфигурации"""
        config_path = Path(__file__).parent / 'config.json'
        try:
            with open(config_path) as f:
                return json.load(f)
        except Exception:
            return {'auto_paste': True, 'debug': False}
    
    def get_history(self):
        """Получить историю из БД"""
        if not self.db_path.exists():
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, mime_type, content_path, preview 
            FROM items 
            ORDER BY timestamp DESC
        ''')
        items = cursor.fetchall()
        conn.close()
        return items
    
    def format_item(self, item):
        """Форматировать элемент для показа"""
        item_id, mime_type, content_path, preview = item
        
        # Добавляем иконку по типу
        if mime_type.startswith('image/'):
            icon = '🖼️ '
        elif mime_type.startswith('text/html'):
            icon = '🌐 '
        elif mime_type.startswith('text/uri-list'):
            icon = '📁 '
        else:
            icon = '📝 '
        
        # Ограничиваем длину preview
        max_len = self.config.get('max_preview_length', 80)
        if len(preview) > max_len:
            preview = preview[:max_len - 3] + '...'
        
        # Заменяем переносы строк на пробелы
        preview = preview.replace('\n', ' ').replace('\r', '').replace('\t', ' ')
        
        return f"{item_id}|{icon}{preview}"
    
    def get_cursor_position(self):
        """Получить позицию курсора мыши"""
        try:
            result = subprocess.run(
                ['xdotool', 'getmouselocation', '--shell'],
                capture_output=True, text=True, timeout=0.5
            )
            pos = {}
            for line in result.stdout.strip().split('\n'):
                if '=' in line:
                    key, val = line.split('=')
                    pos[key] = int(val)
            return pos.get('X', 0), pos.get('Y', 0)
        except Exception:
            return 0, 0
    
    def is_dark_theme(self):
        """Определить используется ли тёмная тема"""
        try:
            # Проверяем тему Cinnamon
            result = subprocess.run(
                ['gsettings', 'get', 'org.cinnamon.theme', 'name'],
                capture_output=True, text=True, timeout=0.5
            )
            theme = result.stdout.strip().strip("'").lower()
            if 'dark' in theme or 'noir' in theme or 'black' in theme:
                return True
            
            # Проверяем GTK тему
            result = subprocess.run(
                ['gsettings', 'get', 'org.cinnamon.desktop.interface', 'gtk-theme'],
                capture_output=True, text=True, timeout=0.5
            )
            theme = result.stdout.strip().strip("'").lower()
            return 'dark' in theme or 'noir' in theme or 'black' in theme
        except Exception:
            return True  # По умолчанию тёмная
    
    def show_with_rofi(self):
        """Показать список в rofi"""
        items = self.get_history()
        
        if not items:
            print("История пуста")
            return None
        
        # Форматируем для rofi
        rofi_input = '\n'.join(self.format_item(item) for item in items)
        
        # Определяем тему
        is_dark = self.is_dark_theme()
        
        # Параметры масштабирования
        scale = self.config.get('ui_scale', 1.0)
        window_width = int(self.config.get('window_width', 600) * scale)
        font_size = int(self.config.get('font_size', 11) * scale)
        element_padding = int(self.config.get('element_padding', 10) * scale)
        header_font_size = int(font_size * 1.1)  # Заголовок чуть крупнее
        
        # Базовые параметры
        rofi_args = [
            'rofi',
            '-dmenu',
            '-i',
            '-format', 's',
            '-no-custom',
            '-mesg', '📋 История буфера обмена',
            '-theme-str', f'window {{ width: {window_width}px; border: 2px; border-radius: 8px; }}',
            '-theme-str', 'inputbar { enabled: false; }',  # Скрываем строку поиска
            '-theme-str', f'message {{ enabled: true; padding: {element_padding}px; border: 0; font: "Sans Bold {header_font_size}"; }}',
            '-theme-str', 'listview { lines: 10; scrollbar: false; }',
            '-theme-str', f'element {{ padding: {element_padding}px 15px; border-radius: 4px; }}',
            '-theme-str', f'element-text {{ font: "Sans {font_size}"; }}',
        ]
        
        # Применяем цветовую схему в зависимости от темы
        if is_dark:
            rofi_args.extend([
                '-theme-str', 'window { background-color: #2b2b2b; border-color: #404040; }',
                '-theme-str', 'mainbox { background-color: #2b2b2b; }',
                '-theme-str', 'message { background-color: #2b2b2b; text-color: #ffffff; }',
                '-theme-str', 'listview { background-color: #2b2b2b; }',
                '-theme-str', 'element { background-color: #2b2b2b; text-color: #e0e0e0; }',
                '-theme-str', 'element selected { background-color: #404040; text-color: #ffffff; }',
            ])
        else:
            rofi_args.extend([
                '-theme-str', 'window { background-color: #ffffff; border-color: #cccccc; }',
                '-theme-str', 'mainbox { background-color: #ffffff; }',
                '-theme-str', 'message { background-color: #ffffff; text-color: #000000; }',
                '-theme-str', 'listview { background-color: #ffffff; }',
                '-theme-str', 'element { background-color: #ffffff; text-color: #333333; }',
                '-theme-str', 'element selected { background-color: #e0e0e0; text-color: #000000; }',
            ])
        
        try:
            result = subprocess.run(
                rofi_args,
                input=rofi_input, text=True, capture_output=True, timeout=30
            )
            
            if result.returncode != 0:
                return None
            
            # Парсим выбор
            selected = result.stdout.strip()
            if not selected:
                return None
            
            item_id = int(selected.split('|')[0])
            return item_id
            
        except Exception as e:
            print(f"⚠️  Ошибка rofi: {e}")
            return None
    
    def restore_to_clipboard(self, item_id):
        """Восстановить элемент в clipboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT mime_type, content_path, preview FROM items WHERE id = ?',
            (item_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return False
        
        mime_type, content_path, preview = row
        
        # Определяем что вставлять
        if content_path:
            # Читаем из файла
            with open(content_path, 'rb') as f:
                content = f.read()
        else:
            # Текст из preview
            content = preview.encode('utf-8')
        
        # Помещаем в clipboard
        try:
            subprocess.run(
                ['xclip', '-selection', 'clipboard', '-t', mime_type],
                input=content, timeout=1.0, stderr=subprocess.DEVNULL
            )
            return True
        except Exception as e:
            if self.config.get('debug'):
                print(f"⚠️  Ошибка вставки: {e}")
            return False
    
    def auto_paste(self):
        """Автоматически эмулировать Ctrl+V"""
        try:
            subprocess.run(
                ['xdotool', 'key', 'ctrl+v'],
                timeout=1.0, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass
    
    def run(self):
        """Показать UI и обработать выбор"""
        item_id = self.show_with_rofi()
        
        if item_id is None:
            sys.exit(0)
        
        if self.restore_to_clipboard(item_id):
            if self.config.get('auto_paste', True):
                self.auto_paste()

if __name__ == '__main__':
    ui = ClipShow()
    ui.run()
