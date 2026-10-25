import argparse
from pathlib import Path

from sklearn.datasets import load_iris, load_wine


def prepare_data(mode, data_dir=Path("data")):
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    if mode == "wine":
        frame = load_wine(as_frame=True).frame
        filename = "wine.csv"
    else:
        frame = load_iris(as_frame=True).frame
        filename = "iris.csv"

    frame = frame.sort_values(list(frame.columns), kind="mergesort")
    if mode == "iris_features":
        frame["sepal_area"] = frame["sepal length (cm)"] * frame["sepal width (cm)"]
        frame["petal_area"] = frame["petal length (cm)"] * frame["petal width (cm)"]

    path = data_dir / filename
    frame.to_csv(path, index=False, lineterminator="\n", float_format="%.10g")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Подготовка Iris и Wine")
    parser.add_argument("mode", choices=["base", "wine", "iris_features"])
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    print(prepare_data(args.mode, args.data_dir))
