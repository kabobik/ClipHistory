#!/bin/bash
# Скрипт для создания .tar.gz архива ClipHistory

set -e

VERSION="1.0.0"
PACKAGE_NAME="cliphistory"
BUILD_DIR="build/${PACKAGE_NAME}-${VERSION}"

echo "📦 Создание .tar.gz архива ClipHistory v${VERSION}..."

# Очистка старой сборки
rm -rf build
mkdir -p "$BUILD_DIR"

# Копирование файлов
echo "📋 Копирование файлов..."
cp cliphistory_new.py "$BUILD_DIR/"
cp clipshow_qt.py "$BUILD_DIR/"
cp config.json "$BUILD_DIR/"
cp install.sh "$BUILD_DIR/"
cp uninstall.sh "$BUILD_DIR/"
cp README.md "$BUILD_DIR/" 2>/dev/null || echo "README.md не найден"
cp INSTALL.md "$BUILD_DIR/" 2>/dev/null || echo "INSTALL.md не найден"

# Создание файла VERSION
echo "$VERSION" > "$BUILD_DIR/VERSION"

# Установка прав
chmod +x "$BUILD_DIR/install.sh"
chmod +x "$BUILD_DIR/uninstall.sh"
chmod +x "$BUILD_DIR/cliphistory_new.py"
chmod +x "$BUILD_DIR/clipshow_qt.py"

# Создание README для архива
cat > "$BUILD_DIR/INSTALL.txt" << 'EOF'
ClipHistory - Менеджер истории буфера обмена
=============================================

УСТАНОВКА:
----------
sudo ./install.sh

Скрипт автоматически:
- Проверит зависимости
- Установит файлы в /opt/cliphistory/
- Создаст команды cliphistory и cliphistory-show
- Добавит иконку в меню приложений
- Настроит автозапуск демона

ЗАВИСИМОСТИ (Debian/Ubuntu/Mint):
----------------------------------
sudo apt install python3 python3-pyqt5 python3-pyqt5.qtsvg xclip xdotool

НАСТРОЙКА ГОРЯЧЕЙ КЛАВИШИ:
--------------------------
1. Откройте Системные настройки → Клавиатура → Горячие клавиши
2. Добавьте новую комбинацию: Super+V
3. Команда: /usr/local/bin/cliphistory-show

ИСПОЛЬЗОВАНИЕ:
--------------
cliphistory &          # Запустить демон
cliphistory-show       # Показать историю

УДАЛЕНИЕ:
---------
sudo ./uninstall.sh

ФАЙЛЫ:
------
cliphistory_new.py     - Демон мониторинга буфера
clipshow_qt.py         - UI для отображения истории
config.json            - Конфигурация
install.sh             - Скрипт установки
uninstall.sh           - Скрипт удаления
EOF

# Создание архива
echo "🗜️  Создание архива..."
cd build
tar -czf "${PACKAGE_NAME}-${VERSION}.tar.gz" "${PACKAGE_NAME}-${VERSION}"
cd ..

# Перемещение в корень
mv "build/${PACKAGE_NAME}-${VERSION}.tar.gz" "./"

# Создание контрольной суммы
echo "🔐 Создание контрольной суммы..."
sha256sum "${PACKAGE_NAME}-${VERSION}.tar.gz" > "${PACKAGE_NAME}-${VERSION}.tar.gz.sha256"

echo ""
echo "✅ Архив создан: ${PACKAGE_NAME}-${VERSION}.tar.gz"
echo "   Контрольная сумма: ${PACKAGE_NAME}-${VERSION}.tar.gz.sha256"
echo ""
echo "📦 Распаковка и установка:"
echo "   tar -xzf ${PACKAGE_NAME}-${VERSION}.tar.gz"
echo "   cd ${PACKAGE_NAME}-${VERSION}"
echo "   sudo ./install.sh"
echo ""
