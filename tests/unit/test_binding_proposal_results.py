import pytest

from datamate.binding_proposals import make_case


def case():
    return make_case(
        "source",
        "known source",
        [],
        None,
        dict(code_sha256="a" * 64, model_revision="b" * 40, rulebook_sha256="c" * 64),
    )


def envelope():
    return dict(
        network_blocked=True,
        weights_read_only=True,
        snapshot_verified=True,
        contexts=[
            dict(
                status="completed",
                exit_code=0,
                timed_out=False,
                cleaned_up=True,
                peak_memory_bytes=29 * 1024**3,
                memory_sample_count=1,
                torch_peak_allocated_bytes=28 * 1024**3,
                torch_peak_reserved_bytes=29 * 1024**3,
                records=[
                    dict(
                        case_id=case()["id"],
                        text='{"choice":"unknown","quote":"","bindings":[]}',
                        finish_reason="stop",
                    )
                ],
            )
        ],
    )


@pytest.mark.parametrize(
    "change",
    [
        dict(records=[]),
        dict(exit_code=1),
        dict(timed_out=True),
        dict(cleaned_up=False),
        dict(peak_memory_bytes=31 * 1024**3),
        dict(memory_sample_count=0),
        dict(records=[dict(case_id="foreign", text="{}", finish_reason="stop")]),
    ],
)
def test_failed_incomplete_or_overbudget_run_cannot_populate_cache(change):
    from datamate.binding_proposals import validate_cloud_result

    result = envelope()
    result["contexts"][0].update(change)
    with pytest.raises(ValueError):
        validate_cloud_result(result, [case()], 30 * 1024**3)


def test_complete_envelope_and_cache_identity_are_required():
    from datamate.binding_proposals import validate_cached_record, validate_cloud_result

    result = envelope()
    records = validate_cloud_result(result, [case()], 30 * 1024**3)
    assert len(records) == 1
    assert validate_cached_record(records[0], case())["citation_valid"]
    with pytest.raises(ValueError):
        validate_cached_record(records[0] | dict(case_id="foreign"), case())
    rejected = validate_cached_record(records[0] | dict(finish_reason="length"), case())
    assert not rejected["citation_valid"] and not rejected["capabilities_granted"]
