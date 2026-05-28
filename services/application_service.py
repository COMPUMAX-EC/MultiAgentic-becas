"""Service wrapper for the application assistant."""
from __future__ import annotations

from application.application_agent import ApplicationAgent, ApplicationAgentError


def build_application_package(
    *,
    profile: dict,
    scholarship: dict,
    applicant_name: str = "",
    applicant_email: str = "",
    application_url: str | None = None,
) -> dict:
    agent = ApplicationAgent()
    return agent.prepare_application_package(
        profile=profile,
        scholarship=scholarship,
        applicant_name=applicant_name,
        applicant_email=applicant_email,
        application_url=application_url,
    )


__all__ = ["build_application_package", "ApplicationAgentError"]
