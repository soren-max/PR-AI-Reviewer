"""
Regression tests for prompt builder compatibility imports.
"""
from __future__ import annotations


def test_review_prompt_builder_reexports_canonical_llm_builder() -> None:
    from app.services.llm.prompts import build_review_prompt as canonical
    from app.services.review.prompt_builder import build_review_prompt as compatibility

    canonical_system, canonical_user = canonical(
        pr_title="Fix auth",
        pr_description="Body",
        diff="+secure_login()",
        language="en",
        risk_context="authentication module changed",
    )
    compatibility_system, compatibility_user = compatibility(
        pr_title="Fix auth",
        pr_description="Body",
        diff="+secure_login()",
        language="en",
        risk_context="authentication module changed",
    )

    assert compatibility_system == canonical_system
    assert compatibility_user == canonical_user
    assert "authentication module changed" in compatibility_user
