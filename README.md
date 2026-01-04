# ClipHistory

Простой и универсальный менеджер истории буфера обмена для Linux (X11).

## Особенности

✅ **Универсальность** - поддерживает текст, изображения, файлы и любые MIME типы  
✅ **Простота** - одна горячая клавиша, один список, Enter = вставка  
✅ **Автовставка** - автоматически эмулирует Ctrl+V после выбора  
✅ **Минимализм** - без GUI, без лишних функций  
✅ **Умная очистка** - автоматически удаляет старые элементы  

## Установка зависимостей

```bash
sudo apt install xclip rofi xdotool python3
```

## Использование

### 1. Запуск демона

```bash
python3 cliphistory.py
```

Демон будет мониторить clipboard и сохранять историю.

### 2. Показ истории

```bash
python3 clipshow.py
```

Или настройте горячую клавишу (например, Super+V) в системных настройках:
- Command: `/full/path/to/clipshow.py`
- Shortcut: Super+V

### 3. Автозапуск демона

Создайте systemd сервис:

```bash
# ~/.config/systemd/user/cliphistory.service
[Unit]
Description=ClipHistory Daemon

[Service]
ExecStart=/usr/bin/python3 /home/YOUR_USER/VsCode/ClipHistory/cliphistory.py
Restart=always

[Install]
WantedBy=default.target
```

Затем:
```bash
systemctl --user enable cliphistory.service
systemctl --user start cliphistory.service
```

## Конфигурация

Редактируйте `config.json`:

```json
{
  "max_text_items": 50,      // Максимум текстовых элементов
  "max_image_items": 10,     // Максимум изображений
  "max_other_items": 20,     // Максимум других типов
  "check_interval": 0.3,     // Интервал проверки (секунды)
  "cleanup_days": 7,         // Удалять старше N дней
  "auto_paste": true,        // Автоматически Ctrl+V после выбора
  "debug": false             // Отладочные сообщения
}
```

## Как это работает

1. **Демон** (`cliphistory.py`) следит за clipboard каждые 0.3s
2. При изменении:
   - Определяет MIME тип (text/plain, image/png, и т.д.)
   - Сохраняет в SQLite + файлы для изображений
   - Удаляет дубликаты и старые элементы
3. **UI** (`clipshow.py`):
   - Показывает историю в rofi
   - Восстанавливает выбранный элемент в clipboard
   - Автоматически вставляет (Ctrl+V)

## Хранилище

```
~/.cache/cliphistory/
├── history.db          # SQLite база
├── images/             # Изображения (PNG, JPEG)
└── other/              # Другие форматы
```

## Поддерживаемые форматы

- ✅ Текст (plain, HTML, uri-list)
- ✅ Изображения (PNG, JPEG, BMP, GIF)
- ✅ Файлы (копирование из файлового менеджера)
- ✅ Любые другие MIME типы (сохраняются как есть)

## Лицензия

MIT
