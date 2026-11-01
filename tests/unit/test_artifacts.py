from datamate import artifacts


def test_packaged_runtime_without_git_keeps_manifest_and_source_hashes(
    tmp_path, monkeypatch
):
    def missing_git(*args, **kwargs):
        raise FileNotFoundError("git not included in runtime image")

    monkeypatch.setattr(artifacts.subprocess, "run", missing_git)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "example.py").write_text("# synthetic source\n")
    result = artifacts.manifest(tmp_path, [], "smoke", "synthetic")
    assert result["commit"] is None
    assert result["dirty"] is None
    assert result["git_diff_sha256"] is None
    assert result["source_files_sha256"]["src/example.py"]
