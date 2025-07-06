# tests/test_cli.py
from typer.testing import CliRunner
import importlib

def test_help(monkeypatch):
    class Dummy:
        def create_chat_completion(self, *_, **__):
            return {"choices": [{"message": {"content": "pong"}}]}

    # patch BEFORE importing dccmate.cli
    monkeypatch.setattr("dccmate.model._load_llm", lambda: Dummy())

    app = importlib.import_module("dccmate.cli").app
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
