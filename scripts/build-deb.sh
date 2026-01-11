#!/bin/bash
# Скрипт для создания .deb пакета ClipHistory

set -e

# Читаем версию из файла VERSION
VERSION=$(cat "$(dirname "$0")/../VERSION" | tr -d '\n\r')
PACKAGE_NAME="cliphistory"
ARCH="all"
BUILD_DIR="build/${PACKAGE_NAME}_${VERSION}_${ARCH}"

echo "📦 Создание .deb пакета ClipHistory v${VERSION}..."

# Очистка старой сборки
rm -rf build
mkdir -p "$BUILD_DIR"

# Создание структуры пакета
echo "📁 Создание структуры пакета..."
mkdir -p "$BUILD_DIR/opt/cliphistory"
mkdir -p "$BUILD_DIR/usr/local/bin"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$BUILD_DIR/etc/xdg/autostart"
mkdir -p "$BUILD_DIR/DEBIAN"

# Копирование файлов приложения
echo "📋 Копирование файлов..."
cp cliphistory_new.py "$BUILD_DIR/opt/cliphistory/"
cp clipshow_qt.py "$BUILD_DIR/opt/cliphistory/"
cp config.json "$BUILD_DIR/opt/cliphistory/"
chmod +x "$BUILD_DIR/opt/cliphistory/cliphistory_new.py"
chmod +x "$BUILD_DIR/opt/cliphistory/clipshow_qt.py"

# Создание символических ссылок (будут созданы в postinst)
# ln -sf относительно не работает в .deb, делаем через postinst

# Создание иконки
cat > "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps/cliphistory.svg" << 'EOF'
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

# Создание .desktop файла
cat > "$BUILD_DIR/usr/share/applications/cliphistory.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=ClipHistory
Comment=Менеджер истории буфера обмена
Icon=cliphistory
Exec=cliphistory
Terminal=false
Categories=Utility;
Keywords=clipboard;history;copy;paste;
StartupNotify=false
EOF

# Создание autostart файла
cat > "$BUILD_DIR/etc/xdg/autostart/cliphistory.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=ClipHistory Daemon
Comment=Демон менеджера истории буфера обмена
Icon=cliphistory
Exec=cliphistory
Terminal=false
X-GNOME-Autostart-enabled=true
Hidden=false
EOF

# Создание control файла
cat > "$BUILD_DIR/DEBIAN/control" << EOF
Package: cliphistory
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Depends: python3 (>= 3.6), python3-pyqt5, python3-pyqt5.qtsvg, xclip, xdotool
Maintainer: Anton <anton@example.com>
Description: Менеджер истории буфера обмена
 ClipHistory - современный менеджер истории буфера обмена для Linux.
 .
 Особенности:
  - Автоматическое сохранение истории буфера обмена
  - Удобный интерфейс на Qt5
  - Поддержка горячих клавиш
  - Иконка в системном трее
  - Автозапуск демона при входе в систему
EOF

# Создание postinst скрипта
cat > "$BUILD_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

# Создание символических ссылок
ln -sf /opt/cliphistory/cliphistory_new.py /usr/local/bin/cliphistory
ln -sf /opt/cliphistory/clipshow_qt.py /usr/local/bin/cliphistory-show

# Обновление кэша иконок
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache /usr/share/icons/hicolor/ || true
fi

# Обновление базы приложений
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database /usr/share/applications || true
fi

echo ""
echo "✅ ClipHistory установлен!"
echo ""
echo "🔧 Настройте горячую клавишу Super+V:"
echo "   Системные настройки → Клавиатура → Горячие клавиши"
echo "   Команда: cliphistory-show"
echo ""
echo "🚀 Демон запустится автоматически при следующем входе"
echo "   Или запустите сейчас: cliphistory &"
echo ""

exit 0
EOF

chmod +x "$BUILD_DIR/DEBIAN/postinst"

# Создание prerm скрипта
cat > "$BUILD_DIR/DEBIAN/prerm" << 'EOF'
#!/bin/bash
set -e

# Остановка демона
pkill -f cliphistory_new.py || true
pkill -f clipshow_qt.py || true

exit 0
EOF

chmod +x "$BUILD_DIR/DEBIAN/prerm"

# Создание postrm скрипта
cat > "$BUILD_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e

if [ "$1" = "purge" ]; then
    # Удаление символических ссылок
    rm -f /usr/local/bin/cliphistory
    rm -f /usr/local/bin/cliphistory-show
    
    # Обновление кэшей
    if command -v gtk-update-icon-cache &> /dev/null; then
        gtk-update-icon-cache /usr/share/icons/hicolor/ || true
    fi
    
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database /usr/share/applications || true
    fi
fi

exit 0
EOF

chmod +x "$BUILD_DIR/DEBIAN/postrm"

# Установка правильных прав
echo "🔒 Установка прав доступа..."
find "$BUILD_DIR" -type f -exec chmod 644 {} \;
find "$BUILD_DIR" -type d -exec chmod 755 {} \;
chmod +x "$BUILD_DIR/opt/cliphistory/cliphistory_new.py"
chmod +x "$BUILD_DIR/opt/cliphistory/clipshow_qt.py"
chmod +x "$BUILD_DIR/DEBIAN/postinst"
chmod +x "$BUILD_DIR/DEBIAN/prerm"
chmod +x "$BUILD_DIR/DEBIAN/postrm"

# Сборка пакета
echo "🔨 Сборка .deb пакета..."
dpkg-deb --build "$BUILD_DIR"

# Перемещение в корень
mv "build/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb" "./"

echo ""
echo "✅ Пакет создан: ${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo ""
echo "📦 Установка:"
echo "   sudo dpkg -i ${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo "   sudo apt-get install -f  # если есть зависимости"
echo ""
echo "🗑️  Удаление:"
echo "   sudo apt remove cliphistory"
echo ""
