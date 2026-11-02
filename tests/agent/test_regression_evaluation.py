"""Module 7's regression run is recorded as an evaluation (acceptance/lab/mlflow-regression-evaluation.feature).

The regression set runs exactly as before, then hands each case's trace and verdict to
mlflow.genai.evaluate with one deterministic code scorer ("check"), inside a run named after
--name. MLflow's evaluation view then shows one row per case with its trace and verdict, and
two evaluation runs can be compared.
"""
import re

import pytest

LINE = re.compile(r"^(PASS|FAIL|SKIP)\s+(\S+)\s", re.MULTILINE)


def tracking(tmp_path):
    return {"MLFLOW_TRACKING_URI": f"sqlite:///{tmp_path}/mlflow.db"}


def evaluation_runs(tmp_path):
    mlflow = pytest.importorskip("mlflow")
    mlflow.set_tracking_uri(tracking(tmp_path)["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment("kestrel-agent")
    return mlflow, mlflow.search_runs(experiment_names=["kestrel-agent"], output_format="list",
                                      order_by=["attributes.start_time ASC"])


def verdicts(mlflow, run):
    """{case: (verdict, reason)} from the "check" assessments on the run's traces."""
    found = {}
    for trace in mlflow.search_traces(run_id=run.info.run_id, return_type="list"):
        (check,) = [a for a in trace.info.assessments if a.name == "check"]
        case, reason = check.rationale.split(": ", 1)
        found[case] = (check.value, reason)
    return found


def printed(out):
    return {case: status for status, case in LINE.findall(out)}


def test_the_regression_run_is_recorded_as_an_evaluation(work, tmp_path):
    """Scenario: The regression run is recorded as an evaluation"""
    work.repoint_to_validated()
    out = work.run("regression.py", "--name", "my-baseline", env=tracking(tmp_path)).stdout
    mlflow, runs = evaluation_runs(tmp_path)
    (run,) = runs
    assert run.info.run_name == "my-baseline"
    assert run.data.tags.get("mlflow.runType") == "genai_evaluate"      # MLflow's evaluation view
    found = verdicts(mlflow, run)
    assert set(found) == set(printed(out)) and len(found) == 6          # one row per case
    assert {v for v, _ in found.values()} <= {"PASS", "FAIL", "SKIP"}
    assert all(reason for _, reason in found.values())
    # David (Q4): the run keeps the counts on the Runs tab.
    counts = {s: list(printed(out).values()).count(s) for s in ("PASS", "FAIL", "SKIP")}
    assert run.data.metrics == {"passed": counts["PASS"], "failed": counts["FAIL"], "skipped": counts["SKIP"]}
    assert f"Recorded MLflow run 'my-baseline' ({run.info.run_id})" in out


def test_mlflows_verdicts_match_the_terminals(work, tmp_path):
    """Scenario: MLflow's verdicts match the terminal's"""
    work.repoint_to_validated()
    work.apply_solution("module-03")
    out = work.run("regression.py", env=tracking(tmp_path)).stdout
    mlflow, (run,) = evaluation_runs(tmp_path)
    found = verdicts(mlflow, run)
    report = (sorted((work.path / "runs").glob("regression-*.md"))[-1]).read_text()
    in_report = {m.group(1): m.group(2) for m in re.finditer(r"^\| (\S+) \| [^|]+ \| (PASS|FAIL|SKIP) \|", report, re.MULTILINE)}
    assert {case: v for case, (v, _) in found.items()} == printed(out) == in_report
    for case, (_, reason) in found.items():
        assert reason in out                                            # the same reason, word for word


def test_a_later_run_can_be_compared_with_the_baseline(work, tmp_path):
    """Scenario: A later run can be compared with the baseline"""
    work.run("regression.py", "--name", "baseline-start", env=tracking(tmp_path))
    work.repoint_to_validated()
    work.apply_solution("module-05")
    work.run("regression.py", "--name", "after-fixes", env=tracking(tmp_path))
    mlflow, runs = evaluation_runs(tmp_path)
    assert [r.info.run_name for r in runs] == ["baseline-start", "after-fixes"]
    assert all(r.data.tags.get("mlflow.runType") == "genai_evaluate" for r in runs)
    before, after = (verdicts(mlflow, r) for r in runs)
    assert set(before) == set(after)                                    # every case in both
    changed = {case for case in before if before[case][0] != after[case][0]}
    assert {"m1", "m3", "m4"} <= changed                                # what the compare view shows


def test_without_tracing_the_regression_run_is_unchanged(work):
    """Scenario: Without tracing, the regression run is unchanged"""
    work.repoint_to_validated()
    out = work.run("regression.py", "--name", "my-baseline").stdout
    assert len(printed(out)) == 6
    assert "Report and checklist:" in out
    assert "mlflow" not in out.lower() and "evaluation" not in out.lower()
    assert list((work.path / "runs").glob("regression-*.md"))


def test_unreachable_mlflow_still_reports_every_case(work):
    """David, 2026-11-02 (Q5): when MLflow can't be reached, every case is still reported and the
    run says the evaluation wasn't recorded."""
    work.repoint_to_validated()
    out = work.run("regression.py", env={"MLFLOW_TRACKING_URI": "http://127.0.0.1:9"}).stdout
    assert len(printed(out)) == 6 and "Report and checklist:" in out
    assert "The evaluation wasn't recorded in MLflow" in out
