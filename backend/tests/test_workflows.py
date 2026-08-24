"""Guards on `.github/workflows/weekly-recaps.yml`.

The workflow is the redundant path for recap generation, so when it drifts the
symptom is invisible: `scheduled-sync.yml` keeps producing recaps either way.
These tests pin the two timing rules that are easy to reintroduce by hand.

Parsed as text rather than YAML on purpose: PyYAML reaches CI only as an
undeclared transitive dependency of uvicorn[standard], and the assertions below
are all on shell bodies and `if:` conditions, which stay strings either way.
"""

from pathlib import Path

import pytest

WORKFLOW = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "weekly-recaps.yml"
)


@pytest.fixture(scope="module")
def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def steps(workflow_text: str) -> dict[str, str]:
    """Split the workflow into {step name: step body}."""
    blocks: dict[str, str] = {}
    name = None
    lines: list[str] = []
    for line in workflow_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- name:"):
            if name is not None:
                blocks[name] = "\n".join(lines)
            name = stripped.removeprefix("- name:").strip()
            lines = []
        elif name is not None:
            lines.append(line)
    if name is not None:
        blocks[name] = "\n".join(lines)
    return blocks


def test_workflow_exists(workflow_text):
    assert workflow_text.strip(), f"{WORKFLOW} is empty or missing"


def test_status_step_derives_first_game_day_from_the_schedule(steps):
    """Thursday is only the usual opener - the day must come from Sleeper."""
    body = steps["Check NFL season status"]
    assert "schedule/nfl/regular/" in body
    assert "is_first_game_day=true" in body
    assert "is_first_game_day=false" in body


def test_status_step_evaluates_today_in_eastern_time(steps):
    """Sleeper's schedule dates are US Eastern, so UTC would be off by hours."""
    assert "TZ=America/New_York" in steps["Check NFL season status"]


def test_prediction_step_is_gated_on_the_first_game_day(steps):
    """Without the gate, the Thursday cron rewrites predictions after a
    Wednesday opener has already kicked off (2026 Week 1)."""
    name = next(n for n in steps if n.startswith("Generate predictions"))
    condition = steps[name].split("run:")[0]
    assert "is_first_game_day == 'true'" in condition
    # Tuesday still seeds predictions before any game has been played.
    assert "'0 10 * * 2'" in condition


def test_tuesday_recap_step_skips_week_one(steps):
    """Week 1 has no previous week; ungated this calls regenerate/0."""
    body = steps["Generate recaps (Tuesday only)"]
    assert '"$WEEK" -lt 2' in body
    assert body.index('"$WEEK" -lt 2') < body.index("PREV_WEEK=")


def test_recap_and_prediction_steps_fail_loudly(steps):
    """PR #106: a swallowed curl error hid a broken workflow for ~6 months."""
    for name, body in steps.items():
        if name.startswith(("Generate recaps", "Generate predictions")):
            assert "::error::" in body, f"{name} does not report failures"
            assert "exit 1" in body, f"{name} does not fail the run"
