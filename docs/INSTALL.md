# 📦 Установка ClipHistory

## Быстрая установка

```bash
sudo ./install.sh
```

Скрипт автоматически:
- ✅ Проверит зависимости
- ✅ Установит файлы в `/opt/cliphistory/`
- ✅ Создаст команды `cliphistory` и `cliphistory-show`
- ✅ Добавит иконку в меню приложений
- ✅ Настроит автозапуск демона

## Зависимости

### Ubuntu/Debian/Mint:
```bash
sudo apt install python3 python3-pyqt5 python3-pyqt5.qtsvg xclip xdotool
```

### Fedora:
```bash
sudo dnf install python3 python3-qt5 xclip xdotool
```

### Arch:
```bash
sudo pacman -S python python-pyqt5 xclip xdotool
```

## Настройка горячей клавиши

После установки настройте системный хоткей:

### Linux Mint / Cinnamon:
1. Откройте **Системные настройки** → **Клавиатура** → **Горячие клавиши**
2. Нажмите **Добавить пользовательское сочетание**
3. Введите:
   - **Имя:** ClipHistory
   - **Команда:** `/usr/local/bin/cliphistory-show`
   - **Горячая клавиша:** нажмите `Super+V`

### GNOME:
```bash
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "['/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/cliphistory/']"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/cliphistory/ name 'ClipHistory'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/cliphistory/ command '/usr/local/bin/cliphistory-show'
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/cliphistory/ binding '<Super>v'
```

### KDE Plasma:
1. **Системные настройки** → **Сочетания клавиш** → **Пользовательские сочетания**
2. **Правка** → **Создать** → **Глобальное сочетание клавиш** → **Команда/URL**
3. Вкладка **Действие**: Команда - `/usr/local/bin/cliphistory-show`
4. Вкладка **Триггер**: Сочетание клавиш - `Meta+V`

## Использование

### Запуск демона вручную:
```bash
cliphistory &
```

### Открыть историю буфера:
```bash
cliphistory-show
```

Или используйте:
- **Горячая клавиша:** `Super+V`
- **Меню приложений:** Найдите "ClipHistory"
- **Иконка в трее:** Левый клик для открытия, правый клик для меню

## Удаление

```bash
sudo ./uninstall.sh
```

Скрипт удалит все файлы программы и спросит, нужно ли удалить данные (историю буфера).

## Файлы программы

После установки:

```
/opt/cliphistory/                  # Файлы программы
├── cliphistory_new.py            # Демон
├── clipshow_qt.py                # UI
└── config.json                   # Конфигурация

/usr/local/bin/                    # Команды
├── cliphistory -> /opt/cliphistory/cliphistory_new.py
└── cliphistory-show -> /opt/cliphistory/clipshow_qt.py

~/.local/share/applications/       # Иконка в меню
└── cliphistory.desktop

~/.config/autostart/               # Автозапуск
└── cliphistory.desktop

~/.local/share/icons/              # Иконка
└── cliphistory.svg

~/.cache/cliphistory/              # Данные пользователя
├── history.db                     # База данных истории
└── .ui.lock                       # Lock файл UI
```

## Конфигурация

Настройки находятся в `/opt/cliphistory/config.json`:

```json
{
    "check_interval": 0.3,         // Интервал проверки буфера (сек)
    "cleanup_days": 7,              // Очистка истории старше N дней
    "auto_paste": true,             // Автовставка при выборе
    "hotkey": "Super+V",            // Отображение в UI
    "debug": false,                 // Режим отладки
    "ui_scale": 1.5,                // Масштаб UI
    "content_width": 650,           // Ширина контента
    "list_height": 500,             // Высота списка
    "max_display_length": 100,      // Макс. длина превью
    "scrollbar_width": 14           // Ширина скроллбара
}
```

## Решение проблем

### Демон не запускается:
```bash
# Проверьте процесс
ps aux | grep cliphistory_new

# Запустите вручную для отладки
python3 /opt/cliphistory/cliphistory_new.py
```

### Иконка не появляется в трее:
```bash
# Проверьте поддержку системного трея
python3 -c "from PyQt5.QtWidgets import QApplication, QSystemTrayIcon; app = QApplication([]); print(QSystemTrayIcon.isSystemTrayAvailable())"
```

### UI не открывается:
```bash
# Удалите lock файл
rm -f ~/.cache/cliphistory/.ui.lock

# Проверьте xdotool
xdotool getmouselocation --shell
```

### Горячая клавиша не работает:
```bash
# Проверьте настройку в системе
# Попробуйте запустить вручную:
/usr/local/bin/cliphistory-show
```

## Разработка

Для разработки без установки в систему:

```bash
# Запуск демона
python3 cliphistory_new.py

# Запуск UI
python3 clipshow_qt.py
```
