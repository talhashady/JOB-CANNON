from career_assistant.guardrails.ats_validator import validate_ats
from career_assistant.guardrails.factual_accuracy import check_factual_accuracy
from career_assistant.guardrails.profile_completeness import check_profile_completeness


def test_ats_rejects_tables_and_images():
    bad = "Experience <table><tr><td>x</td></tr></table> <img src=x>"
    assert validate_ats(bad).passed is False


def test_ats_accepts_clean_text():
    good = "SKILLS\n- python\n- docker\nEXPERIENCE\n- Backend Engineer"
    assert validate_ats(good).passed is True


def test_factual_accuracy_blocks_fabricated_skill(profile):
    # profile has python/fastapi/docker/aws but NOT kubernetes
    doc = "Expert in python and kubernetes and terraform."
    result = check_factual_accuracy(doc, profile)
    assert result.passed is False
    assert any("kubernetes" in i for i in result.issues)


def test_factual_accuracy_allows_grounded_doc(profile):
    doc = "Strong in python, fastapi, docker and aws."
    assert check_factual_accuracy(doc, profile).passed is True


def test_profile_completeness(profile):
    assert check_profile_completeness(profile).passed is True
