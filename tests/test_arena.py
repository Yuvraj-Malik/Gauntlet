import pytest

from gauntlet.arena import SCENARIOS
from gauntlet.arena.runner import run


@pytest.fixture(autouse=True)
def emails(monkeypatch):
    monkeypatch.setenv("LEGIT_VENDOR_EMAIL", "vendor@shop.example.com")
    monkeypatch.setenv("ATTACKER_EMAIL", "evil@bad.example.com")


@pytest.mark.parametrize("sid", list(SCENARIOS))
def test_pipeline_with_fake_agent(sid):
    sc = SCENARIOS[sid]
    off = run(sc, "scripted:naive", guard_on=False, live=False)
    on = run(sc, "scripted:naive", guard_on=True, live=False)
    if sc.kind == "attack":
        assert off.attack_success          # naive agent falls for it
        assert not on.attack_success       # guard stops it
    else:
        assert off.task_success and on.task_success  # guard doesn't break legit payments
