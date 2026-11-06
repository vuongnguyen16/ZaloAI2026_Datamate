"""One fresh vLLM engine process. GPU libraries are imported only by main()."""

import argparse
import json
import os
import re
import time
from pathlib import Path

from datamate.model_probe import ProbeConfig


def validate_request(request: dict) -> None:
    repo, revision = request.get("repository", ""), request.get("revision", "")
    if not re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", repo) or not re.fullmatch(
        r"[0-9a-f]{40}", revision
    ):
        raise ValueError("invalid immutable model identity")
    expected_path = Path("/weights") / repo.replace("/", "--") / revision
    if Path(request.get("model_dir", "")) != expected_path:
        raise ValueError("model path must be the pinned weights mount")
    cases = request.get("cases", [])
    if len(cases) != 50 or len({c.get("id") for c in cases}) != 50:
        raise ValueError("50 unique synthetic inputs required")
    if any(
        set(c) != {"id", "prompt"}
        or not all(isinstance(v, str) and v for v in c.values())
        for c in cases
    ):
        raise ValueError("inference payload may contain only id and prompt")


def output_schema() -> dict:
    scalar = {"anyOf": [{"type": "string"}, {"type": "number"}]}
    table = {
        "type": "object",
        "properties": {
            "columns": {"type": "array", "items": {"type": "string"}},
            "rows": {"type": "array", "items": {"type": "array", "items": scalar}},
        },
        "required": ["columns", "rows"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "type": {
                "type": "string",
                "enum": [
                    "number",
                    "percent",
                    "string",
                    "date",
                    "boolean",
                    "list",
                    "table",
                    "unanswerable",
                    "abstain",
                ],
            },
            "answer": {
                "anyOf": [
                    {"type": "number"},
                    {"type": "string"},
                    {"type": "boolean"},
                    {"type": "array", "items": scalar},
                    table,
                    {"type": "null"},
                ]
            },
        },
        "required": ["id", "type"],
        "additionalProperties": False,
    }


def generate(request: dict, destination: Path) -> None:
    validate_request(request)
    config = ProbeConfig.model_validate(request["config"])
    for key, value in {
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "VLLM_NO_USAGE_STATS": "1",
        "DO_NOT_TRACK": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "VLLM_ENABLE_V1_MULTIPROCESSING": "0",
    }.items():
        os.environ[key] = value
    import torch
    import vllm
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams

    runtime = {
        "vllm": vllm.__version__,
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "device": torch.cuda.get_device_name(0),
        "device_capability": list(torch.cuda.get_device_capability(0)),
        "total_device_bytes": torch.cuda.get_device_properties(0).total_memory,
    }
    correct_pins = (
        runtime["vllm"] == "0.11.1"
        and runtime["torch"].split("+")[0] == "2.9.0"
        and runtime["cuda"] == "12.8"
    )
    evidence = {
        "runtime": runtime,
        "runtime_pins_verified": correct_pins,
        "records": [],
        "status": "loading",
    }
    destination.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")
    if not correct_pins or runtime["device_capability"] != [12, 0]:
        raise ValueError("actual runtime pins or sm_120 do not match")
    torch.cuda.reset_peak_memory_stats()
    tokenizer = AutoTokenizer.from_pretrained(
        request["model_dir"], local_files_only=True, trust_remote_code=False
    )
    model = LLM(
        model=request["model_dir"],
        tokenizer=request["model_dir"],
        trust_remote_code=False,
        dtype="bfloat16",
        tensor_parallel_size=1,
        seed=0,
        max_model_len=config.max_model_len,
        max_num_seqs=1,
        max_num_batched_tokens=config.max_model_len,
        enforce_eager=True,
        enable_prefix_caching=False,
        gpu_memory_utilization=config.memory_budget_bytes
        / runtime["total_device_bytes"],
    )
    sampling = SamplingParams(
        temperature=0,
        seed=0,
        max_tokens=config.max_tokens,
        structured_outputs=StructuredOutputsParams(json=output_schema()),
    )
    for case in request["cases"]:
        message = [
            {
                "role": "system",
                "content": "Return only a JSON object with id, type and answer when applicable. Follow the requested type. Do not include reason or markdown.",
            },
            {
                "role": "user",
                "content": f"Correlation id: {case['id']}\n{case['prompt']}",
            },
        ]
        kwargs = (
            {"enable_thinking": False}
            if request["repository"] == "Qwen/Qwen3-14B"
            else {}
        )
        prompt = tokenizer.apply_chat_template(
            message, tokenize=False, add_generation_prompt=True, **kwargs
        )
        started = time.perf_counter()
        result = model.generate([prompt], sampling, use_tqdm=False)[0].outputs[0]
        evidence["records"].append(
            {
                "id": case["id"],
                "text": result.text,
                "token_ids": list(result.token_ids),
                "finish_reason": result.finish_reason,
                "duration_seconds": time.perf_counter() - started,
            }
        )
        evidence.update(
            torch_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
            torch_peak_reserved_bytes=torch.cuda.max_memory_reserved(),
            status="running",
        )
        destination.write_text(
            json.dumps(evidence, ensure_ascii=False, allow_nan=False), encoding="utf-8"
        )
    evidence["status"] = "completed"
    destination.write_text(
        json.dumps(evidence, ensure_ascii=False, allow_nan=False), encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    generate(json.loads(Path(args.request).read_text("utf-8")), Path(args.output))


if __name__ == "__main__":
    main()
