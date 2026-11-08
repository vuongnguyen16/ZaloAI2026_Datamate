import importlib.util
from pathlib import Path

import pytest


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_transport_upload_allowlist_contains_only_required_code():
    from infra.modal_binding_proposals import extra_image_files

    pairs = extra_image_files()
    names = {str(p).replace("\\", "/") for p, _ in pairs}
    assert any(p.endswith("/binding_proposals.py") for p in names)
    assert any(p.endswith("/binding_generate.py") for p in names)
    assert all(
        "/data/" not in p and "/runs/" not in p and "/.modal/" not in p for p in names
    )
    assert all(Path(p).is_file() for p, _ in pairs)


def test_gpu_entry_rejects_invalid_payload_before_gpu_imports(tmp_path):
    root = Path(__file__).resolve().parents[2]
    module = load(root / "infra/p1_runtime/binding_generate.py", "binding_gpu")
    with pytest.raises(ValueError):
        module.generate(dict(cases=[]), tmp_path / "output.json")
    assert not (tmp_path / "output.json").exists()


def test_output_must_not_overlap_input_or_profile_generation(tmp_path):
    root = Path(__file__).resolve().parents[2]
    module = load(root / "scripts/p2_binding_proposals.py", "binding_proposal_cli")
    source, split, profile = (
        tmp_path / "source",
        tmp_path / "frozen",
        tmp_path / "profile",
    )
    for directory in (source, split, profile):
        directory.mkdir()
    for output in (source / "extra", split / "extra", profile / "extra"):
        with pytest.raises(ValueError):
            module.check_output(
                output,
                dict(
                    source=str(source),
                    split=str(split),
                    profile_index=str(profile / "profile.json"),
                ),
            )
        assert not output.exists()
