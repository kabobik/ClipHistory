#!/usr/bin/env python3
"""
ClipHistory - Универсальный менеджер истории буфера обмена
Демон, следящий за изменениями clipboard и сохраняющий историю
"""

import subprocess
import time
import json
import sqlite3
import os
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

# Приоритет MIME типов (от высшего к низшему)
MIME_PRIORITY = [
    'text/plain;charset=utf-8',
    'text/plain',
    'UTF8_STRING',
    'STRING',
    'TEXT',
    'image/png',
    'image/jpeg',
    'image/jpg',
    'image/bmp',
    'text/html',
    'text/uri-list',
]

class ClipHistory:
    def __init__(self):
        self.cache_dir = Path.home() / '.cache' / 'cliphistory'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.images_dir = self.cache_dir / 'images'
        self.images_dir.mkdir(exist_ok=True)
        
        self.other_dir = self.cache_dir / 'other'
        self.other_dir.mkdir(exist_ok=True)
        
        self.db_path = self.cache_dir / 'history.db'
        self.config = self.load_config()
        
        self.init_db()
        self.last_hash = None
        
    def load_config(self):
        """Загрузка конфигурации"""
        config_path = Path(__file__).parent / 'config.json'
        try:
            with open(config_path) as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Ошибка загрузки конфига: {e}")
            return {
                'max_text_items': 50,
                'max_image_items': 10,
                'max_other_items': 20,
                'check_interval': 0.3,
                'cleanup_days': 7,
                'debug': False
            }
    
    def init_db(self):
        """Инициализация БД"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                mime_type TEXT NOT NULL,
                content_path TEXT,
                preview TEXT,
                hash TEXT UNIQUE
            )
        ''')
        conn.commit()
        conn.close()
        
    def get_available_targets(self):
        """Получить список доступных MIME типов в clipboard"""
        try:
            result = subprocess.run(
                ['xclip', '-o', '-selection', 'clipboard', '-t', 'TARGETS'],
                capture_output=True, timeout=0.5, text=True
            )
            return result.stdout.strip().split('\n')
        except Exception:
            return []
    
    def select_best_mime(self, available_targets):
        """Выбрать лучший MIME тип из доступных"""
        for mime in MIME_PRIORITY:
            if mime in available_targets:
                return mime
        
        # Если ничего не подошло, берём первый image/* или text/*
        for target in available_targets:
            if target.startswith(('image/', 'text/')):
                return target
        
        # Совсем неизвестный формат
        return available_targets[0] if available_targets else None
    
    def get_clipboard_content(self, mime_type):
        """Получить содержимое clipboard для заданного MIME типа"""
        try:
            result = subprocess.run(
                ['xclip', '-o', '-selection', 'clipboard', '-t', mime_type],
                capture_output=True, timeout=1.0
            )
            return result.stdout
        except Exception as e:
            if self.config.get('debug'):
                print(f"⚠️  Ошибка чтения clipboard: {e}")
            return None
    
    def compute_hash(self, content):
        """Вычислить хэш содержимого"""
        return hashlib.sha256(content).hexdigest()[:16]
    
    def save_item(self, mime_type, content, preview):
        """Сохранить элемент в историю"""
        content_hash = self.compute_hash(content)
        
        # Проверяем, не дубликат ли это
        if content_hash == self.last_hash:
            return
        
        self.last_hash = content_hash
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Проверяем есть ли уже такой элемент
        cursor.execute('SELECT id FROM items WHERE hash = ?', (content_hash,))
        if cursor.fetchone():
            conn.close()
            return
        
        content_path = None
        
        # Определяем как сохранять
        if mime_type.startswith('image/'):
            # Сохраняем изображение в файл
            ext = mime_type.split('/')[-1]
            if ext not in ['png', 'jpg', 'jpeg', 'bmp', 'gif']:
                ext = 'png'
            content_path = str(self.images_dir / f"{content_hash}.{ext}")
            with open(content_path, 'wb') as f:
                f.write(content)
        elif mime_type.startswith('text/') and not mime_type.startswith('text/plain'):
            # HTML, uri-list и т.д. - сохраняем как текст в preview
            preview = content.decode('utf-8', errors='ignore')[:500]
        elif not mime_type.startswith('text/'):
            # Неизвестный формат - сохраняем в файл
            content_path = str(self.other_dir / f"{content_hash}.bin")
            with open(content_path, 'wb') as f:
                f.write(content)
        
        # Сохраняем в БД
        try:
            cursor.execute(
                'INSERT INTO items (mime_type, content_path, preview, hash) VALUES (?, ?, ?, ?)',
                (mime_type, content_path, preview, content_hash)
            )
            conn.commit()
            
            if self.config.get('debug'):
                print(f"✓ Сохранено: {mime_type} ({len(content)} bytes)")
        except sqlite3.IntegrityError:
            pass  # Дубликат
        finally:
            conn.close()
        
        # Очистка старых элементов
        self.cleanup()
    
    def cleanup(self):
        """Очистка старых элементов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Лимиты по типам
        limits = {
            'text': self.config['max_text_items'],
            'image': self.config['max_image_items'],
            'other': self.config['max_other_items']
        }
        
        for mime_prefix, limit in [('text/', 'text'), ('image/', 'image')]:
            cursor.execute('''
                DELETE FROM items WHERE id IN (
                    SELECT id FROM items 
                    WHERE mime_type LIKE ? 
                    ORDER BY timestamp DESC 
                    LIMIT -1 OFFSET ?
                )
            ''', (f'{mime_prefix}%', limits[limit]))
        
        # Удаляем файлы старше N дней
        cutoff = datetime.now() - timedelta(days=self.config['cleanup_days'])
        cursor.execute(
            'SELECT content_path FROM items WHERE timestamp < ? AND content_path IS NOT NULL',
            (cutoff,)
        )
        for (path,) in cursor.fetchall():
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass
        
        cursor.execute('DELETE FROM items WHERE timestamp < ?', (cutoff,))
        conn.commit()
        conn.close()
    
    def check_clipboard(self):
        """Проверить clipboard на изменения"""
        targets = self.get_available_targets()
        if not targets or targets == ['']:
            return
        
        mime_type = self.select_best_mime(targets)
        if not mime_type:
            return
        
        content = self.get_clipboard_content(mime_type)
        if not content:
            return
        
        # Создаём preview
        if mime_type.startswith('text/'):
            preview = content.decode('utf-8', errors='ignore')[:150]
        elif mime_type.startswith('image/'):
            preview = f"[IMG] {len(content)} bytes"
        else:
            preview = f"[{mime_type}] {len(content)} bytes"
        
        self.save_item(mime_type, content, preview)
    
    def run(self):
        """Основной цикл демона"""
        print("🚀 ClipHistory запущен")
        print(f"📁 Кэш: {self.cache_dir}")
        print(f"⏱️  Проверка каждые {self.config['check_interval']}s")
        print("💡 Нажмите Ctrl+C для выхода")
        print("-" * 50)
        
        try:
            while True:
                self.check_clipboard()
                time.sleep(self.config['check_interval'])
        except KeyboardInterrupt:
            print("\n👋 Выход...")

if __name__ == '__main__':
    daemon = ClipHistory()
    daemon.run()
