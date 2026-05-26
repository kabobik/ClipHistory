# 🏗️ Сборка пакетов ClipHistory

## Варианты упаковки

### 1. .deb пакет (для Debian/Ubuntu/Mint)

Создание полноценного .deb пакета с зависимостями:

```bash
./build-deb.sh
```

Будет создан файл `cliphistory_<version>_all.deb`, где `<version>` берется из `VERSION`.

**Установка:**
```bash
sudo dpkg -i cliphistory_<version>_all.deb
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

Будет создан файл `cliphistory-<version>.tar.gz` + контрольная сумма

**Установка:**
```bash
tar -xzf cliphistory-<version>.tar.gz
cd cliphistory-<version>
sudo ./install.sh
```

**Удаление:**
```bash
cd cliphistory-<version>
sudo ./uninstall.sh
```

**Преимущества .tar.gz:**
- ✅ Работает на любом дистрибутиве Linux
- ✅ Простой и понятный формат
- ✅ Легко модифицировать перед установкой
- ✅ Не требует dpkg/rpm

## Структура .deb пакета

```
cliphistory_<version>_all.deb
├── opt/cliphistory/              # Файлы приложения
│   ├── cliphistory_new.py       # Демон
│   ├── clipshow_qt.py           # UI
│   ├── VERSION                  # Версия сборки
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
cliphistory-<version>.tar.gz
└── cliphistory-<version>/
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

Версия хранится в корневом файле `VERSION`. Оба сборочных скрипта читают ее оттуда:

```bash
cat VERSION
```

При сборке эта версия попадает в имя архива/пакета, metadata `.deb` и файл `VERSION` внутри собранного пакета.

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
VERSION=$(cat VERSION)
git tag -a "v${VERSION}" -m "Release version ${VERSION}"
git push origin "v${VERSION}"
```

2. Загрузите файлы в GitHub Releases:
   - `cliphistory_<version>_all.deb`
   - `cliphistory-<version>.tar.gz`
   - `cliphistory-<version>.tar.gz.sha256`

### PPA (для Ubuntu):

1. Зарегистрируйтесь на Launchpad
2. Создайте PPA: https://launchpad.net/~/+activate-ppa
3. Загрузите .deb пакет через dput

### AUR (для Arch Linux):

Создайте PKGBUILD файл:
```bash
pkgname=cliphistory
pkgver=<version>
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
sudo dpkg -i cliphistory_<version>_all.deb
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
tar -xzf cliphistory-<version>.tar.gz
cd cliphistory-<version>

# Проверка контрольной суммы
sha256sum -c ../cliphistory-<version>.tar.gz.sha256

# Установка
sudo ./install.sh

# Проверка
cliphistory &
cliphistory-show

# Удаление
sudo ./uninstall.sh
```

## CI/CD автоматизация

В репозитории есть workflow `.github/workflows/build-deb.yml`. Он запускается вручную или при каждом push в `master`/`main`, если изменились файлы, влияющие на пакеты:

- `VERSION`
- `cliphistory_new.py`
- `clipshow_qt.py`
- `config.json`
- `scripts/build-deb.sh`
- `scripts/build-tarball.sh`

Workflow собирает `cliphistory_<version>_all.deb`, `cliphistory-<version>.tar.gz` и checksum-файл, проверяет версию через `dpkg-deb`/`sha256sum`, затем публикует их как GitHub Actions artifacts. В git при этом попадают только исходники и workflow, а собранные пакеты доступны в конкретном запуске Actions.

### Запуск из VS Code

В проект добавлена рекомендация расширения `GitHub Actions` (`github.vscode-github-actions`). После установки расширения:

1. Откройте боковую панель GitHub Actions.
2. Выберите репозиторий `kabobik/ClipHistory`.
3. Откройте workflow `Build release packages`.
4. Нажмите `Run Workflow` и выберите ветку `master`.

Workflow можно запускать вручную благодаря `workflow_dispatch` в `.github/workflows/build-deb.yml`.

После завершения запуска скачайте пакеты в блоке `Artifacts` на странице workflow run.

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
