"""Dev-only question taxonomy; never consumes answer values for classification."""

import hashlib
import re
import unicodedata
from collections import Counter
from pathlib import Path

from datamate.artifacts import sha256, write_json
from datamate.contracts import Question
from datamate.evaluation import bounded_bytes, external_metadata, output_path
from datamate.scoped_data import read_scoped
from datamate.scoring import parse_object
from datamate.splits import open_split


def search_key(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    return " ".join(
        "".join(c for c in decomposed if unicodedata.category(c) != "Mn").split()
    )


def classify(text: str, expected_type: str, rules: dict) -> dict:
    raw_key = search_key(text)
    key = re.sub(
        r"\b[a-z]+\b",
        lambda m: rules.get("token_rewrites", {}).get(m[0], m[0]),
        raw_key,
    )
    families = [
        name for name, pattern in rules["family_priority"] if re.search(pattern, key)
    ]
    operations = [
        name for name, pattern in rules["operations"] if re.search(pattern, key)
    ]
    time_forms = [
        name for name, pattern in rules["time_forms"] if re.search(pattern, key)
    ]
    tokens = set(re.findall(r"\b[a-z]+\b", raw_key))
    return dict(
        expected_type=expected_type,
        family=families[0] if families else "other",
        family_candidates=families,
        ambiguous_family=len(families) > 1,
        operations=operations or ["unspecified"],
        time_forms=time_forms or ["unspecified"],
        abbreviations=sorted(tokens.intersection(rules["abbreviation_tokens"])),
        ascii_only=text.isascii(),
        question_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def run_taxonomy(
    split: Path, manifest_sha256: str, rules_path: Path, output: Path
) -> dict:
    manifest, _ = open_split(split, manifest_sha256, verify_sources=True)
    source = Path(manifest["source"]["input_dir"])
    target = output_path(output, source, split)
    external_metadata(rules_path, source, split)
    rules_bytes = bounded_bytes(rules_path, 1024 * 1024)
    if len(rules_bytes) > 1024 * 1024:
        raise ValueError("Taxonomy rules exceed limit")
    rules = parse_object(rules_bytes)
    if rules.get("version") != 1 or not isinstance(rules.get("family_priority"), list):
        raise ValueError("Unsupported taxonomy rules")
    rule_sha = hashlib.sha256(rules_bytes).hexdigest()
    questions, qa = read_scoped(
        split, manifest_sha256, "dev", "questions", "taxonomy", "developer", rule_sha
    )
    # The classifier receives question text and gold type only, never gold values/aliases.
    references, ga = read_scoped(
        split, manifest_sha256, "dev", "gold", "taxonomy", "developer", rule_sha
    )
    records = []
    for qid, obj in sorted(questions.items()):
        question = Question.model_validate(obj)
        records.append(
            dict(
                id=qid,
                business_id=question.business_id,
                **classify(question.question, references[qid]["type"], rules),
            )
        )
    types = Counter(r["expected_type"] for r in records)
    families = Counter(r["family"] for r in records)
    operations = Counter(x for r in records for x in r["operations"])
    time_forms = Counter(x for r in records for x in r["time_forms"])
    abbreviations = Counter(x for r in records for x in r["abbreviations"])
    n = len(records)
    withheld = {
        part: manifest["summary"][part]["questions"]
        for part in ("calibration", "holdout")
    }
    result = dict(
        valid=True,
        partition="dev",
        manifest_sha256=manifest_sha256,
        rules_sha256=rule_sha,
        implementation_sha256=sha256(Path(__file__)),
        label_method=rules["label_method"],
        coverage=dict(
            train_metadata=sum(p["questions"] for p in manifest["summary"].values()),
            classified=n,
            sealed=withheld,
        ),
        summary=dict(
            by_type=dict(sorted(types.items())),
            by_family=dict(sorted(families.items())),
            top_five_families=[
                dict(family=k, count=v) for k, v in families.most_common(5)
            ],
            by_operation=dict(sorted(operations.items())),
            by_time_form=dict(sorted(time_forms.items())),
            abbreviations=dict(sorted(abbreviations.items())),
            ascii_only=sum(r["ascii_only"] for r in records),
            ambiguous_family=sum(r["ambiguous_family"] for r in records),
            unanswerable_count=types["unanswerable"],
            unanswerable_fraction=types["unanswerable"] / n,
        ),
        reader_audit=dict(questions=qa, gold=ga),
        records=records,
        holdout_answer_values_decoded=False,
        calibration_answer_values_decoded=False,
        gold_answers_exported=False,
    )
    if sha256(rules_path) != rule_sha:
        raise ValueError("Taxonomy rules changed during analysis")
    target.mkdir(parents=True, exist_ok=False)
    write_json(target / "taxonomy.json", result)
    lines = [
        "# Taxonomy train trong phạm vi dev",
        "",
        f"Chi tiết {n} câu dev; calibration {withheld['calibration']} và holdout {withheld['holdout']} giữ kín.",
        "Nhãn họ/thời gian là heuristic, không phải nhãn được reviewer độc lập xác nhận.",
        "",
        "| Kiểu gold dev | Số câu |",
        "|---|---:|",
        *[f"| {k} | {v} |" for k, v in sorted(types.items())],
        "",
        "| Họ câu hỏi heuristic dev | Số câu |",
        "|---|---:|",
        *[f"| {k} | {v} |" for k, v in families.most_common()],
        "",
        f"ASCII-only: {result['summary']['ascii_only']}; nhiều ứng viên họ: {result['summary']['ambiguous_family']}.",
        "Không xuất answer/alias gold và không suy taxonomy cho phần sealed.",
        "",
    ]
    (target / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return {k: v for k, v in result.items() if k != "records"}
