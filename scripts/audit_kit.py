"""Hash supplied kit without analyzing answer content or question semantics."""

import json
from collections import Counter
from pathlib import Path

from datamate.artifacts import sha256, write_json


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    records = []
    summary = {}
    for split in ("train", "public_test"):
        directory = root / "data" / split
        files = sorted(p for p in directory.rglob("*") if p.is_file())
        summary[split] = {
            "files": len(files),
            "bytes": sum(p.stat().st_size for p in files),
            "business_directories": sum(
                p.is_dir() for p in (directory / "data").iterdir()
            ),
            "extensions": dict(Counter(p.suffix for p in files)),
        }
        records.extend(
            {
                "path": p.relative_to(root).as_posix(),
                "size_bytes": p.stat().st_size,
                "sha256": sha256(p),
            }
            for p in files
        )
    for path in sorted((root / "Thể lệ cuộc thi").glob("*.docx")):
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    destination = root / "manifests" / "kit_files.json"
    if destination.exists():
        saved = json.loads(destination.read_text("utf-8"))
        if saved["files"] != records:
            raise SystemExit(
                "Kit differs from saved manifest; review version before replacing it"
            )
        print("Kit hashes unchanged")
    else:
        destination.parent.mkdir(exist_ok=True)
        write_json(
            destination,
            {
                "source": "supplied local kit; upstream revision unknown",
                "summary": summary,
                "files": records,
            },
        )
        print(destination)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
