"""One-pass BF16 semantic proposals; GPU imports occur only after validation."""

import argparse
import json
import os
import platform
import time
from pathlib import Path

from datamate.binding_proposals import (
    BindingProposalConfig,
    proposal_schema,
    validate_cases,
    validate_proposal,
)
from infra.probe_process import atomic_json


def generate(request, destination):
    validate_cases(request["cases"])
    config = BindingProposalConfig.model_validate(request["config"])
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
        records=[],
        max_model_len=config.max_model_len,
        dtype="bfloat16",
        tp=1,
        prefix_cache=False,
        result_cache=False,
        pa_measured=False,
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
    evidence.update(status="loading", prompt_token_counts=lengths)
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
        max_num_seqs=1,
        max_num_batched_tokens=config.max_model_len,
        enforce_eager=True,
        enable_prefix_caching=False,
        gpu_memory_utilization=config.engine_memory_fraction(
            runtime["total_device_bytes"]
        ),
    )
    evidence.update(
        status="ready",
        engine_startup_seconds=time.perf_counter() - started,
        torch_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        torch_peak_reserved_bytes=torch.cuda.max_memory_reserved(),
    )
    atomic_json(destination, evidence)
    for case, prompt, length in zip(request["cases"], prompts, lengths, strict=True):
        sampling = SamplingParams(
            temperature=0,
            seed=0,
            max_tokens=config.max_tokens,
            structured_outputs=StructuredOutputsParams(json=proposal_schema(case)),
        )
        record = dict(
            case_id=case["id"],
            prompt_tokens=length,
            output_tokens=0,
            finish_reason="prompt_over_budget",
            text="",
            citation_valid=False,
        )
        if length + config.max_tokens <= config.max_model_len:
            started = time.perf_counter()
            generated = model.generate([prompt], sampling, use_tqdm=False)[0]
            output = generated.outputs[0]
            record.update(
                text=output.text,
                output_tokens=len(output.token_ids),
                finish_reason=output.finish_reason,
                duration_seconds=time.perf_counter() - started,
            )
            try:
                if output.finish_reason != "stop":
                    raise ValueError("truncated proposal")
                validate_proposal(output.text, case)
                record["citation_valid"] = True
            except (ValueError, TypeError):
                pass
        evidence["records"].append(record)
        evidence.update(
            status="running",
            torch_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
            torch_peak_reserved_bytes=torch.cuda.max_memory_reserved(),
        )
        atomic_json(destination, evidence)
    evidence["status"] = "completed"
    atomic_json(destination, evidence)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    generate(json.loads(Path(args.request).read_text("utf-8")), Path(args.output))


if __name__ == "__main__":
    main()
