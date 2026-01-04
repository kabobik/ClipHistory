#!/usr/bin/env python3
"""
ClipHistory GTK UI - окно с превью изображений
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf

import subprocess
import sqlite3
import json
from pathlib import Path
from PIL import Image

class ClipHistoryWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="История буфера обмена")
        self.cache_dir = Path.home() / '.cache' / 'cliphistory'
        self.db_path = self.cache_dir / 'history.db'
        self.config = self.load_config()
        
        # Настройки окна
        self.set_default_size(800, 500)
        self.set_border_width(0)
        self.set_decorated(True)
        self.set_resizable(True)
        
        # Позиционируем у курсора
        self.position_near_cursor()
        
        # Применяем тему
        self.apply_theme()
        
        # Создаём UI
        self.create_ui()
        
        # Загружаем данные
        self.load_history()
        
        # Обработчики
        self.connect("key-press-event", self.on_key_press)
        
    def load_config(self):
        """Загрузка конфигурации"""
        config_path = Path(__file__).parent / 'config.json'
        try:
            with open(config_path) as f:
                return json.load(f)
        except Exception:
            return {'auto_paste': True, 'ui_scale': 1.0}
    
    def position_near_cursor(self):
        """Позиционировать окно рядом с курсором"""
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
            x, y = pos.get('X', 100), pos.get('Y', 100)
            self.move(x - 400, max(50, y - 250))  # Центрируем относительно курсора
        except Exception:
            pass
    
    def apply_theme(self):
        """Применить тёмную/светлую тему"""
        is_dark = self.is_dark_theme()
        
        css = f"""
        window {{
            background-color: {'#2b2b2b' if is_dark else '#ffffff'};
        }}
        
        .header {{
            background-color: {'#333333' if is_dark else '#f5f5f5'};
            color: {'#ffffff' if is_dark else '#000000'};
            padding: 12px;
            font-weight: bold;
            font-size: 14px;
        }}
        
        .list-item {{
            background-color: {'#2b2b2b' if is_dark else '#ffffff'};
            color: {'#e0e0e0' if is_dark else '#333333'};
            padding: 8px;
            border-bottom: 1px solid {'#404040' if is_dark else '#e0e0e0'};
        }}
        
        .list-item:hover {{
            background-color: {'#404040' if is_dark else '#f0f0f0'};
        }}
        
        .list-item:selected {{
            background-color: {'#4a9eff' if is_dark else '#0066cc'};
            color: #ffffff;
        }}
        
        .preview-text {{
            font-size: 13px;
        }}
        
        .item-type {{
            font-size: 11px;
            opacity: 0.7;
        }}
        """
        
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
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
    
    def create_ui(self):
        """Создать интерфейс"""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)
        
        # Заголовок
        header = Gtk.Label(label="📋 История буфера обмена")
        header.get_style_context().add_class('header')
        header.set_xalign(0)
        vbox.pack_start(header, False, False, 0)
        
        # Скроллируемый список
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        vbox.pack_start(scrolled, True, True, 0)
        
        # ListBox для элементов
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect('row-activated', self.on_item_activated)
        scrolled.add(self.listbox)
    
    def create_thumbnail(self, image_path, size=64):
        """Создать миниатюру изображения"""
        try:
            img = Image.open(image_path)
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            
            # Конвертируем в GdkPixbuf
            img_bytes = img.tobytes()
            width, height = img.size
            pixbuf = GdkPixbuf.Pixbuf.new_from_data(
                img_bytes,
                GdkPixbuf.Colorspace.RGB,
                'A' in img.mode,  # has_alpha
                8,  # bits_per_sample
                width, height,
                width * len(img.mode)  # rowstride
            )
            return pixbuf
        except Exception:
            return None
    
    def load_history(self):
        """Загрузить историю из БД"""
        if not self.db_path.exists():
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, mime_type, content_path, preview 
            FROM items 
            ORDER BY timestamp DESC
            LIMIT 50
        ''')
        items = cursor.fetchall()
        conn.close()
        
        for item_id, mime_type, content_path, preview in items:
            row = self.create_list_row(item_id, mime_type, content_path, preview)
            self.listbox.add(row)
    
    def create_list_row(self, item_id, mime_type, content_path, preview):
        """Создать строку списка"""
        row = Gtk.ListBoxRow()
        row.item_id = item_id
        row.mime_type = mime_type
        row.content_path = content_path
        row.preview = preview
        
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        hbox.set_margin_start(8)
        hbox.set_margin_end(8)
        hbox.set_margin_top(6)
        hbox.set_margin_bottom(6)
        
        # Иконка или превью
        if mime_type.startswith('image/') and content_path:
            # Миниатюра изображения
            pixbuf = self.create_thumbnail(content_path, 48)
            if pixbuf:
                image = Gtk.Image.new_from_pixbuf(pixbuf)
            else:
                image = Gtk.Image.new_from_icon_name('image-x-generic', Gtk.IconSize.DIALOG)
        elif mime_type.startswith('text/html'):
            image = Gtk.Image.new_from_icon_name('text-html', Gtk.IconSize.DIALOG)
        elif mime_type.startswith('text/uri-list'):
            image = Gtk.Image.new_from_icon_name('folder', Gtk.IconSize.DIALOG)
        else:
            image = Gtk.Image.new_from_icon_name('text-x-generic', Gtk.IconSize.DIALOG)
        
        hbox.pack_start(image, False, False, 0)
        
        # Текст
        vbox_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        # Preview
        preview_label = Gtk.Label(label=preview[:100])
        preview_label.set_xalign(0)
        preview_label.set_ellipsize(3)  # END
        preview_label.get_style_context().add_class('preview-text')
        vbox_text.pack_start(preview_label, False, False, 0)
        
        # Тип
        type_label = Gtk.Label(label=mime_type)
        type_label.set_xalign(0)
        type_label.get_style_context().add_class('item-type')
        vbox_text.pack_start(type_label, False, False, 0)
        
        hbox.pack_start(vbox_text, True, True, 0)
        
        row.add(hbox)
        return row
    
    def on_item_activated(self, listbox, row):
        """Обработка выбора элемента"""
        self.restore_to_clipboard(row.item_id, row.mime_type, row.content_path, row.preview)
        
        if self.config.get('auto_paste', True):
            self.auto_paste()
        
        self.close()
    
    def restore_to_clipboard(self, item_id, mime_type, content_path, preview):
        """Восстановить элемент в clipboard"""
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
        """Автоматически эмулировать Ctrl+V"""
        try:
            subprocess.run(
                ['xdotool', 'key', 'ctrl+v'],
                timeout=1.0, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass
    
    def on_key_press(self, widget, event):
        """Обработка клавиш"""
        if event.keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

def main():
    win = ClipHistoryWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == '__main__':
    main()
