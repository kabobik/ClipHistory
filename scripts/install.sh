#!/bin/bash
# ClipHistory - Установщик

set -e

INSTALL_DIR="/opt/cliphistory"

echo "🚀 Установка ClipHistory..."

# Проверка прав
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Для установки в /opt требуются права root"
    echo "   Запустите: sudo ./install.sh"
    exit 1
fi

# Получение реального пользователя (если запущено через sudo)
REAL_USER=${SUDO_USER:-$USER}
REAL_HOME=$(eval echo ~$REAL_USER)

ICON_DIR="$REAL_HOME/.local/share/icons"
DESKTOP_DIR="$REAL_HOME/.local/share/applications"
AUTOSTART_DIR="$REAL_HOME/.config/autostart"

# Проверка зависимостей
echo "📦 Проверка зависимостей..."
MISSING_DEPS=()

if ! command -v python3 &> /dev/null; then
    MISSING_DEPS+=("python3")
fi

if ! command -v xclip &> /dev/null; then
    MISSING_DEPS+=("xclip")
fi

if ! command -v xdotool &> /dev/null; then
    MISSING_DEPS+=("xdotool")
fi

if ! python3 -c "import PyQt5" 2>/dev/null; then
    MISSING_DEPS+=("python3-pyqt5 python3-pyqt5.qtsvg")
fi

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo "❌ Отсутствуют зависимости: ${MISSING_DEPS[*]}"
    echo "   Установите: sudo apt install ${MISSING_DEPS[*]}"
    exit 1
fi

# Создание директорий
echo "📁 Создание директорий..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$ICON_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$AUTOSTART_DIR"

# Копирование файлов
echo "📋 Копирование файлов..."
cp cliphistory_new.py "$INSTALL_DIR/"
cp clipshow_qt.py "$INSTALL_DIR/"
cp config.json "$INSTALL_DIR/"

# Создание исполняемых файлов
chmod +x "$INSTALL_DIR/cliphistory_new.py"
chmod +x "$INSTALL_DIR/clipshow_qt.py"

# Создание символических ссылок
echo "�� Создание символических ссылок..."
ln -sf "$INSTALL_DIR/cliphistory_new.py" /usr/local/bin/cliphistory
ln -sf "$INSTALL_DIR/clipshow_qt.py" /usr/local/bin/cliphistory-show

# Создание SVG иконки
echo "🎨 Создание иконки..."
ICON_FILE="$ICON_DIR/cliphistory.svg"
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

chown $REAL_USER:$REAL_USER "$ICON_FILE"

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

chown $REAL_USER:$REAL_USER "$DESKTOP_FILE"

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

chown $REAL_USER:$REAL_USER "$AUTOSTART_FILE"

# Создание директории для кэша и БД
echo "💾 Создание директории для данных..."
CACHE_DIR="$REAL_HOME/.cache/cliphistory"
mkdir -p "$CACHE_DIR"
chown -R $REAL_USER:$REAL_USER "$CACHE_DIR"

echo ""
echo "✅ ClipHistory успешно установлен!"
echo ""
echo "📌 Команды:"
echo "   cliphistory       - Запустить демон"
echo "   cliphistory-show  - Показать историю буфера"
echo ""
echo "🔧 Настройка горячей клавиши:"
echo "   1. Откройте Системные настройки → Клавиатура → Горячие клавиши"
echo "   2. Добавьте новую комбинацию: Super+V"
echo "   3. Команда: /usr/local/bin/cliphistory-show"
echo ""
echo "🚀 Демон запустится автоматически при следующем входе в систему"
echo "   Или запустите сейчас: cliphistory &"
echo ""
