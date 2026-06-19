"""Career Orchestrator: the entry point that sequences the specialist agents.

Implements the Manager + Handoff pattern: the orchestrator owns ProfileContext and hands
off to each specialist in turn, recording an audit step at every stage.
"""
from __future__ import annotations

from typing import Optional

from .base import BaseAgent, LLMClient
from .application_agent import ApplicationAgent
from .cover_letter_agent import CoverLetterAgent
from .matching_agent import MatchingAgent
from .resume_agent import ResumeAgent
from .scraping_agent import ScrapingAgent
from .skill_interview_agent import SkillInterviewAgent
from .tracking_agent import TrackingAgent
from .verification_agent import VerificationAgent
from ..config import Settings


class CareerOrchestrator(BaseAgent):
    name = "CareerOrchestrator"
    instructions = (
        "Sequence the career pipeline: job collection, verification, matching, document "
        "customization, application, tracking, and skill development. Maintain user profile "
        "context across all handoffs."
    )

    def __init__(self, llm: Optional[LLMClient] = None, settings: Optional[Settings] = None) -> None:
        super().__init__(llm=llm, settings=settings)
        # Specialist agents share the orchestrator's LLM + settings.
        self.scraping = ScrapingAgent(llm=self.llm, settings=self.settings)
        self.verification = VerificationAgent(llm=self.llm, settings=self.settings)
        self.matching = MatchingAgent(llm=self.llm, settings=self.settings)
        self.resume = ResumeAgent(llm=self.llm, settings=self.settings)
        self.cover_letter = CoverLetterAgent(llm=self.llm, settings=self.settings)
        self.application = ApplicationAgent(llm=self.llm, settings=self.settings)
        self.tracking = TrackingAgent(llm=self.llm, settings=self.settings)
        self.skill_interview = SkillInterviewAgent(llm=self.llm, settings=self.settings)

    @property
    def model(self) -> str:
        return self.settings.orchestrator_model
