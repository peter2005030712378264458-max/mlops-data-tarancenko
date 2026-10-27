import json
import re
import sys
from datetime import datetime
from pathlib import Path

from clearml import Dataset

from check_data import check_data
from prepare_data import prepare_data


def main():
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("По заданию нужен Python 3.12")

    root = Path(__file__).resolve().parent
    report_path = root / "REPORT.md"
    report = report_path.read_text()
    ids = dict(re.findall(r"^(BASE_ID|WINE_ID|IRIS_FEATURES_ID): `([^`]+)`$", report, re.MULTILINE))
    before, heading, rest = report.partition("## ClearML\n")
    _, next_heading, after = rest.partition("## Сравнение\n")
    if not heading or not next_heading:
        raise RuntimeError("В REPORT.md не найдены разделы ClearML и Сравнение")
    details = []

    def save_report():
        lines = [f"{key}: `{value}`" for key, value in ids.items()]
        section = "\n\n".join(lines + details)
        report_path.write_text(before + heading + "\n" + section + "\n\n" + next_heading + after)

    def create_version(key, version, path, description, parent_id=None, tags=None):
        if key in ids:
            dataset = Dataset.get(dataset_id=ids[key])
        else:
            dataset = Dataset.create(
                dataset_project="MIIT/MLOps/practice_3/tarancenko",
                dataset_name="sklearn-tabular-tarancenko",
                dataset_version=version,
                parent_datasets=[parent_id] if parent_id else [],
                dataset_tags=tags or [],
                description=description,
            )
            ids[key] = dataset.id
            save_report()

        if not dataset.is_final():
            dataset.add_files(path=str(path))
            dataset.upload()
            dataset.finalize()
        print(f"{key}: {dataset.id}", flush=True)
        return dataset

    sources = root / "clearml_sources"
    base_dir = sources / "base"
    wine_dir = sources / "wine"
    features_dir = sources / "iris_features"
    prepare_data("base", base_dir)
    prepare_data("base", wine_dir)
    prepare_data("wine", wine_dir)
    prepare_data("iris_features", features_dir)
    expected = {
        "base": check_data(base_dir, "base"),
        "wine": check_data(wine_dir, "wine"),
        "iris_features": check_data(features_dir, "iris_features"),
    }

    base = create_version(
        "BASE_ID", "1.0.0", base_dir / "iris.csv",
        "Исходный Iris из scikit-learn", tags=["base"],
    )
    wine = create_version(
        "WINE_ID", "1.1.0", wine_dir / "wine.csv",
        "Добавлен Wine, исходный Iris унаследован от базы", parent_id=base.id,
    )
    features = create_version(
        "IRIS_FEATURES_ID", "2.0.0", features_dir / "iris.csv",
        "В Iris добавлены sepal_area и petal_area, без Wine", parent_id=base.id,
    )

    downloads = root / "downloads" / datetime.now().strftime("%Y%m%d-%H%M%S")
    versions = [
        (base.id, "1.0.0", "base", [], ["iris.csv"], []),
        (wine.id, "1.1.0", "wine", [base.id], ["wine.csv"], []),
        (features.id, "2.0.0", "iris_features", [base.id], [], ["iris.csv"]),
    ]
    for dataset_id, version, mode, parents, added, modified in versions:
        dataset = Dataset.get(dataset_id=dataset_id, only_completed=True)
        graph = dataset.get_dependency_graph()
        assert dataset.is_final()
        assert dataset.version == version
        assert graph[dataset.id] == parents
        assert dataset.list_added_files() == added
        assert dataset.list_modified_files() == modified
        assert dataset.list_removed_files() == []
        if mode == "iris_features":
            assert wine.id not in graph

        folder = downloads / mode
        dataset.get_mutable_local_copy(target_folder=str(folder), overwrite=False)
        files = check_data(folder, mode)
        assert files == expected[mode]
        assert dataset.list_files() == sorted(Path(item["path"]).name for item in files)

        lines = [
            f"### Версия {version}", "",
            f"Dataset ID: `{dataset.id}`. Статус: Completed.",
            f"Parent IDs: `{json.dumps(parents)}`.",
            f"Files: `{json.dumps(dataset.list_files())}`.",
            f"Added: `{json.dumps(added)}`; modified: `{json.dumps(modified)}`; removed: `[]`.",
            f"Dependency graph: `{json.dumps(graph)}`.",
            f"Скачано в `{folder.relative_to(root)}`. Проверка данных и SHA-256 пройдена.",
            "", "| Файл | Форма | SHA-256 |", "|---|---|---|",
        ]
        for item in files:
            lines.append(
                f"| {item['path']} | {item['rows']} × {item['columns']} | `{item['sha256']}` |"
            )
        for item in files:
            lines += ["", f"Столбцы `{item['path']}`: " + ", ".join(item["column_names"]) + "."]
        details.append("\n".join(lines))
        save_report()

    report = report_path.read_text()
    report = report.replace(
        "Наблюдения DVC получены при выполнении. Столбец ClearML приведён справочно:\n"
        "проверку на сервере ещё нужно выполнить.",
        "Версии ClearML созданы, скачаны по ID и проверены. Результаты приведены выше.",
    )
    report = report.replace("ClearML: справочно", "ClearML: наблюдение")
    observations = {
        "Dataset ID; version — читаемая метка": "Получены три разных ID для 1.0.0, 1.1.0 и 2.0.0",
        "ClearML Server": "Списки файлов и parent IDs получены через Dataset.get по ID",
        "File Server или внешний storage": "Файлы загружены через upload и получены в пустые папки",
        "Новый Dataset с parent ID": "Версия Wine создана с BASE_ID и загрузкой только wine.csv",
        "Получение Dataset по ID": "Все три версии запрошены по сохранённым ID после создания 2.0.0",
        "Скачивание по ID при доступном storage": "Копии скачаны в новые папки; отдельная машина не проверялась",
        "Две версии с одним parent": "Обе дочерние версии имеют единственного родителя BASE_ID",
        "Отдельный Dataset с несколькими parents или подготовленным результатом": "Слияние не выполнялось; проверены две независимые ветви",
        "Git-коммит можно записать отдельно в метаданные": "Версии получены по ID без переключения Git",
        "Web UI показывает версии и lineage": "SDK вывел ссылки на созданные Dataset; UI проверяется отдельно",
    }
    for old, new in observations.items():
        report = report.replace(f"| {old} |", f"| {new} |")
    report = report.replace(
        "В этой работе такая проверка пока не выполнялась.",
        "Проверка выполнена по dependency graph скачанной версии.",
    )
    report = report.replace(
        "практическое сравнение будет дополнено после его запуска.",
        "выполненная проверка подтвердила получение каждой версии по отдельному ID.",
    )
    report_path.write_text(report)
    print("Готово. Результаты записаны в REPORT.md.")


if __name__ == "__main__":
    main()
