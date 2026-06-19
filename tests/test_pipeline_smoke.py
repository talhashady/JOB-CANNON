from career_assistant.models.job import JobSearchRequest
from career_assistant.pipeline import CareerPipeline


def test_full_pipeline_offline(profile):
    """End-to-end run in deterministic/offline mode (sample jobs, dry-run apply)."""
    pipeline = CareerPipeline()
    request = JobSearchRequest(query="python developer", location="Remote",
                               sites=["indeed"], results_wanted=5, is_remote=True)
    result = pipeline.run(profile, request, top_k=3, auto_apply=True)

    assert result["jobs_scraped"] > 0
    assert result["jobs_verified"] > 0
    assert len(result["recommendations"]) >= 1

    top = result["recommendations"][0]
    assert top["match"]["score"] >= 0.0
    assert top["resume"]["plain_text"]
    assert top["cover_letter"]["body"]
    # Application must be dry-run by default (never live without explicit opt-in).
    assert top["application"]["status"] == "dry_run"


def test_build_profile_scrubs_pii():
    pipeline = CareerPipeline()
    cv = "Jane Dev\npython fastapi docker aws\n5 years experience\nID 42101-1234567-8"
    profile = pipeline.build_profile("user-2", cv, career_goals="Senior engineer")
    assert "42101-1234567-8" not in profile.raw_cv_text
    assert profile.years_experience == 5
    assert "python" in profile.skills
