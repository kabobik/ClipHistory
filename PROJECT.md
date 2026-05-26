# ClipHistory

Современный менеджер истории буфера обмена для Linux.

## 📋 Структура проекта

```
cliphistory/
├── cliphistory_new.py       # Демон мониторинга буфера
├── clipshow_qt.py           # UI приложение (Qt5)
├── config.json              # Конфигурация
├── README.md                # Основная документация
├── LICENSE                  # Лицензия MIT
│
├── scripts/                 # Скрипты установки и сборки
│   ├── install.sh          # Установка в систему
│   ├── uninstall.sh        # Удаление из системы
│   ├── build-deb.sh        # Сборка .deb пакета
│   └── build-tarball.sh    # Сборка .tar.gz архива
│
├── docs/                    # Документация
│   ├── INSTALL.md          # Инструкция по установке
│   └── BUILD.md            # Инструкция по сборке
│
├── tests/
│   └── manual/             # Ручные диагностические скрипты
│
└── archive/                 # Старые версии
    ├── clipshow.py         # Версия с Rofi
    └── clipshow_gtk.py     # Версия с GTK
```

## 🚀 Быстрый старт

### Установка:
```bash
cd scripts
sudo ./install.sh
```

### Запуск из исходников:
```bash
# Демон
python3 cliphistory_new.py

# UI
python3 clipshow_qt.py
```

### Сборка пакета:
```bash
cd scripts
./build-deb.sh        # .deb пакет
./build-tarball.sh    # .tar.gz архив
```

## 📚 Документация

- **README.md** - Основная документация, возможности, использование
- **docs/INSTALL.md** - Подробная инструкция по установке
- **docs/BUILD.md** - Инструкция по сборке и упаковке

## 🛠️ Разработка

### Основные файлы:
- `cliphistory_new.py` - Демон с тремя классами:
  - `ClipboardMonitor` - мониторинг буфера обмена
  - `HotkeyManager` - управление горячими клавишами
  - `ClipHistoryDaemon` - главный координатор

- `clipshow_qt.py` - Qt5 UI приложение:
  - Темный интерфейс в стиле Windows 11
  - Умное позиционирование окна
  - Автообновление истории
  - Закрепление элементов

### Конфигурация:
`config.json` - настройки приложения (интервалы, размеры UI, и т.д.)

### Зависимости:
- Python 3.6+
- PyQt5
- xclip
- xdotool

## 📦 Сборка

См. [docs/BUILD.md](docs/BUILD.md) для полной инструкции.

## 📝 Лицензия

MIT License - см. [LICENSE](LICENSE)
