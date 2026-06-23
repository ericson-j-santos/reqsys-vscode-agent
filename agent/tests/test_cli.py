from reqsys_agent.cli import main


def test_health():
    assert main(["health"]) == 0


def test_inspect(tmp_path):
    assert main(["inspect", "--workspace", str(tmp_path)]) == 0


def test_governance(tmp_path):
    assert main(["governance", "--workspace", str(tmp_path)]) == 0


def test_index_uses_allowed_paths_and_creates_manifest(tmp_path):
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=blocked\n", encoding="utf-8")
    (tmp_path / ".reqsys-agent.json").write_text(
        '{"project":"demo","mode":"safe-readonly","allowedPaths":["README.md"],"blockedActions":["read-secrets"]}',
        encoding="utf-8",
    )

    assert main(["index", "--workspace", str(tmp_path)]) == 0

    index_file = tmp_path / ".reqsys" / "agent-index" / "index.json"
    assert index_file.exists()
    content = index_file.read_text(encoding="utf-8")
    assert "README.md" in content
    assert "SECRET=blocked" not in content
