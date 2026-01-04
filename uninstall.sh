#!/bin/bash
# ClipHistory - Деинсталлятор

set -e

INSTALL_DIR="/opt/cliphistory"
REAL_USER=${SUDO_USER:-$USER}
REAL_HOME=$(eval echo ~$REAL_USER)

echo "🗑️  Удаление ClipHistory..."

# Проверка прав
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Для удаления из /opt требуются права root"
    echo "   Запустите: sudo ./uninstall.sh"
    exit 1
fi

# Остановка демона
echo "⏹️  Остановка демона..."
pkill -f cliphistory_new.py || true
pkill -f clipshow_qt.py || true

# Удаление lock файла
rm -f "$REAL_HOME/.cache/cliphistory/.ui.lock"

# Удаление файлов
echo "📁 Удаление файлов..."
rm -rf "$INSTALL_DIR"
rm -f /usr/local/bin/cliphistory
rm -f /usr/local/bin/cliphistory-show
rm -f "$REAL_HOME/.local/share/applications/cliphistory.desktop"
rm -f "$REAL_HOME/.config/autostart/cliphistory.desktop"
rm -f "$REAL_HOME/.local/share/icons/cliphistory.svg"

# Спросить про данные
echo ""
read -p "❓ Удалить данные (история буфера и настройки)? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "💾 Удаление данных..."
    rm -rf "$REAL_HOME/.cache/cliphistory"
    echo "✅ Данные удалены"
else
    echo "💾 Данные сохранены в $REAL_HOME/.cache/cliphistory"
fi

echo ""
echo "✅ ClipHistory успешно удалён!"
echo ""
