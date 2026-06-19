"""Command-line entry point.

Usage:
  career-assistant run --profile profile.json --query "python developer" \
      --location Remote --sites indeed --results 25
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import get_settings
from .logging_config import configure_logging, get_logger
from .models.job import JobSearchRequest
from .models.profile import UserProfile
from .pipeline import CareerPipeline
from .tools import cv_parser

log = get_logger("cli")


def _load_profile(pipeline: CareerPipeline, args: argparse.Namespace) -> UserProfile:
    """Build a profile from a JSON file or a CV (.txt/.docx/.pdf)."""
    path = Path(args.profile)
    if not path.exists():
        log.error("Profile/CV file not found: %s", path)
        sys.exit(2)
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if "raw_cv_text" in data and not data.get("skills"):
            return pipeline.build_profile(
                data.get("user_id", "user-1"),
                data["raw_cv_text"],
                data.get("career_goals", ""),
            )
        return UserProfile.model_validate(data)
    cv_text = cv_parser.read_cv_file(str(path))
    return pipeline.build_profile(args.user_id, cv_text, args.goals)


def _cmd_run(args: argparse.Namespace) -> int:
    pipeline = CareerPipeline()
    profile = _load_profile(pipeline, args)
    request = JobSearchRequest(
        query=args.query,
        location=args.location,
        sites=args.sites or get_settings().default_job_sites,
        results_wanted=args.results,
        is_remote=args.remote,
    )
    result = pipeline.run(profile, request, top_k=args.top_k, auto_apply=not args.no_apply)

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
        log.info("Wrote full result to %s", args.output)

    _print_summary(result)
    return 0


def _print_summary(result: dict) -> None:
    print("\n" + "=" * 64)
    print(f"AI Career Assistant - results for: {result['query']}")
    print("=" * 64)
    print(f"Scraped: {result['jobs_scraped']} | Verified: {result['jobs_verified']} "
          f"| Elapsed: {result['elapsed_s']}s")
    for i, rec in enumerate(result["recommendations"], 1):
        job = rec["job"]
        match = rec["match"]
        app = rec["application"]
        print(f"\n{i}. {job['title']} @ {job['company']}  ({job['location']})")
        print(f"   match score : {match['score']:.2f}  ({match['rationale']})")
        print(f"   matched     : {', '.join(match['matched_skills']) or '-'}")
        if match["missing_skills"]:
            print(f"   to learn    : {', '.join(match['missing_skills'])}")
        if app:
            print(f"   application : {app['status']}")
    print("\nNote: applications are DRY-RUN unless ALLOW_LIVE_APPLY=true and a backend is set.\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="career-assistant", description="AI Career Assistant")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run the full pipeline")
    run.add_argument("--profile", required=True, help="Path to a profile .json or CV file (.txt/.docx/.pdf)")
    run.add_argument("--user-id", default="user-1")
    run.add_argument("--goals", default="", help="Career goals (used when parsing a CV)")
    run.add_argument("--query", required=True)
    run.add_argument("--location", default="Remote")
    run.add_argument("--sites", nargs="*", default=None,
                     help="Boards: indeed linkedin glassdoor google zip_recruiter")
    run.add_argument("--results", type=int, default=25)
    run.add_argument("--top-k", type=int, default=5)
    run.add_argument("--remote", action="store_true")
    run.add_argument("--no-apply", action="store_true", help="Skip the application stage")
    run.add_argument("--output", help="Write full JSON result to this path")
    run.set_defaults(func=_cmd_run)
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
