import csv
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

from simplifiapi.cli import main, parse_arguments, write_data
from simplifiapi.client import Client


class TestParseArguments:
    def test_no_args_defaults(self):
        options = parse_arguments([])
        assert options.filename == "output"
        assert options.format == "json"
        assert options.accounts is False
        assert options.transactions is False
        assert options.tags is False
        assert options.categories is False
        assert options.email is None
        assert options.password is None
        assert options.token is None

    def test_custom_filename_and_format(self):
        options = parse_arguments(["--filename", "mydata", "--format", "csv"])
        assert options.filename == "mydata"
        assert options.format == "csv"

    def test_accounts_flag(self):
        options = parse_arguments(["--accounts"])
        assert options.accounts is True

    def test_multiple_flags(self):
        options = parse_arguments(["--accounts", "--transactions", "--categories"])
        assert options.accounts is True
        assert options.transactions is True
        assert options.categories is True
        assert options.tags is False

    def test_email_and_password(self):
        options = parse_arguments(["--email", "a@b.com", "--password", "secret"])
        assert options.email == "a@b.com"
        assert options.password == "secret"

    def test_token(self):
        options = parse_arguments(["--token", "tok-123"])
        assert options.token == "tok-123"


class TestWriteData:
    def test_write_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            options = parse_arguments(["--filename", "test", "--format", "json"])
            data = [{"id": 1, "name": "foo"}, {"id": 2, "name": "bar"}]
            write_data(options, data, "accounts")
            with open("test_accounts.json") as f:
                written = json.load(f)
            assert written == data

    def test_write_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            options = parse_arguments(["--filename", "test", "--format", "csv"])
            data = [{"id": 1, "name": "foo"}, {"id": 2, "name": "bar"}]
            write_data(options, data, "accounts")
            with open("test_accounts.csv") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            assert rows == [{"id": "1", "name": "foo"}, {"id": "2", "name": "bar"}]

    def test_write_csv_nested_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            options = parse_arguments(["--filename", "test", "--format", "csv"])
            data = [{"id": 1, "nested": {"key": "val"}, "tags": ["a", "b"]}]
            write_data(options, data, "stuff")
            with open("test_stuff.csv") as f:
                rows = list(csv.DictReader(f))
            assert rows[0]["id"] == "1"
            assert json.loads(rows[0]["nested"]) == {"key": "val"}
            assert json.loads(rows[0]["tags"]) == ["a", "b"]

    def test_write_csv_empty_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            options = parse_arguments(["--filename", "test", "--format", "csv"])
            write_data(options, [], "empty")
            assert not os.path.exists("test_empty.csv")

    def test_write_csv_with_mixed_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            options = parse_arguments(["--filename", "test", "--format", "csv"])
            data = [{"a": 1}, {"b": 2}, {"a": 3, "b": 4}]
            write_data(options, data, "mixed")
            with open("test_mixed.csv") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            assert reader.fieldnames == ["a", "b"]
            assert rows[0]["a"] == "1"
            assert rows[0]["b"] == ""
            assert rows[1]["a"] == ""
            assert rows[1]["b"] == "2"

    def test_write_json_empty_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            options = parse_arguments(["--filename", "test", "--format", "json"])
            write_data(options, [], "empty")
            with open("test_empty.json") as f:
                written = json.load(f)
            assert written == []

    def test_filename_prefix_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            options = parse_arguments(["--filename", "myprefix", "--format", "json"])
            write_data(options, [{"x": 1}], "txns")
            assert os.path.exists("myprefix_txns.json")


class TestMain:
    def test_main_get_token_fails(self):
        with patch("simplifiapi.cli.Client") as MockClient:
            instance = MockClient.return_value
            instance.get_token.return_value = None
            with patch("sys.argv", ["simplifiapi", "--accounts"]):
                main()
            instance.verify_token.assert_not_called()

    def test_main_verify_token_fails(self):
        with patch("simplifiapi.cli.Client") as MockClient:
            instance = MockClient.return_value
            instance.get_token.return_value = "fake-token"
            instance.verify_token.return_value = False
            with patch("sys.argv", ["simplifiapi", "--accounts"]):
                main()
            instance.verify_token.assert_called_once_with("fake-token")

    def test_main_no_datasets(self):
        with patch("simplifiapi.cli.Client") as MockClient:
            instance = MockClient.return_value
            instance.get_token.return_value = "fake-token"
            instance.verify_token.return_value = True
            instance.get_datasets.return_value = []
            with patch("sys.argv", ["simplifiapi", "--accounts"]):
                main()
            instance.get_accounts.assert_not_called()

    def test_main_retrieves_accounts(self):
        with patch("simplifiapi.cli.Client") as MockClient, patch("simplifiapi.cli.write_data") as mock_write:
            instance = MockClient.return_value
            instance.get_token.return_value = "fake-token"
            instance.verify_token.return_value = True
            instance.get_datasets.return_value = [{"id": "ds1"}]
            instance.get_accounts.return_value = [{"name": "Checking"}]
            with patch("sys.argv", ["simplifiapi", "--accounts"]):
                main()
            instance.get_accounts.assert_called_once_with("ds1")
            mock_write.assert_called_once()

    def test_main_with_existing_token(self):
        with patch("simplifiapi.cli.Client") as MockClient, patch("simplifiapi.cli.write_data") as mock_write:
            instance = MockClient.return_value
            instance.verify_token.return_value = True
            instance.get_datasets.return_value = [{"id": "ds1"}]
            instance.get_accounts.return_value = []
            instance.get_transactions.return_value = []
            with patch("sys.argv", ["simplifiapi", "--token", "existing-tok", "--accounts", "--transactions"]):
                main()
            instance.get_token.assert_not_called()
            instance.get_accounts.assert_called_once_with("ds1")
            instance.get_transactions.assert_called_once_with("ds1")
            assert mock_write.call_count == 2

    def test_main_retrieves_all_types(self):
        with patch("simplifiapi.cli.Client") as MockClient, patch("simplifiapi.cli.write_data") as mock_write:
            instance = MockClient.return_value
            instance.get_token.return_value = "fake-token"
            instance.verify_token.return_value = True
            instance.get_datasets.return_value = [{"id": "ds1"}]
            instance.get_accounts.return_value = []
            instance.get_transactions.return_value = []
            instance.get_tags.return_value = []
            instance.get_categories.return_value = []
            with patch("sys.argv", ["simplifiapi", "--accounts", "--transactions", "--tags", "--categories"]):
                main()
            instance.get_accounts.assert_called_once_with("ds1")
            instance.get_transactions.assert_called_once_with("ds1")
            instance.get_tags.assert_called_once_with("ds1")
            instance.get_categories.assert_called_once_with("ds1")
            assert mock_write.call_count == 4


class TestMainModule:
    def test_main_module_import(self):
        from simplifiapi.__main__ import main as main_mod_main
        assert callable(main_mod_main)
