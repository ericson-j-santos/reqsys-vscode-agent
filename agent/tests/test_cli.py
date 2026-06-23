from reqsys_agent.cli import main


def test_health():
    assert main(["health"]) == 0


def test_inspect(tmp_path):
    assert main(["inspect", "--workspace", str(tmp_path)]) == 0


def test_governance(tmp_path):
    assert main(["governance", "--workspace", str(tmp_path)]) == 0


def test_build_index(tmp_path):
    (tmp_path / "README.md").write_text("# ReqSys\n\nWorkflow documentation.", encoding="utf-8")
    assert main(["build-index", "--workspace", str(tmp_path)]) == 0
    assert (tmp_path / ".reqsys" / "index.json").exists()


def test_ask(tmp_path):
    (tmp_path / "README.md").write_text("# ReqSys\n\nCI workflows and guardrails.", encoding="utf-8")
    assert main(["ask", "--workspace", str(tmp_path), "--question", "Quais workflows existem?"]) == 0
