"""
Review Service — Clean Architecture 模块。

分层:
  Domain (纯逻辑):
    diff_parser.py       — 解析 unified diff
    risk_analyzer.py     — 风险分析
    prompt_builder.py    — Prompt 构建
    report_generator.py  — 报告生成

  Service (编排):
    workflow_service.py  — LangGraph workflow orchestration
    review_service.py    — Backwards-compatible facade
"""
from app.services.review.review_service import ReviewService, ReviewInput, ReviewOutput
from app.services.review.workflow_service import WorkflowService
from app.services.review.state import ReviewState
from app.services.review.diff_parser import parse_diff, DiffResult
from app.services.review.risk_analyzer import assess_risk, RiskResult, build_risk_prompt_context
from app.services.review.prompt_builder import build_review_prompt
from app.services.review.report_generator import ReportGenerator, ReviewReport, ReviewIssue

__all__ = [
    "ReviewService",
    "ReviewInput",
    "ReviewOutput",
    "WorkflowService",
    "ReviewState",
    "parse_diff",
    "DiffResult",
    "assess_risk",
    "RiskResult",
    "build_risk_prompt_context",
    "build_review_prompt",
    "ReportGenerator",
    "ReviewReport",
    "ReviewIssue",
]
