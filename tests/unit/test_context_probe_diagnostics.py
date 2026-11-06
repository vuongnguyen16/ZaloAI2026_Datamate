import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from datamate.intent_probe import intent_schema, make_case, validate_intent


def test_filter_element_bound_is_in_schema_and_parser():
    value = dict(
        operation="abstain",
        period_text="",
        comparison_text="",
        filter_texts=["x" * 257],
        reason="",
    )
    with pytest.raises(ValueError):
        validate_intent(json.dumps(value))
    assert intent_schema()["properties"]["filter_texts"]["items"]["maxLength"] == 256


def test_warmup_failure_preserves_completed_initialization(tmp_path, monkeypatch):
    from infra.p1_runtime.context_generate import generate

    cuda = SimpleNamespace(
        get_device_name=lambda _: "synthetic",
        get_device_capability=lambda _: (12, 0),
        get_device_properties=lambda _: SimpleNamespace(total_memory=96 * 1024**3),
        reset_peak_memory_stats=lambda: None,
        max_memory_allocated=lambda: 123,
        max_memory_reserved=lambda: 456,
    )
    torch = SimpleNamespace(
        __version__="2.9.0", version=SimpleNamespace(cuda="12.8"), cuda=cuda
    )
    tokenizer = SimpleNamespace(
        apply_chat_template=lambda *a, **k: "prompt", encode=lambda *a, **k: [1] * 100
    )

    class Model:
        def generate(self, *a, **k):
            raise RuntimeError("synthetic warmup failure")

    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(
        sys.modules,
        "vllm",
        SimpleNamespace(
            __version__="0.11.1",
            LLM=lambda **k: Model(),
            SamplingParams=SimpleNamespace,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "vllm.sampling_params",
        SimpleNamespace(StructuredOutputsParams=SimpleNamespace),
    )
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            AutoTokenizer=SimpleNamespace(from_pretrained=lambda *a, **k: tokenizer)
        ),
    )
    monkeypatch.setenv("VLLM_ENABLE_V1_MULTIPROCESSING", "0")
    cases = [
        make_case(
            dict(
                id=f"synthetic_{i}",
                business_id="synthetic_b",
                question="Total?",
                as_of_date="2026-11-07",
            ),
            {"tables": []},
        )
        for i in range(4)
    ]
    config = dict(
        profile="vuonghungnguyen07",
        workspace="vuonghungnguyen07",
        budget_usd=30.0,
        estimated_cost_usd=20.0,
        gpu="RTX-PRO-6000",
        memory_budget_bytes=32212254720,
        seed=0,
        max_model_len=4096,
        max_tokens=256,
        gpu_timeout_seconds=1200,
        startup_timeout_seconds=600,
        staging_timeout_seconds=300,
    )
    path = tmp_path / "output.json"
    with pytest.raises(RuntimeError, match="warmup"):
        generate(dict(config=config, cases=cases, model_dir="synthetic"), path)
    evidence = json.loads(path.read_text("utf-8"))
    assert evidence["status"] == "warming_up"
    assert evidence["engine_startup_seconds"] >= 0
    assert evidence["torch_peak_reserved_bytes"] == 456


def test_snapshot_failure_checkpoint_preserves_bounded_sanitized_stderr(
    tmp_path, monkeypatch
):
    from infra.context_probe_process import verify_context_snapshot

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(
            1, args[0], stderr=b"Authorization: secret-value\n" + b"x" * 6000
        )

    monkeypatch.setattr(subprocess, "run", fail)
    path = tmp_path / "snapshot.json"
    with pytest.raises(ValueError, match="snapshot verification"):
        verify_context_snapshot({"files": {"synthetic": "0" * 64}}, tmp_path, path)
    value = json.loads(path.read_text("utf-8"))
    assert value["status"] == "snapshot_verification_failed"
    assert "secret-value" not in path.read_text("utf-8")
    assert 0 < len(value["diagnostic"]) <= 4096
