from src.transfer.service import format_amount, generate_signature


def test_signature_matches_spec_vector() -> None:
    assert (
        generate_signature("webhook-secret", b'{"id":"abc"}')
        == "2ef8625de7bf407caa0df98fbfed0f36dec718f2110403cb614f167c497fea7d"
    )


def test_signature_is_deterministic_hex() -> None:
    body = b'{"id":"abc"}'
    first = generate_signature("webhook-secret", body)
    assert first == generate_signature("webhook-secret", body)
    assert len(first) == 64
    assert all(c in "0123456789abcdef" for c in first)


def test_signature_sensitive_to_key_and_body() -> None:
    base = generate_signature("webhook-secret", b'{"id":"abc"}')
    assert generate_signature("other-secret", b'{"id":"abc"}') != base
    assert generate_signature("webhook-secret", b'{"id":"abd"}') != base


def test_format_amount_strips_trailing_zeros() -> None:
    from decimal import Decimal

    assert format_amount(Decimal("10.5000")) == "10.5"
    assert format_amount(Decimal("100")) == "100"
    assert format_amount(Decimal("0.000000000000000001")) == "0.000000000000000001"
