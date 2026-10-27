# Практическая работа 3

## Окружение

Нужны Python 3.12, Poetry и Git.

```bash
poetry env use python3.12
poetry install
```

## Данные

```bash
poetry run python prepare_data.py base
poetry run python check_data.py --version base
poetry run python prepare_data.py wine
poetry run python check_data.py --version wine
poetry run python prepare_data.py iris_features
poetry run python check_data.py --version merged
```

Каждый режим записывает только свой CSV. Состояние `iris_features` без Wine
получается при запуске из базовой версии в отдельной ветке.

## Восстановление DVC

Локальный remote — соседняя папка `dvc-remote-tarancenko`.
Для нового клона в той же родительской директории:

```bash
poetry install
poetry run dvc pull
poetry run python check_data.py
```

При другом расположении хранилища:

```bash
poetry run dvc remote modify --local storage url /path/to/dvc-remote-tarancenko
```

Переключение на базовую версию и обратно:

```bash
git switch --detach data-v1
poetry run dvc remote add --local --force -d recovery ../dvc-remote-tarancenko
poetry run dvc pull
poetry run python check_data.py --version base
git switch main
poetry run dvc checkout
poetry run python check_data.py
```

Тег `data-v1` создан до настройки remote. Поэтому для него адрес хранилища
задаётся в локальной конфигурации, которая не меняется при переключении Git.

Настройка merge driver в новом клоне:

```bash
git config merge.dvc.name "DVC merge driver"
git config merge.dvc.driver "poetry run dvc git-hook merge-driver --ancestor %O --our %A --their %B"
```

CSV и cache в Git не входят. Для восстановления на другой машине ей нужен
доступ к содержимому DVC remote.

## ClearML

После `clearml-init` в активированном окружении Python 3.12:

```bash
python clearml_versions.py
```

Скрипт создаёт три версии, скачивает их и записывает IDs и результаты проверок
в `REPORT.md`. Ключи читает из пользовательских настроек ClearML.
При повторном запуске использует IDs, уже записанные в отчёт.
Исходные CSV сохраняет в `clearml_sources`, скачанные — в `downloads`.
