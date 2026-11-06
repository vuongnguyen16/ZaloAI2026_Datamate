"""P2b GPU worker. Import-safe on CPU; actual GPU imports only in generate."""

import argparse
import json
import os
import platform
import time
from pathlib import Path

from datamate.intent_probe import (
    ContextProbeConfig,
    batch_schedule,
    intent_schema,
    validate_cases,
    validate_intent,
)
from infra.probe_process import atomic_json


def generate(request, destination):
    validate_cases(request["cases"])
    config = ContextProbeConfig.model_validate(request["config"])
    os.environ["VLLM_ENABLE_V1_MULTIPROCESSING"] = "0"
    import torch
    import vllm
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.sampling_params import StructuredOutputsParams

    runtime = dict(
        vllm=vllm.__version__,
        torch=torch.__version__,
        cuda=torch.version.cuda,
        python=platform.python_version(),
        device=torch.cuda.get_device_name(0),
        capability=list(torch.cuda.get_device_capability(0)),
        total_device_bytes=torch.cuda.get_device_properties(0).total_memory,
    )
    evidence = dict(
        status="tokenizing",
        runtime=runtime,
        max_model_len=config.max_model_len,
        max_tokens=config.max_tokens,
        dtype="bfloat16",
        tp=1,
        prefix_cache=False,
        result_cache=False,
        records=[],
        batches=[],
    )
    atomic_json(destination, evidence)
    if (
        runtime["vllm"] != "0.11.1"
        or runtime["torch"].split("+")[0] != "2.9.0"
        or runtime["cuda"] != "12.8"
        or runtime["python"] != "3.11.18"
        or runtime["capability"] != [12, 0]
    ):
        raise ValueError("runtime pins/sm_120 mismatch")
    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(
        request["model_dir"], local_files_only=True, trust_remote_code=False
    )
    prompts = [
        tokenizer.apply_chat_template(
            c["messages"],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        for c in request["cases"]
    ]
    lengths = [len(tokenizer.encode(p, add_special_tokens=False)) for p in prompts]
    eligible = sorted(
        (
            i
            for i, n in enumerate(lengths)
            if n + config.max_tokens <= config.max_model_len
        ),
        key=lambda i: (lengths[i], request["cases"][i]["id"]),
    )
    evidence.update(
        prompt_token_counts=lengths,
        eligible_cases=len(eligible),
        tokenization_seconds=time.perf_counter() - started,
    )
    if len(eligible) < 4:
        evidence["status"] = "insufficient_fitting_prompts"
        atomic_json(destination, evidence)
        return
    # Four length quantiles, identical workload for every batch size and repeat.
    indices = [eligible[(len(eligible) - 1) * j // 3] for j in range(4)]
    selected = [prompts[i] for i in indices]
    evidence["selected_indices"] = indices
    evidence["status"] = "loading"
    atomic_json(destination, evidence)
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    model = LLM(
        model=request["model_dir"],
        tokenizer=request["model_dir"],
        trust_remote_code=False,
        dtype="bfloat16",
        tensor_parallel_size=1,
        seed=0,
        max_model_len=config.max_model_len,
        max_num_seqs=4,
        max_num_batched_tokens=config.max_model_len,
        enforce_eager=True,
        enable_prefix_caching=False,
        gpu_memory_utilization=config.engine_memory_fraction(
            runtime["total_device_bytes"]
        ),
    )
    evidence["engine_startup_seconds"] = time.perf_counter() - started
    evidence.update(
        status="warming_up",
        torch_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        torch_peak_reserved_bytes=torch.cuda.max_memory_reserved(),
    )
    atomic_json(destination, evidence)
    sampling = SamplingParams(
        temperature=0,
        seed=0,
        max_tokens=config.max_tokens,
        structured_outputs=StructuredOutputsParams(json=intent_schema()),
    )
    started = time.perf_counter()
    model.generate([selected[0]], sampling, use_tqdm=False)
    evidence["warmup_seconds"] = time.perf_counter() - started
    evidence.update(
        status="ready",
        torch_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        torch_peak_reserved_bytes=torch.cuda.max_memory_reserved(),
    )
    atomic_json(destination, evidence)
    for repeat in (1, 2):
        for size in (1, 2, 4):
            started = time.perf_counter()
            outputs = []
            for batch in batch_schedule(4, size):
                generated = model.generate(
                    [selected[i] for i in batch], sampling, use_tqdm=False
                )
                for i, result in zip(batch, generated, strict=True):
                    output = result.outputs[0]
                    try:
                        validate_intent(output.text)
                        valid = True
                    except (ValueError, TypeError):
                        valid = False
                    record = dict(
                        repeat=repeat,
                        batch_size=size,
                        case_index=indices[i],
                        prompt_tokens=len(result.prompt_token_ids),
                        output_tokens=len(output.token_ids),
                        text=output.text,
                        finish_reason=output.finish_reason,
                        json_valid=valid,
                    )
                    outputs.append(record)
            duration = time.perf_counter() - started
            evidence["records"].extend(outputs)
            evidence["batches"].append(
                dict(
                    repeat=repeat,
                    batch_size=size,
                    requests=4,
                    duration_seconds=duration,
                    requests_per_second=4 / duration,
                    prompt_tokens=sum(x["prompt_tokens"] for x in outputs),
                    output_tokens=sum(x["output_tokens"] for x in outputs),
                    output_tokens_per_second=sum(x["output_tokens"] for x in outputs)
                    / duration,
                )
            )
            evidence.update(
                status="running",
                torch_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                torch_peak_reserved_bytes=torch.cuda.max_memory_reserved(),
            )
            atomic_json(destination, evidence)
    bycase = {}
    for record in evidence["records"]:
        bycase.setdefault(record["case_index"], set()).add(record["text"])
    evidence.update(
        status="completed",
        json_valid=all(r["json_valid"] for r in evidence["records"]),
        repeat_and_batch_invariant=all(len(v) == 1 for v in bycase.values()),
    )
    atomic_json(destination, evidence)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    generate(json.loads(Path(args.request).read_text("utf-8")), Path(args.output))


if __name__ == "__main__":
    main()
