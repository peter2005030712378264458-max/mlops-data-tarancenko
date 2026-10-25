import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.datasets import load_iris, load_wine


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_data(data_dir=Path("data"), version="merged"):
    data_dir = Path(data_dir)
    expected_files = {"iris.csv"}
    if version in ("wine", "merged"):
        expected_files.add("wine.csv")

    actual_files = {path.name for path in data_dir.iterdir() if path.is_file()}
    if actual_files != expected_files:
        raise ValueError(f"Ожидались {sorted(expected_files)}, найдены {sorted(actual_files)}")

    results = []
    for filename in sorted(expected_files):
        path = data_dir / filename
        frame = pd.read_csv(path)
        if any(str(column).startswith("Unnamed:") for column in frame.columns):
            raise ValueError(f"{filename}: найден столбец индекса")

        source = load_iris if filename == "iris.csv" else load_wine
        original = source(as_frame=True).frame
        original = original.sort_values(list(original.columns), kind="mergesort")
        columns = list(original.columns)
        with_features = filename == "iris.csv" and version in ("iris_features", "merged")
        if with_features:
            columns += ["sepal_area", "petal_area"]

        if len(frame) != len(original) or list(frame.columns) != columns:
            raise ValueError(f"{filename}: неверная форма таблицы или порядок столбцов")
        if frame.isna().any().any():
            raise ValueError(f"{filename}: найдены пропуски")
        if not np.allclose(frame[list(original.columns)], original, rtol=1e-9, atol=1e-10):
            raise ValueError(f"{filename}: изменены исходные данные или порядок строк")

        if with_features:
            for prefix in ("sepal", "petal"):
                expected = frame[f"{prefix} length (cm)"] * frame[f"{prefix} width (cm)"]
                if not np.allclose(frame[f"{prefix}_area"], expected, rtol=1e-9, atol=1e-10):
                    raise ValueError(f"{filename}: неверные значения {prefix}_area")

        results.append({
            "path": f"{data_dir.name}/{filename}",
            "sha256": sha256_file(path),
            "rows": len(frame),
            "columns": len(frame.columns),
            "column_names": list(frame.columns),
            "missing": int(frame.isna().sum().sum()),
        })
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Проверка состава и содержимого CSV")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--version", choices=["base", "wine", "iris_features", "merged"], default="merged")
    args = parser.parse_args()
    try:
        result = check_data(args.data_dir, args.version)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Ошибка: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
