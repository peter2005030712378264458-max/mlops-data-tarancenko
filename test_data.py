import tempfile
import unittest
from pathlib import Path

import pandas as pd

from check_data import check_data, sha256_file
from prepare_data import prepare_data


class DataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / "data"
        prepare_data("base", self.data)

    def test_versions_and_repeatability(self):
        for mode in ("base", "wine", "iris_features"):
            path = prepare_data(mode, self.data)
            first_hash = sha256_file(path)
            prepare_data(mode, self.data)
            self.assertEqual(first_hash, sha256_file(path))

        result = check_data(self.data, "merged")
        self.assertEqual([(item["rows"], item["columns"]) for item in result], [(150, 7), (178, 14)])

    def test_wine_preserves_iris(self):
        original_hash = sha256_file(self.data / "iris.csv")
        prepare_data("wine", self.data)
        self.assertEqual(original_hash, sha256_file(self.data / "iris.csv"))
        check_data(self.data, "wine")

    def test_features_without_wine(self):
        prepare_data("iris_features", self.data)
        check_data(self.data, "iris_features")
        self.assertFalse((self.data / "wine.csv").exists())

    def test_missing_file(self):
        with self.assertRaises(ValueError):
            check_data(self.data, "wine")

    def test_index_column(self):
        path = self.data / "iris.csv"
        pd.read_csv(path).to_csv(path, index=True)
        with self.assertRaisesRegex(ValueError, "столбец индекса"):
            check_data(self.data, "base")

    def test_wrong_row_count(self):
        path = self.data / "iris.csv"
        pd.read_csv(path).iloc[:-1].to_csv(path, index=False)
        with self.assertRaisesRegex(ValueError, "форма"):
            check_data(self.data, "base")

    def test_wrong_feature(self):
        path = prepare_data("iris_features", self.data)
        frame = pd.read_csv(path)
        frame.loc[0, "sepal_area"] += 1
        frame.to_csv(path, index=False)
        with self.assertRaisesRegex(ValueError, "sepal_area"):
            check_data(self.data, "iris_features")


if __name__ == "__main__":
    unittest.main()
