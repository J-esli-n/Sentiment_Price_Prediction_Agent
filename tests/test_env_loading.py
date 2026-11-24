import os

from sentipipe.providers import load_local_env


def test_local_env_loads_example_without_overriding_existing_environment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    monkeypatch.setenv("APIFY_API_TOKEN", "already-set")
    (tmp_path / ".env.example").write_text(
        "APIFY_API_TOKEN=example-token\nEXA_API_KEY=example-key\n",
        encoding="utf-8",
    )

    load_local_env()

    assert os.environ["APIFY_API_TOKEN"] == "already-set"
    assert os.environ["EXA_API_KEY"] == "example-key"


def test_local_env_prefers_dotenv_values_to_example(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    monkeypatch.delenv("APIFY_API_TOKEN", raising=False)
    (tmp_path / ".env").write_text("EXA_API_KEY=local-key\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text(
        "EXA_API_KEY=example-key\nAPIFY_API_TOKEN=example-token\n",
        encoding="utf-8",
    )

    load_local_env()

    assert os.environ["EXA_API_KEY"] == "local-key"
    assert os.environ["APIFY_API_TOKEN"] == "example-token"
