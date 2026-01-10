#!/usr/bin/env python3
"""
ClipHistory - Универсальный менеджер истории буфера обмена
Рефакторенная версия с чёткой архитектурой
"""

import subprocess
import time
import json
import sqlite3
import hashlib
import threading
import signal
import sys
from pathlib import Path
from datetime import datetime, timedelta

try:
    from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
    from PyQt5.QtGui import QIcon, QPixmap, QPainter
    from PyQt5.QtCore import Qt, QByteArray
    from PyQt5.QtSvg import QSvgRenderer
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

try:
    from Xlib import X, XK, display
    from Xlib.ext import record
    from Xlib.protocol import rq
    XLIB_AVAILABLE = True
except ImportError:
    XLIB_AVAILABLE = False
    print("⚠️  python-xlib не установлен: pip3 install python-xlib")

# Приоритет MIME типов
MIME_PRIORITY = [
    'text/plain;charset=utf-8', 'text/plain', 'UTF8_STRING', 'STRING', 'TEXT',
    'image/png', 'image/jpeg', 'image/jpg', 'image/bmp',
    'text/html', 'text/uri-list',
]


class ClipboardMonitor:
    """Мониторинг буфера обмена и сохранение истории"""
    
    def __init__(self, config):
        self.config = config
        self.cache_dir = Path.home() / '.cache' / 'cliphistory'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.images_dir = self.cache_dir / 'images'
        self.images_dir.mkdir(exist_ok=True)
        
        self.other_dir = self.cache_dir / 'other'
        self.other_dir.mkdir(exist_ok=True)
        
        self.db_path = self.cache_dir / 'history.db'
        self.last_content_hash = None
        self.init_db()
    
    def init_db(self):
        """Инициализация БД с миграцией"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                mime_type TEXT,
                content_path TEXT,
                preview TEXT,
                hash TEXT UNIQUE
            )
        ''')
        
        # Миграция: добавляем pinned если нет
        cursor.execute("PRAGMA table_info(items)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'pinned' not in columns:
            cursor.execute('ALTER TABLE items ADD COLUMN pinned INTEGER DEFAULT 0')
            if self.config.get('debug'):
                print("✓ Добавлена колонка 'pinned'")
        
        conn.commit()
        conn.close()
    
    def get_clipboard(self):
        """Получить содержимое буфера обмена с определением MIME"""
        try:
            result = subprocess.run(
                ['xclip', '-selection', 'clipboard', '-t', 'TARGETS', '-o'],
                capture_output=True, text=True, timeout=1
            )
            available_types = result.stdout.strip().split('\n')
            
            # Выбираем лучший MIME тип
            mime_type = None
            for preferred in MIME_PRIORITY:
                if preferred in available_types:
                    mime_type = preferred
                    break
            
            if not mime_type and available_types:
                mime_type = available_types[0]
            
            if not mime_type:
                return None, None
            
            # Получаем контент
            result = subprocess.run(
                ['xclip', '-selection', 'clipboard', '-t', mime_type, '-o'],
                capture_output=True, timeout=1
            )
            
            return mime_type, result.stdout
        except Exception as e:
            if self.config.get('debug'):
                print(f"Ошибка чтения clipboard: {e}")
            return None, None
    
    def save_to_history(self, mime_type, content):
        """Сохранить в историю"""
        if not content:
            return
        
        # Хеш для дедупликации
        content_hash = hashlib.md5(content).hexdigest()
        if content_hash == self.last_content_hash:
            return
        
        self.last_content_hash = content_hash
        
        # Обработка по типу
        if mime_type.startswith('image/'):
            self._save_image(mime_type, content, content_hash)
        elif mime_type.startswith('text/'):
            self._save_text(mime_type, content, content_hash)
        else:
            self._save_other(mime_type, content, content_hash)
    
    def _save_text(self, mime_type, content, content_hash):
        """Сохранить текст"""
        try:
            text = content.decode('utf-8', errors='ignore')
            preview = text[:200]
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO items (timestamp, mime_type, content_path, preview, hash)
                VALUES (?, ?, NULL, ?, ?)
            ''', (time.time(), mime_type, preview, content_hash))
            conn.commit()
            conn.close()
        except Exception as e:
            if self.config.get('debug'):
                print(f"Ошибка сохранения текста: {e}")
    
    def _save_image(self, mime_type, content, content_hash):
        """Сохранить изображение"""
        try:
            ext = '.png' if 'png' in mime_type else '.jpg'
            file_path = self.images_dir / f"{content_hash}{ext}"
            
            with open(file_path, 'wb') as f:
                f.write(content)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO items (timestamp, mime_type, content_path, preview, hash)
                VALUES (?, ?, ?, '', ?)
            ''', (time.time(), mime_type, str(file_path), content_hash))
            conn.commit()
            conn.close()
        except Exception as e:
            if self.config.get('debug'):
                print(f"Ошибка сохранения изображения: {e}")
    
    def _save_other(self, mime_type, content, content_hash):
        """Сохранить другие типы"""
        try:
            file_path = self.other_dir / content_hash
            with open(file_path, 'wb') as f:
                f.write(content)
            
            preview = content.decode('utf-8', errors='ignore')[:200]
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO items (timestamp, mime_type, content_path, preview, hash)
                VALUES (?, ?, ?, ?, ?)
            ''', (time.time(), mime_type, str(file_path), preview, content_hash))
            conn.commit()
            conn.close()
        except Exception as e:
            if self.config.get('debug'):
                print(f"Ошибка сохранения: {e}")
    
    def cleanup_old(self):
        """Очистка старых элементов"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            days = self.config.get('cleanup_days', 7)
            cutoff = time.time() - (days * 24 * 3600)
            
            # Удаляем незакрепленные старые элементы
            cursor.execute('SELECT content_path FROM items WHERE timestamp < ? AND pinned = 0', (cutoff,))
            for (path,) in cursor.fetchall():
                if path and Path(path).exists():
                    Path(path).unlink()
            
            cursor.execute('DELETE FROM items WHERE timestamp < ? AND pinned = 0', (cutoff,))
            
            # Лимиты по типам
            for mime_prefix, max_items in [('text/', 'max_text_items'), ('image/', 'max_image_items')]:
                limit = self.config.get(max_items, 50)
                cursor.execute(f'''
                    DELETE FROM items WHERE id IN (
                        SELECT id FROM items 
                        WHERE mime_type LIKE ? AND pinned = 0
                        ORDER BY timestamp DESC 
                        LIMIT -1 OFFSET ?
                    )
                ''', (f'{mime_prefix}%', limit))
            
            conn.commit()
            conn.close()
        except Exception as e:
            if self.config.get('debug'):
                print(f"Ошибка очистки: {e}")
    
    def monitor_loop(self):
        """Основной цикл мониторинга"""
        interval = self.config.get('check_interval', 0.3)
        cleanup_counter = 0
        
        while True:
            mime_type, content = self.get_clipboard()
            if mime_type and content:
                self.save_to_history(mime_type, content)
            
            cleanup_counter += 1
            if cleanup_counter >= 100:  # Каждые 30 секунд
                self.cleanup_old()
                cleanup_counter = 0
            
            time.sleep(interval)


class HotkeyManager:
    """Управление горячими клавишами и запуском UI через python-xlib"""
    
    def __init__(self, config, script_path):
        self.config = config
        self.script_path = script_path
        self.ui_process = None
        self.display = None
        self.root = None
    
    def is_ui_running(self):
        """Проверка запущен ли UI (через lock-файл)"""
        lock_file = Path.home() / '.cache' / 'cliphistory' / '.ui.lock'
        
        if not lock_file.exists():
            return False
        
        # Проверяем что процесс с PID из lock-файла существует
        try:
            with open(lock_file) as f:
                pid = int(f.read().strip())
            # Проверяем существование процесса
            import os
            os.kill(pid, 0)
            return True  # Процесс существует и окно открыто
        except (ProcessLookupError, ValueError, FileNotFoundError):
            # Процесс не существует или файл битый - окно закрыто
            try:
                lock_file.unlink()
            except:
                pass
            return False
        self.keyboards_grabbed = False
        if self.config.get('debug'):
            print("🔓 Клавиатуры отпущены")
    
    def launch_ui(self):
        """Запустить UI окно"""
        if self.is_ui_running():
            if self.config.get('debug'):
                print("⏭️  UI уже запущен, пропускаем")
            return
        
        try:
            ui_script = self.script_path.parent / 'clipshow_qt.py'
            self.ui_process = subprocess.Popen(
                ['python3', str(ui_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            if self.config.get('debug'):
                print(f"🚀 UI запущен (PID: {self.ui_process.pid})")
        except Exception as e:
            if self.config.get('debug'):
                print(f"Ошибка запуска UI: {e}")
    
    def monitor_hotkey(self):
        """Мониторинг горячих клавиш через python-xlib"""
        if not XLIB_AVAILABLE:
            print("❌ python-xlib не доступен, используйте: pip3 install python-xlib")
            return
        
        try:
            # Подключаемся к X display
            self.display = display.Display()
            self.root = self.display.screen().root
            
            # Получаем keycode для 'v'
            v_keycode = self.display.keysym_to_keycode(XK.string_to_keysym('v'))
            
            # Пытаемся зарегистрировать Super+V (Mod4Mask = Super)
            try:
                self.root.grab_key(
                    v_keycode,
                    X.Mod4Mask,  # Super key
                    True,  # owner_events
                    X.GrabModeAsync,
                    X.GrabModeAsync
                )
                
                # Синхронизируем с X server чтобы поймать ошибки
                self.display.sync()
                
                print(f"✅ Хоткей Super+V зарегистрирован через XGrabKey")
                
            except Exception as grab_error:
                print(f"❌ Не удалось зарегистрировать Super+V: {grab_error}")
                print(f"⚠️  Возможно хоткей уже занят системой (проверьте Settings → Keyboard → Shortcuts)")
                print(f"💡 Попробуйте освободить Super+V в настройках системы")
                return
            
            # Слушаем события
            print("🎧 Ожидаем нажатия Super+V...")
            while True:
                event = self.display.next_event()
                
                # Проверяем статус UI
                if self.ui_process and self.ui_process.poll() is not None:
                    self.ui_process = None
                
                # KeyPress event
                if event.type == X.KeyPress:
                    # Проверяем что это Super+V
                    if event.detail == v_keycode and (event.state & X.Mod4Mask):
                        if self.config.get('debug'):
                            print("⌨️  Super+V нажат!")
                        if not self.is_ui_running():
                            self.launch_ui()
        
        except Exception as e:
            print(f"❌ Ошибка мониторинга хоткея: {e}")
            import traceback
            traceback.print_exc()
        
        try:
            # Находим клавиатуры
            for path in list_devices():
                dev = InputDevice(path)
                caps = dev.capabilities()
                if ecodes.EV_KEY in caps and ecodes.KEY_LEFTMETA in caps.get(ecodes.EV_KEY, []):
                    self.devices.append(dev)
            
            if not self.devices:
                print("⚠️  Клавиатуры не найдены")
                return
            
            print(f"⌨️  Мониторинг {len(self.devices)} клавиатур для Super+V")
            
            # Состояние клавиш
            super_pressed = False
            
            # Селектор для всех устройств
            sel = selectors.DefaultSelector()
            for dev in self.devices:
                sel.register(dev, selectors.EVENT_READ)
            
            while True:
                current_time = time.time()
                
                # Проверяем статус UI
                if self.ui_process and self.ui_process.poll() is not None:
                    self.ui_process = None
                    self.ui_launched_flag = False
                
                # Проверяем нужно ли отпустить клавиатуры (через 300мс после отпускания Super)
                if self.keyboards_grabbed and self.ungrab_time > 0 and current_time >= self.ungrab_time:
                    self.ungrab_keyboards()
                    self.ungrab_time = 0
                
                for key, _ in sel.select(timeout=0.05):
                    dev = key.fileobj
                    for event in dev.read():
                        if event.type == ecodes.EV_KEY:
                            # Super key
                            if event.code in [ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA]:
                                if event.value == 1:  # Нажали Super
                                    super_pressed = True
                                elif event.value == 0:  # Отпустили Super
                                    super_pressed = False
                                    self.ui_launched_flag = False
                            
                            # V key - запуск UI при Super+V
                            elif event.code == ecodes.KEY_V and event.value == 1:
                                if super_pressed and not self.ui_launched_flag:
                                    # Запускаем UI
                                    self.launch_ui()
                                    self.ui_launched_flag = True
                                    
                                    # Удаляем символ 'v' через xdotool с небольшой задержкой
                                    def delete_v():
                                        time.sleep(0.05)
                                        try:
                                            subprocess.run(['xdotool', 'key', 'BackSpace'], 
                                                         timeout=0.5, check=False, 
                                                         stdout=subprocess.DEVNULL, 
                                                         stderr=subprocess.DEVNULL)
                                        except:
                                            pass
                                    
                                    threading.Thread(target=delete_v, daemon=True).start()
        
        except Exception as e:
            print(f"Ошибка hotkey: {e}")
        finally:
            # Обязательно отпускаем клавиатуры при выходе
            self.ungrab_keyboards()


class ClipHistoryDaemon:
    """Главный класс демона"""
    
    def __init__(self):
        self.script_path = Path(__file__).resolve()
        self.config = self.load_config()
        
        self.clipboard_monitor = ClipboardMonitor(self.config)
        self.hotkey_manager = HotkeyManager(self.config, self.script_path)
        
        # Qt приложение для трея
        self.app = None
        self.tray_icon = None
        self.tray_menu = None
        
        # Обработчик сигналов для корректного завершения
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Обработка сигналов завершения"""
        print("\n⚠️  Получен сигнал завершения...")
        if self.app:
            self.app.quit()
        sys.exit(0)
    
    def create_tray_icon(self):
        """Создать иконку в системном трее"""
        if not PYQT_AVAILABLE or not QSystemTrayIcon.isSystemTrayAvailable():
            return False
        
        # Определяем тему панели через gsettings
        is_dark_panel = True  # По умолчанию темная
        try:
            import subprocess
            import re
            result = subprocess.run(
                ['gsettings', 'get', 'org.cinnamon.desktop.interface', 'gtk-theme'],
                capture_output=True, text=True, timeout=1
            )
            if result.returncode == 0:
                theme_name = result.stdout.strip().strip("'")
                theme_path = Path(f'/usr/share/themes/{theme_name}/gtk-3.0/gtk.css')
                if theme_path.exists():
                    content = theme_path.read_text()
                    match = re.search(r'@define-color\s*(?:theme_bg_color|bg_color)\s*#([0-9a-fA-F]{6});', content)
                    if match:
                        hex_color = match.group(1)
                        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                        is_dark_panel = (r + g + b) / 3 < 128
        except:
            pass
        
        # Выбираем цвет иконки в зависимости от темы панели
        icon_color = '#ffffff' if is_dark_panel else '#2b2b2b'
        
        # SVG иконка с адаптивным цветом
        svg_data = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <path fill="{icon_color}" d="M19 3H14.82C14.4 1.84 13.3 1 12 1S9.6 1.84 9.18 3H5C3.9 3 3 3.9 3 5V19C3 20.1 3.9 21 5 21H19C20.1 21 21 20.1 21 19V5C21 3.9 20.1 3 19 3M12 3C12.55 3 13 3.45 13 4S12.55 5 12 5 11 4.55 11 4 11.45 3 12 3M7 7H17V5H19V19H5V5H7V7M7 9V11H17V9H7M7 13V15H17V13H7Z" />
        </svg>'''
        
        renderer = QSvgRenderer(QByteArray(svg_data.encode()))
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        self.tray_icon = QSystemTrayIcon(QIcon(pixmap))
        self.tray_icon.setToolTip('ClipHistory - Демон активен')
        
        # Меню трея (сохраняем как атрибут!)
        self.tray_menu = QMenu()
        
        # Стиль темного меню
        self.tray_menu.setStyleSheet("""
            QMenu {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 8px 0px;
            }
            QMenu::item {
                padding: 8px 32px 8px 16px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #0078d4;
                border-radius: 4px;
                margin: 0px 4px;
            }
            QMenu::item:pressed {
                background-color: #0063b1;
            }
            QMenu::separator {
                height: 1px;
                background-color: #404040;
                margin: 4px 8px;
            }
        """)
        
        show_action = QAction('Открыть историю', self.tray_menu)
        show_action.triggered.connect(self.launch_ui)
        self.tray_menu.addAction(show_action)
        
        self.tray_menu.addSeparator()
        
        # Подменю масштабирования
        scale_menu = QMenu('Масштаб интерфейса', self.tray_menu)
        scale_menu.setStyleSheet(self.tray_menu.styleSheet())
        
        # Создаем группу для радио-кнопок (взаимоисключающий выбор)
        from PyQt5.QtWidgets import QActionGroup
        scale_group = QActionGroup(scale_menu)
        scale_group.setExclusive(True)
        
        current_scale = self.config.get('ui_scale', 1.5)
        
        for scale_value in [1.0, 1.25, 1.5, 2.0]:
            scale_action = QAction(f'{scale_value}x', scale_menu)
            scale_action.setCheckable(True)
            scale_action.setActionGroup(scale_group)  # Добавляем в группу
            if abs(current_scale - scale_value) < 0.01:
                scale_action.setChecked(True)
            scale_action.triggered.connect(lambda checked, s=scale_value: self.change_ui_scale(s))
            scale_menu.addAction(scale_action)
        
        self.tray_menu.addMenu(scale_menu)
        
        self.tray_menu.addSeparator()
        
        quit_action = QAction('Выход', self.tray_menu)
        quit_action.triggered.connect(self.quit_daemon)
        self.tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_clicked)
        self.tray_icon.show()
        
        print("📌 Иконка в трее создана")
        return True
    
    def on_tray_clicked(self, reason):
        """Обработка клика по трею"""
        if reason == QSystemTrayIcon.Trigger:  # Левый клик
            self.launch_ui()
    
    def launch_ui(self):
        """Запустить UI"""
        self.hotkey_manager.launch_ui()
    
    def change_ui_scale(self, scale):
        """Изменить масштаб интерфейса"""
        try:
            # Обновляем конфигурацию
            self.config['ui_scale'] = scale
            
            # Сохраняем в файл
            config_path = self.script_path.parent / 'config.json'
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            # Показываем уведомление через трей
            if self.tray_icon:
                self.tray_icon.showMessage(
                    'Масштаб изменен',
                    f'Масштаб интерфейса установлен на {scale}x.\nИзменения вступят в силу при следующем открытии окна.',
                    QSystemTrayIcon.Information,
                    3000
                )
            
            if self.config.get('debug'):
                print(f"✅ Масштаб изменен на {scale}x")
        except Exception as e:
            if self.config.get('debug'):
                print(f"Ошибка изменения масштаба: {e}")
    
    def quit_daemon(self):
        """Выход из демона"""
        print("\n👋 Завершение работы через трей...")
        if self.tray_icon:
            self.tray_icon.hide()
        if self.app:
            self.app.quit()
        sys.exit(0)
    
    def load_config(self):
        """Загрузка конфигурации"""
        config_path = self.script_path.parent / 'config.json'
        try:
            with open(config_path) as f:
                return json.load(f)
        except Exception:
            return {
                'check_interval': 0.3,
                'cleanup_days': 7,
                'auto_paste': True,
                'hotkey': 'Super+V',
                'debug': False
            }
    
    def run(self):
        """Запуск демона"""
        print("🚀 ClipHistory запущен")
        print(f"📁 Кэш: {self.clipboard_monitor.cache_dir}")
        print(f"⏱️  Проверка каждые {self.config.get('check_interval', 0.3)}s")
        print(f"⌨️  Горячая клавиша: {self.config.get('hotkey', 'Super+V')}")
        print("💡 Нажмите Ctrl+C для выхода")
        
        # Инициализируем Qt приложение для трея
        if PYQT_AVAILABLE:
            self.app = QApplication(sys.argv)
            self.app.setQuitOnLastWindowClosed(False)  # Не закрывать при закрытии окон
            
            if self.create_tray_icon():
                # Запускаем мониторинг буфера в отдельном потоке
                clipboard_thread = threading.Thread(
                    target=self.clipboard_monitor.monitor_loop,
                    daemon=True
                )
                clipboard_thread.start()
                
                # Запускаем event loop Qt (блокирующий)
                try:
                    sys.exit(self.app.exec_())
                except KeyboardInterrupt:
                    print("\n👋 Завершение работы...")
                    self.app.quit()
            else:
                print("⚠️  Не удалось создать трей, работаем без него")
                # Fallback без трея
                clipboard_thread = threading.Thread(
                    target=self.clipboard_monitor.monitor_loop,
                    daemon=True
                )
                clipboard_thread.start()
                
                # Простой цикл ожидания
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\n👋 Завершение работы...")
        else:
            print("⚠️  PyQt5 не доступен, работаем без трея")
            clipboard_thread = threading.Thread(
                target=self.clipboard_monitor.monitor_loop,
                daemon=True
            )
            clipboard_thread.start()
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n👋 Завершение работы...")


if __name__ == '__main__':
    daemon = ClipHistoryDaemon()
    daemon.run()
