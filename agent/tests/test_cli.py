from reqsys_agent.cli import main


def test_health():
    assert main(["health"]) == 0


def test_runtime_deploy_contract():
    assert main(["runtime-deploy"]) == 0


def test_runtime_deploy_contract_by_environment():
    assert main(["runtime-deploy", "--environment", "staging"]) == 0


def test_runtime_artifact_contract():
    assert main(["runtime-artifact"]) == 0


def test_runtime_artifact_contract_by_environment():
    assert main(["runtime-artifact", "--environment", "staging"]) == 0


def test_runtime_public_contract():
    assert main(["runtime-public", "--app-name", "reqsys-vscode-agent"]) == 0


def test_runtime_public_contract_with_duckdns():
    assert main([
        "runtime-public",
        "--environment",
        "staging",
        "--app-name",
        "reqsys-vscode-agent",
        "--duckdns-hostname",
        "reqsys.duckdns.org",
    ]) == 0


def test_runtime_monitor_contract():
    assert main([
        "runtime-monitor",
        "--base-url",
        "https://reqsys-vscode-agent.fly.dev",
    ]) == 0


def test_runtime_monitor_contract_with_duckdns():
    assert main([
        "runtime-monitor",
        "--environment",
        "staging",
        "--base-url",
        "https://reqsys-vscode-agent.fly.dev",
        "--duckdns-url",
        "https://reqsys.duckdns.org",
    ]) == 0


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


def test_build_index(tmp_path):
    (tmp_path / "README.md").write_text("# ReqSys\n\nWorkflow documentation.", encoding="utf-8")
    assert main(["build-index", "--workspace", str(tmp_path)]) == 0
    assert (tmp_path / ".reqsys" / "index.json").exists()


def test_ask(tmp_path):
    (tmp_path / "README.md").write_text("# ReqSys\n\nCI workflows and guardrails.", encoding="utf-8")
    assert main(["ask", "--workspace", str(tmp_path), "--question", "Quais workflows existem?"]) == 0


def test_semantic_ask(tmp_path):
    (tmp_path / "README.md").write_text("# ReqSys\n\nCI workflows, quality gates and guardrails.", encoding="utf-8")
    assert main(["semantic-ask", "--workspace", str(tmp_path), "--question", "controle de qualidade de pipelines"]) == 0
