from app.evaluation import EvaluationHarness


def test_evaluation_harness_runs_traces():
    harness = EvaluationHarness()
    traces = [["I need a cognitive assessment for a mid-level Java engineer"], ["Compare SHL Cognitive Ability Test and SHL Java Programming Test"]]

    results = harness.run_traces(traces)

    assert len(results) == 2
    assert results[0]["recommendation_count"] >= 1
    assert results[1]["recommendation_count"] >= 2
