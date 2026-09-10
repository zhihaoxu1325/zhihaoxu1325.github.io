import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


CRAWLER_PATH = (
    Path(__file__).resolve().parents[1] / "google_scholar_crawler" / "main.py"
)


class _NetworkTrap:
    def search_author_id(self, _scholar_id):
        raise AssertionError("importing the crawler must not access Google Scholar")

    def fill(self, *_args, **_kwargs):
        raise AssertionError("importing the crawler must not access Google Scholar")


class _FakeScholarly:
    def __init__(self):
        self.timeout = None
        self.retries = None
        self.sections = None

    def set_timeout(self, timeout):
        self.timeout = timeout

    def set_retries(self, retries):
        self.retries = retries

    def search_author_id(self, scholar_id):
        return {
            "scholar_id": scholar_id,
            "name": "Example Researcher",
            "citedby": 12,
            "publications": [
                {
                    "author_pub_id": f"{scholar_id}:paper-one",
                    "num_citations": 7,
                    "bib": {"title": "A Useful Paper"},
                }
            ],
        }

    def fill(self, _author, sections):
        self.sections = sections


def load_crawler():
    fake_scholarly = types.ModuleType("scholarly")
    fake_scholarly.scholarly = _NetworkTrap()
    spec = importlib.util.spec_from_file_location("citation_crawler_under_test", CRAWLER_PATH)
    module = importlib.util.module_from_spec(spec)

    with mock.patch.dict(os.environ, {"GOOGLE_SCHOLAR_ID": "test-author"}), mock.patch.dict(
        sys.modules, {"scholarly": fake_scholarly}
    ):
        spec.loader.exec_module(module)

    return module


class CitationCrawlerImportTests(unittest.TestCase):
    def test_import_does_not_fetch_or_write_results(self):
        original_directory = os.getcwd()
        with tempfile.TemporaryDirectory() as temporary_directory:
            try:
                os.chdir(temporary_directory)
                load_crawler()
                self.assertFalse(Path("results").exists())
            finally:
                os.chdir(original_directory)


class DependencyCompatibilityTests(unittest.TestCase):
    def test_scholarly_imports_with_pinned_dependencies(self):
        from scholarly import scholarly

        self.assertTrue(callable(scholarly.search_author_id))


class CitationFetchTests(unittest.TestCase):
    def test_fetch_is_bounded_and_normalizes_publications(self):
        crawler = load_crawler()
        scholarly_client = _FakeScholarly()

        author = crawler.fetch_author(
            "test-author",
            scholarly_client=scholarly_client,
            updated_at="2026-09-10T12:00:00+00:00",
        )

        self.assertEqual(scholarly_client.timeout, 10)
        self.assertEqual(scholarly_client.retries, 2)
        self.assertEqual(
            scholarly_client.sections,
            ["basics", "indices", "counts", "publications"],
        )
        self.assertEqual(author["updated"], "2026-09-10T12:00:00+00:00")
        self.assertEqual(
            list(author["publications"]),
            ["test-author:paper-one"],
        )


class ResultWritingTests(unittest.TestCase):
    def test_write_results_emits_frontend_and_badge_json(self):
        crawler = load_crawler()
        author = {
            "scholar_id": "test-author",
            "name": "Example Researcher",
            "citedby": 12,
            "publications": {
                "test-author:paper-one": {
                    "author_pub_id": "test-author:paper-one",
                    "num_citations": 7,
                    "bib": {"title": "A Useful Paper"},
                }
            },
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory) / "results"
            crawler.write_results(
                author,
                output_directory,
                expected_scholar_id="test-author",
            )

            with (output_directory / "gs_data.json").open() as input_file:
                self.assertEqual(json.load(input_file), author)
            with (output_directory / "gs_data_shieldsio.json").open() as input_file:
                self.assertEqual(
                    json.load(input_file),
                    {"schemaVersion": 1, "label": "citations", "message": "12"},
                )

    def test_invalid_fetch_does_not_overwrite_last_known_good_results(self):
        crawler = load_crawler()

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory) / "results"
            output_directory.mkdir()
            data_path = output_directory / "gs_data.json"
            data_path.write_text('{"citedby": 11}', encoding="utf-8")

            with self.assertRaises(ValueError):
                crawler.write_results(
                    {
                        "scholar_id": "test-author",
                        "citedby": 12,
                        "publications": {},
                    },
                    output_directory,
                    expected_scholar_id="test-author",
                )

            self.assertEqual(data_path.read_text(encoding="utf-8"), '{"citedby": 11}')

    def test_wrong_profile_does_not_overwrite_last_known_good_results(self):
        crawler = load_crawler()
        author = {
            "scholar_id": "wrong-author",
            "citedby": 12,
            "publications": {
                "wrong-author:paper-one": {
                    "author_pub_id": "wrong-author:paper-one",
                    "num_citations": 7,
                    "bib": {"title": "A Useful Paper"},
                }
            },
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory) / "results"
            output_directory.mkdir()
            data_path = output_directory / "gs_data.json"
            data_path.write_text('{"citedby": 11}', encoding="utf-8")

            with self.assertRaises(ValueError):
                crawler.write_results(
                    author,
                    output_directory,
                    expected_scholar_id="test-author",
                )

            self.assertEqual(data_path.read_text(encoding="utf-8"), '{"citedby": 11}')


if __name__ == "__main__":
    unittest.main()
