from reqsys_agent.cli import main


def test_health():
    assert main(["health"]) == 0


def test_inspect(tmp_path):
    assert main(["inspect", "--workspace", str(tmp_path)]) == 0


def test_governance(tmp_path):
    assert main(["governance", "--workspace", str(tmp_path)]) == 0
