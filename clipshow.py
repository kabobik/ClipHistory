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
        
        # Ограничиваем длину preview
        if len(preview) > 100:
            preview = preview[:97] + '...'
        
        # Заменяем переносы строк на пробелы
        preview = preview.replace('\n', ' ').replace('\r', '')
        
        return f"{item_id}|{preview}"
    
    def show_with_rofi(self):
        """Показать список в rofi"""
        items = self.get_history()
        
        if not items:
            print("История пуста")
            return None
        
        # Форматируем для rofi
        rofi_input = '\n'.join(self.format_item(item) for item in items)
        
        try:
            result = subprocess.run(
                ['rofi', '-dmenu', '-i', '-p', 'History', '-format', 's'],
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
