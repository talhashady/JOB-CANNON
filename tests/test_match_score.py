from career_assistant.models.job import Job
from career_assistant.tools.match_score import calculate_match_score


def test_strong_match_scores_high(profile):
    job = Job(
        source="indeed",
        title="Senior Python Developer",
        company="Acme",
        location="Remote",
        description="Looking for python, fastapi, docker, aws. 3+ years experience.",
        is_remote=True,
    )
    result = calculate_match_score(profile, job)
    assert result.score > 0.7
    assert "python" in [s.lower() for s in result.matched_skills]


def test_weak_match_scores_low(profile):
    job = Job(
        source="indeed",
        title="Senior Rust Systems Engineer",
        company="Acme",
        location="Berlin",
        description="Looking for rust, c++, kubernetes. 10+ years experience.",
    )
    result = calculate_match_score(profile, job)
    assert result.score < 0.6
    assert "rust" in result.missing_skills or "kubernetes" in result.missing_skills


def test_score_bounded(profile):
    job = Job(source="indeed", title="Dev", description="python")
    result = calculate_match_score(profile, job)
    assert 0.0 <= result.score <= 1.0
