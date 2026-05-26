#!/bin/bash
# ClipHistory - Установщик
# Этот скрипт автоматизирует установку ClipHistory на чистую систему Linux

set -e

# Обработчик ошибок
trap 'echo "❌ Установка прервана с ошибкой в строке $LINENO"; exit 1' ERR

INSTALL_DIR="/opt/cliphistory"

echo "🚀 Установка ClipHistory..."
echo ""

# Проверка прав
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Для установки в /opt требуются права root"
    echo "💡 Запустите: sudo $0"
    exit 1
fi

# Получение реального пользователя (если запущено через sudo)
REAL_USER=${SUDO_USER:-$USER}
REAL_HOME=$(eval echo ~$REAL_USER)

ICON_DIR="$REAL_HOME/.local/share/icons"
DESKTOP_DIR="$REAL_HOME/.local/share/applications"
AUTOSTART_DIR="$REAL_HOME/.config/autostart"

# Проверка и установка зависимостей
echo "📦 Проверка зависимостей..."
MISSING_DEPS=()

# Проверка системных команд
if ! command -v python3 &> /dev/null; then
    MISSING_DEPS+=("python3")
fi

if ! command -v xclip &> /dev/null; then
    MISSING_DEPS+=("xclip")
fi

if ! command -v wl-paste &> /dev/null || ! command -v wl-copy &> /dev/null; then
    MISSING_DEPS+=("wl-clipboard")
fi

if ! command -v xdotool &> /dev/null; then
    MISSING_DEPS+=("xdotool")
fi

# Проверка Python модулей
if ! python3 -c "import PyQt5.QtWidgets" 2>/dev/null; then
    MISSING_DEPS+=("python3-pyqt5")
fi

if ! python3 -c "import PyQt5.QtSvg" 2>/dev/null; then
    MISSING_DEPS+=("python3-pyqt5.qtsvg")
fi

# Автоматическая установка недостающих зависимостей
if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo "⚠️  Обнаружены недостающие зависимости: ${MISSING_DEPS[*]}"
    echo "📥 Автоматическая установка..."
    
    # Обновление кэша apt
    apt-get update > /dev/null 2>&1 || true
    
    # Установка пакетов
    apt-get install -y "${MISSING_DEPS[@]}" || {
        echo "❌ Ошибка при установке зависимостей"
        echo "   Попытайтесь установить вручную:"
        echo "   sudo apt install ${MISSING_DEPS[*]}"
        exit 1
    }
    
    echo "✅ Зависимости установлены"
fi

# Финальная проверка всех зависимостей
echo "🔍 Финальная проверка зависимостей..."

DEPS_OK=true

if ! python3 -c "from PyQt5.QtWidgets import QApplication; from PyQt5.QtSvg import QSvgRenderer; from PyQt5.QtGui import QIcon; from PyQt5.QtCore import Qt" 2>/dev/null; then
    echo "❌ Ошибка при загрузке PyQt5 módulей"
    DEPS_OK=false
fi

if ! command -v xclip &> /dev/null; then
    echo "❌ xclip не установлен"
    DEPS_OK=false
fi

if ! command -v wl-paste &> /dev/null || ! command -v wl-copy &> /dev/null; then
    echo "❌ wl-clipboard не установлен"
    DEPS_OK=false
fi

if ! command -v xdotool &> /dev/null; then
    echo "❌ xdotool не установлен"
    DEPS_OK=false
fi

if [ "$DEPS_OK" = false ]; then
    echo "❌ Не все зависимости установлены корректно"
    exit 1
fi

echo "✅ Все зависимости в порядке"

# Создание директорий
echo "📁 Создание директорий..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$ICON_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$AUTOSTART_DIR"

# Копирование файлов
echo "📋 Копирование файлов..."

# Определение директории с исходными файлами
if [ -f "cliphistory_new.py" ]; then
    SOURCE_DIR="."
elif [ -f "../cliphistory_new.py" ]; then
    SOURCE_DIR=".."
else
    echo "❌ Ошибка: не найдены исходные файлы"
    echo "   Убедитесь что установщик запущен из правильной директории"
    exit 1
fi

# Проверка наличия всех необходимых файлов
for file in cliphistory_new.py clipshow_qt.py config.json; do
    if [ ! -f "$SOURCE_DIR/$file" ]; then
        echo "❌ Отсутствует файл: $SOURCE_DIR/$file"
        exit 1
    fi
done

# Копирование файлов
cp "$SOURCE_DIR/cliphistory_new.py" "$INSTALL_DIR/"
cp "$SOURCE_DIR/clipshow_qt.py" "$INSTALL_DIR/"
cp "$SOURCE_DIR/config.json" "$INSTALL_DIR/"

if [ ! -f "$INSTALL_DIR/cliphistory_new.py" ] || [ ! -f "$INSTALL_DIR/clipshow_qt.py" ] || [ ! -f "$INSTALL_DIR/config.json" ]; then
    echo "❌ Ошибка при копировании файлов"
    exit 1
fi

echo "✅ Файлы скопированы"

# Создание исполняемых файлов
echo "🔐 Установка прав доступа..."
chmod +x "$INSTALL_DIR/cliphistory_new.py"
chmod +x "$INSTALL_DIR/clipshow_qt.py"

# Проверка прав доступа
if [ ! -x "$INSTALL_DIR/cliphistory_new.py" ] || [ ! -x "$INSTALL_DIR/clipshow_qt.py" ]; then
    echo "❌ Ошибка при установке прав доступа"
    exit 1
fi

echo "✅ Права доступа установлены"

# Создание символических ссылок
echo "🔗 Создание символических ссылок..."

# Удаление старых ссылок если существуют
rm -f /usr/local/bin/cliphistory /usr/local/bin/cliphistory-show 2>/dev/null || true

# Создание новых ссылок
ln -sf "$INSTALL_DIR/cliphistory_new.py" /usr/local/bin/cliphistory || {
    echo "❌ Ошибка при создании ссылки cliphistory"
    exit 1
}

ln -sf "$INSTALL_DIR/clipshow_qt.py" /usr/local/bin/cliphistory-show || {
    echo "❌ Ошибка при создании ссылки cliphistory-show"
    exit 1
}

# Проверка создания ссылок
if [ ! -L /usr/local/bin/cliphistory ] || [ ! -L /usr/local/bin/cliphistory-show ]; then
    echo "❌ Ошибка при создании символических ссылок"
    exit 1
fi

echo "✅ Символические ссылки созданы"

# Создание SVG иконки
echo "🎨 Создание иконки..."
ICON_FILE="$ICON_DIR/cliphistory.svg"

# Проверка прав доступа на директорию
if [ ! -d "$ICON_DIR" ]; then
    echo "❌ Ошибка: директория иконок недоступна"
    exit 1
fi

# Создание иконки
cat > "$ICON_FILE" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#4a90e2;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#357abd;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect x="8" y="6" width="32" height="40" rx="4" fill="url(#grad1)"/>
  <rect x="10" y="12" width="28" height="32" rx="2" fill="#ffffff" opacity="0.95"/>
  <circle cx="24" cy="6" r="4" fill="#357abd"/>
  <circle cx="24" cy="6" r="2" fill="#ffffff"/>
  <line x1="14" y1="18" x2="34" y2="18" stroke="#4a90e2" stroke-width="2" stroke-linecap="round"/>
  <line x1="14" y1="24" x2="34" y2="24" stroke="#4a90e2" stroke-width="2" stroke-linecap="round"/>
  <line x1="14" y1="30" x2="28" y2="30" stroke="#4a90e2" stroke-width="2" stroke-linecap="round"/>
  <line x1="14" y1="36" x2="26" y2="36" stroke="#4a90e2" stroke-width="2" stroke-linecap="round"/>
</svg>
EOF

# Проверка создания файла иконки
if [ ! -f "$ICON_FILE" ]; then
    echo "❌ Ошибка при создании иконки"
    exit 1
fi

chown $REAL_USER:$REAL_USER "$ICON_FILE"
echo "✅ Иконка создана"

# Создание .desktop файла для меню приложений
echo "📝 Создание .desktop файла..."
DESKTOP_FILE="$DESKTOP_DIR/cliphistory.desktop"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=ClipHistory
Comment=Менеджер истории буфера обмена
Icon=$ICON_FILE
Exec=/usr/local/bin/cliphistory-show
Terminal=false
Categories=Utility;
Keywords=clipboard;history;copy;paste;
StartupNotify=false
EOF

if [ ! -f "$DESKTOP_FILE" ]; then
    echo "❌ Ошибка при создании .desktop файла"
    exit 1
fi

chown $REAL_USER:$REAL_USER "$DESKTOP_FILE"
chmod 644 "$DESKTOP_FILE"
echo "✅ .desktop файл создан"

# Создание autostart файла
echo "⚡ Настройка автозапуска..."
AUTOSTART_FILE="$AUTOSTART_DIR/cliphistory.desktop"
cat > "$AUTOSTART_FILE" << EOF
[Desktop Entry]
Type=Application
Name=ClipHistory Daemon
Comment=Демон менеджера истории буфера обмена
Icon=$ICON_FILE
Exec=/usr/local/bin/cliphistory
Terminal=false
X-GNOME-Autostart-enabled=true
Hidden=false
EOF

if [ ! -f "$AUTOSTART_FILE" ]; then
    echo "❌ Ошибка при создании файла автозапуска"
    exit 1
fi

chown $REAL_USER:$REAL_USER "$AUTOSTART_FILE"
chmod 644 "$AUTOSTART_FILE"
echo "✅ Автозапуск настроен"

# Создание директории для кэша и БД
echo "💾 Создание директории для данных..."
CACHE_DIR="$REAL_HOME/.cache/cliphistory"
DATA_DIR="$REAL_HOME/.local/share/cliphistory"

mkdir -p "$CACHE_DIR"
mkdir -p "$DATA_DIR"

# Установка прав доступа
chown -R $REAL_USER:$REAL_USER "$CACHE_DIR"
chown -R $REAL_USER:$REAL_USER "$DATA_DIR"
chmod 700 "$CACHE_DIR"
chmod 700 "$DATA_DIR"

if [ ! -d "$CACHE_DIR" ] || [ ! -d "$DATA_DIR" ]; then
    echo "❌ Ошибка при создании директорий данных"
    exit 1
fi

echo "✅ Директории данных созданы"

# Проверка конфигурационного файла
echo "⚙️  Проверка конфигурации..."
if [ ! -f "$INSTALL_DIR/config.json" ]; then
    echo "❌ Конфигурационный файл не найден"
    exit 1
fi

# Проверка корректности JSON
if ! python3 -c "import json; json.load(open('$INSTALL_DIR/config.json'))" 2>/dev/null; then
    echo "❌ Ошибка в конфигурационном файле config.json"
    exit 1
fi

echo "✅ Конфигурация валидна"

# Финальная проверка установки
echo ""
echo "🔍 Финальная проверка установки..."

INSTALL_OK=true

# Проверка файлов в /opt
for file in cliphistory_new.py clipshow_qt.py config.json; do
    if [ ! -f "$INSTALL_DIR/$file" ]; then
        echo "❌ Файл не найден: $INSTALL_DIR/$file"
        INSTALL_OK=false
    fi
done

# Проверка исполняемости
if [ ! -x "$INSTALL_DIR/cliphistory_new.py" ] || [ ! -x "$INSTALL_DIR/clipshow_qt.py" ]; then
    echo "❌ Не все файлы имеют права на исполнение"
    INSTALL_OK=false
fi

# Проверка символических ссылок
if [ ! -L /usr/local/bin/cliphistory ] || [ ! -L /usr/local/bin/cliphistory-show ]; then
    echo "❌ Символические ссылки не созданы"
    INSTALL_OK=false
fi

# Проверка файлов конфигурации пользователя
if [ ! -f "$DESKTOP_DIR/cliphistory.desktop" ] || [ ! -f "$AUTOSTART_DIR/cliphistory.desktop" ]; then
    echo "❌ Файлы конфигурации не созданы"
    INSTALL_OK=false
fi

# Проверка иконки
if [ ! -f "$ICON_FILE" ]; then
    echo "❌ Иконка не найдена"
    INSTALL_OK=false
fi

if [ "$INSTALL_OK" = false ]; then
    echo "❌ Проверка установки не пройдена"
    exit 1
fi

echo "✅ Все компоненты установлены корректно"

echo ""
echo "✅ ClipHistory успешно установлен!"
echo ""
echo "� Информация об установке:"
echo "   📦 Установочная директория: $INSTALL_DIR"
echo "   👤 Пользователь: $REAL_USER"
echo "   🎨 Иконка: $ICON_FILE"
echo "   📝 Точка входа (меню): $DESKTOP_DIR/cliphistory.desktop"
echo "   ⚡ Автозапуск: $AUTOSTART_DIR/cliphistory.desktop"
echo ""
echo "📌 Доступные команды:"
echo "   cliphistory       - Запустить демон в фоне"
echo "   cliphistory-show  - Показать окно истории буфера обмена"
echo ""
echo "🚀 Быстрый старт:"
echo "   1. Запустить демон: cliphistory &"
echo "   2. Показать историю: cliphistory-show"
echo ""
echo "🔧 Настройка горячей клавиши (опционально):"
echo "   1. Откройте Системные настройки → Клавиатура → Горячие клавиши"
echo "   2. Добавьте новую комбинацию: Super+V"
echo "   3. Команда: /usr/local/bin/cliphistory-show"
echo ""
echo "📖 Расположение файлов:"
echo "   Кэш и БД: $CACHE_DIR"
echo "   Данные: $DATA_DIR"
echo "   Конфиг: $INSTALL_DIR/config.json"
echo ""
echo "💡 Демон запустится автоматически при следующем входе в систему"
echo "   (благодаря настройке автозапуска)"
echo ""
