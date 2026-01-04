# 🏗️ Сборка пакетов ClipHistory

## Варианты упаковки

### 1. .deb пакет (для Debian/Ubuntu/Mint)

Создание полноценного .deb пакета с зависимостями:

```bash
./build-deb.sh
```

Будет создан файл `cliphistory_1.0.0_all.deb`

**Установка:**
```bash
sudo dpkg -i cliphistory_1.0.0_all.deb
sudo apt-get install -f  # установка зависимостей
```

**Удаление:**
```bash
sudo apt remove cliphistory
```

**Преимущества .deb:**
- ✅ Автоматическая проверка зависимостей
- ✅ Интеграция с системой управления пакетами
- ✅ Простое обновление через `apt upgrade`
- ✅ Правильное удаление со всеми файлами
- ✅ Автоматические pre/post install скрипты

### 2. .tar.gz архив (универсальный)

Создание архива с install.sh скриптом:

```bash
./build-tarball.sh
```

Будет создан файл `cliphistory-1.0.0.tar.gz` + контрольная сумма

**Установка:**
```bash
tar -xzf cliphistory-1.0.0.tar.gz
cd cliphistory-1.0.0
sudo ./install.sh
```

**Удаление:**
```bash
cd cliphistory-1.0.0
sudo ./uninstall.sh
```

**Преимущества .tar.gz:**
- ✅ Работает на любом дистрибутиве Linux
- ✅ Простой и понятный формат
- ✅ Легко модифицировать перед установкой
- ✅ Не требует dpkg/rpm

## Структура .deb пакета

```
cliphistory_1.0.0_all.deb
├── opt/cliphistory/              # Файлы приложения
│   ├── cliphistory_new.py       # Демон
│   ├── clipshow_qt.py           # UI
│   └── config.json              # Конфигурация
├── usr/local/bin/               # Команды (symlinks)
│   ├── cliphistory -> /opt/cliphistory/cliphistory_new.py
│   └── cliphistory-show -> /opt/cliphistory/clipshow_qt.py
├── usr/share/applications/      # Меню приложений
│   └── cliphistory.desktop
├── usr/share/icons/             # Иконка
│   └── hicolor/scalable/apps/
│       └── cliphistory.svg
├── etc/xdg/autostart/          # Автозапуск
│   └── cliphistory.desktop
└── DEBIAN/                      # Метаданные пакета
    ├── control                  # Информация о пакете
    ├── postinst                 # Скрипт после установки
    ├── prerm                    # Скрипт перед удалением
    └── postrm                   # Скрипт после удаления
```

## Структура .tar.gz архива

```
cliphistory-1.0.0.tar.gz
└── cliphistory-1.0.0/
    ├── cliphistory_new.py       # Демон
    ├── clipshow_qt.py           # UI
    ├── config.json              # Конфигурация
    ├── install.sh               # Скрипт установки
    ├── uninstall.sh             # Скрипт удаления
    ├── README.md                # Основная документация
    ├── INSTALL.md               # Инструкции по установке
    ├── INSTALL.txt              # Краткая инструкция
    └── VERSION                  # Версия
```

## Изменение версии

Отредактируйте переменную `VERSION` в начале скриптов:

```bash
# В build-deb.sh
VERSION="1.0.0"

# В build-tarball.sh
VERSION="1.0.0"
```

## Требования для сборки

### Для .deb пакета:
```bash
sudo apt install dpkg-dev
```

### Для .tar.gz архива:
```bash
# Стандартные утилиты (уже установлены)
tar, gzip, sha256sum
```

## Публикация

### GitHub Release:

1. Создайте tag:
```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

2. Загрузите файлы в GitHub Releases:
   - `cliphistory_1.0.0_all.deb`
   - `cliphistory-1.0.0.tar.gz`
   - `cliphistory-1.0.0.tar.gz.sha256`

### PPA (для Ubuntu):

1. Зарегистрируйтесь на Launchpad
2. Создайте PPA: https://launchpad.net/~/+activate-ppa
3. Загрузите .deb пакет через dput

### AUR (для Arch Linux):

Создайте PKGBUILD файл:
```bash
pkgname=cliphistory
pkgver=1.0.0
pkgrel=1
pkgdesc="Менеджер истории буфера обмена"
arch=('any')
url="https://github.com/yourusername/cliphistory"
license=('MIT')
depends=('python' 'python-pyqt5' 'xclip' 'xdotool')
source=("${pkgname}-${pkgver}.tar.gz::${url}/archive/v${pkgver}.tar.gz")
sha256sums=('...')

package() {
    cd "$pkgname-$pkgver"
    install -Dm755 cliphistory_new.py "$pkgdir/opt/cliphistory/cliphistory_new.py"
    install -Dm755 clipshow_qt.py "$pkgdir/opt/cliphistory/clipshow_qt.py"
    install -Dm644 config.json "$pkgdir/opt/cliphistory/config.json"
    # ... остальные файлы
}
```

## Тестирование пакетов

### Тест .deb пакета:
```bash
# Установка
sudo dpkg -i cliphistory_1.0.0_all.deb
sudo apt-get install -f

# Проверка файлов
dpkg -L cliphistory

# Проверка работы
cliphistory &
cliphistory-show

# Удаление
sudo apt remove cliphistory

# Проверка очистки
dpkg -l | grep cliphistory  # Должно быть пусто
```

### Тест .tar.gz архива:
```bash
# Распаковка
tar -xzf cliphistory-1.0.0.tar.gz
cd cliphistory-1.0.0

# Проверка контрольной суммы
sha256sum -c ../cliphistory-1.0.0.tar.gz.sha256

# Установка
sudo ./install.sh

# Проверка
cliphistory &
cliphistory-show

# Удаление
sudo ./uninstall.sh
```

## CI/CD автоматизация

Пример GitHub Actions (`.github/workflows/build.yml`):

```yaml
name: Build Packages

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Install dependencies
        run: sudo apt install dpkg-dev
      
      - name: Build .deb package
        run: ./build-deb.sh
      
      - name: Build .tar.gz archive
        run: ./build-tarball.sh
      
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            cliphistory_*.deb
            cliphistory-*.tar.gz
            cliphistory-*.tar.gz.sha256
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Changelog

Ведите CHANGELOG.md для отслеживания изменений:

```markdown
# Changelog

## [1.0.0] - 2026-01-05
### Added
- Начальный релиз
- Мониторинг буфера обмена
- Qt5 интерфейс
- Иконка в трее
- Автозапуск демона
- Поддержка горячих клавиш
```
