from app.services.evaluation_service import DEFAULT_RECRUITER_PERSONA_TRACES, EvaluationHarness


def test_evaluation_harness_runs_traces():
    harness = EvaluationHarness()
    traces = [["I need a cognitive assessment for a mid-level Java engineer"], ["Compare SHL Cognitive Ability Test and SHL Java Programming Test"]]

    results = harness.run_traces(traces)

    assert len(results) == 2
    assert results[0]["recommendation_count"] >= 1
    assert results[1]["recommendation_count"] >= 2
    assert results[0]["state"] in {"recommending", "refining", "comparing", "clarifying", "refuse"}
    assert results[0]["reply_source"] in {"catalog", "groq"}


def test_evaluation_harness_runs_recruiter_persona_suite():
    harness = EvaluationHarness()

    results = harness.run_recruiter_persona_suite()

    assert set(results.keys()) == set(DEFAULT_RECRUITER_PERSONA_TRACES.keys())
    assert results["java_mid_cognitive"]["recommendation_count"] >= 1
    assert results["engineering_refinement"]["state"] == "refining"
    assert results["stakeholder_comparison"]["state"] == "comparing"
    assert results["vague_intake"]["state"] == "clarifying"
    assert results["out_of_scope_request"]["state"] == "refuse"
