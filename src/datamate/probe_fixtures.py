"""Synthetic format/repeatability probes; never BTC questions or a PA dataset."""

from copy import deepcopy

KINDS = (
    "number",
    "percent",
    "string",
    "date",
    "boolean",
    "list",
    "table",
    "unanswerable",
    "abstain",
)


def build_cases() -> list[dict]:
    cases = []
    for i in range(50):
        kind = KINDS[i % len(KINDS)]
        identifier = f"synthetic-probe-{i:02d}"
        if kind == "number":
            prompt = f"Tính {i + 12} + 0.35. Trả về kiểu number."
            value = float(f"{i + 12}.35")
        elif kind == "percent":
            prompt = f"Return type percent with numeric answer {i + 25}. Do not divide by 100."
            value = i + 25
        elif kind == "string":
            value = f"00{i:02d}"
            prompt = f"Giữ nguyên mã {value}, gồm cả số 0 đầu. Trả về string."
        elif kind == "date":
            value = f"2026-02-{i % 27 + 1:02d}"
            prompt = f"Return type date for the ISO date {value}."
        elif kind == "boolean":
            value = i % 2 == 0
            prompt = f"Số {i} có chẵn không? Trả về boolean."
        elif kind == "list":
            value = ["A", i]
            prompt = f'Return type list containing the string "A" and the number {i}, in order.'
        elif kind == "table":
            value = {"columns": ["mã", "số"], "rows": [["A", i]]}
            prompt = f'Trả về table với columns ["mã","số"], một dòng ["A",{i}].'
        elif kind == "unanswerable":
            value = None
            prompt = f"Synthetic dataset {i} contains no requested value. Return unanswerable without answer."
        else:
            value = None
            prompt = f"Synthetic confidence test {i}: explicitly return abstain without answer."
        expected = {"id": identifier, "type": kind}
        if value is not None:
            expected["answer"] = value
        cases.append({"id": identifier, "prompt": prompt, "expected": expected})
    return cases


def inference_cases(cases: list[dict]) -> list[dict]:
    return [{"id": case["id"], "prompt": case["prompt"]} for case in deepcopy(cases)]
