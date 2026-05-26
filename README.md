# 📋 ClipHistory

<div align="center">

Современный менеджер истории буфера обмена для Linux с интерфейсом в стиле Windows 11.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.6+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Linux-lightgrey.svg)

</div>

## ✨ Особенности

- 🎨 **Современный UI** - темная тема в стиле Windows 11
- ⚡ **Горячие клавиши** - быстрый доступ через Super+V
- 🔄 **Автообновление** - история обновляется в реальном времени
- 📌 **Закрепление** - закрепляйте важные элементы
- 🎯 **Умное позиционирование** - окно открывается рядом с курсором
- 💾 **База данных SQLite** - вся история сохраняется
- 🚀 **Автозапуск** - демон запускается при входе в систему
- 🖼️ **Иконка в трее** - показывает статус демона с темным меню
- 🔍 **Поиск** - быстрый поиск по истории
- 📋 **Форматирование** - сохранение текста с форматированием

## 🚀 Быстрая установка

### Из .deb пакета (рекомендуется)

```bash
VERSION=$(cat VERSION)
sudo dpkg -i "cliphistory_${VERSION}_all.deb"
sudo apt-get install -f
```
Имя файла пакета содержит версию из `VERSION`.

### Из исходников

```bash
cd scripts
sudo ./install.sh
```

## 📋 Требования

**Debian/Ubuntu/Linux Mint:**
```bash
sudo apt install python3 python3-pyqt5 python3-pyqt5.qtsvg xclip xdotool wl-clipboard
```

## ⚙️ Настройка горячей клавиши

**Linux Mint / Cinnamon:**
1. **Системные настройки** → **Клавиатура** → **Горячие клавиши**
2. Нажмите **Добавить пользовательское сочетание**
3. Введите:
   - **Имя:** ClipHistory
   - **Команда:** `cliphistory-show`
   - **Горячая клавиша:** нажмите `Super+V`

## 🎮 Использование

**Команды:**
```bash
cliphistory         # Запустить демон
cliphistory-show    # Показать историю буфера
```

**Управление:**
- **Super+V** - Открыть историю
- **Enter** / **Клик** - Выбрать и вставить элемент
- **Escape** - Закрыть окно
- **⭐ Иконка** - Закрепить/открепить элемент
- **🗑️ Иконка** - Удалить элемент

**Иконка в трее:**
- **Левый клик** - Открыть историю
- **Правый клик** - Темное меню:
  - Открыть историю
  - Выход

## ⚙️ Конфигурация

Файл: `/opt/cliphistory/config.json` (или `config.json` при запуске из исходников)

```json
{
    "check_interval": 0.3,      // Интервал проверки буфера (сек)
    "clipboard_timeout": 0.35,  // Таймаут чтения clipboard (сек)
    "cleanup_days": 7,           // Удаление истории старше N дней
    "auto_paste": true,          // Автовставка при выборе
    "debug": false,              // Режим отладки
    "ui_scale": 1.5,             // Масштаб интерфейса
    "content_width": 650,        // Ширина контента
    "list_height": 500           // Высота списка
}
```

## 📁 Структура проекта

```
cliphistory/
├── cliphistory_new.py      # Демон мониторинга буфера
├── clipshow_qt.py          # UI приложение (Qt5)
├── config.json             # Конфигурация
├── scripts/                # Скрипты
│   ├── install.sh          # Установка
│   ├── uninstall.sh        # Удаление
│   ├── build-deb.sh       # Сборка .deb
│   └── build-tarball.sh   # Сборка .tar.gz
├── docs/                   # Документация
│   ├── INSTALL.md         # Подробная инструкция
│   └── BUILD.md           # Сборка пакетов
└── archive/                # Старые версии
```

## 🛠️ Разработка

**Запуск из исходников:**
```bash
python3 cliphistory_new.py  # Демон
python3 clipshow_qt.py      # UI
```

**Сборка пакетов:**
```bash
cd scripts
./build-deb.sh        # .deb пакет
./build-tarball.sh    # .tar.gz архив
```

См. [docs/BUILD.md](docs/BUILD.md) для подробностей.

## 🐛 Решение проблем

**Демон не запускается:**
```bash
ps aux | grep cliphistory_new
python3 /opt/cliphistory/cliphistory_new.py  # Отладка
```

**UI не открывается:**
```bash
rm -f ~/.cache/cliphistory/.ui.lock
```

**Горячая клавиша не работает:**
Используйте полный путь: `/usr/local/bin/cliphistory-show`

**KDE Plasma / Wayland медленно видит новые копии:**
Установите `wl-clipboard`; на Wayland мониторинг использует `wl-paste`, а восстановление выбранного элемента - `wl-copy`.

```bash
sudo apt install wl-clipboard
```

## 📝 История изменений

**v1.0.0** (2026-01-05)
- 🎉 Начальный релиз
- ✨ Qt5 интерфейс в темном стиле
- 🚀 Автозапуск демона
- 📌 Закрепление элементов
- 🖼️ Темная иконка в трее с меню
- ⚡ Поддержка горячих клавиш
- 🎯 Умное позиционирование окна

## 📄 Лицензия

MIT License - см. [LICENSE](LICENSE)

## 🙏 Благодарности

- PyQt5 за UI фреймворк
- xclip, wl-clipboard и xdotool за работу с буфером обмена
- Сообществу Linux за вдохновение

---

⭐ Если проект вам понравился, поставьте звезду на GitHub!
