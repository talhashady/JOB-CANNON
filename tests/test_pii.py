from career_assistant.guardrails.pii import scrub_pii


def test_scrubs_national_id_and_card():
    text = "ID 42101-1234567-8 card 4111 1111 1111 1111"
    scrubbed, count = scrub_pii(text)
    assert "42101-1234567-8" not in scrubbed
    assert "4111" not in scrubbed
    assert count >= 2


def test_masks_email_and_phone():
    text = "Reach me at jane@example.com or +92 300 1234567"
    scrubbed, count = scrub_pii(text)
    assert "[EMAIL]" in scrubbed
    assert "jane@example.com" not in scrubbed
    assert count >= 1


def test_empty_text_is_noop():
    assert scrub_pii("") == ("", 0)
