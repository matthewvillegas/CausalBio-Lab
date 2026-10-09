"""Safe, correlation-aware API error responses."""

from __future__ import annotations

from typing import Any

from causalbio.inference.hmc import HMCInferenceError
from causalbio.investigations.service import RestrictedQueryError
from causalbio.questions.interpreter import (
    AmbiguousQuestionError,
    EmptyQuestionError,
    UnsupportedQuestionError,
)
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict


class ProblemDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    status: int
    detail: str
    correlation_id: str
    alternatives: tuple[str, ...] = ()


def _correlation_id(request: Request) -> str:
    return str(getattr(request.state, "correlation_id", "unavailable"))


def _response(
    request: Request,
    *,
    status: int,
    error_type: str,
    title: str,
    detail: str,
    alternatives: tuple[str, ...] = (),
) -> JSONResponse:
    problem = ProblemDetail(
        type=f"https://causalbio.example/problems/{error_type}",
        title=title,
        status=status,
        detail=detail,
        correlation_id=_correlation_id(request),
        alternatives=alternatives,
    )
    return JSONResponse(status_code=status, content=problem.model_dump(mode="json"))


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HMCInferenceError)
    async def inference_failure(request: Request, error: HMCInferenceError) -> JSONResponse:
        return _response(
            request,
            status=422,
            error_type="inference-failed",
            title="The uncertainty demonstration could not produce valid samples",
            detail=str(error),
            alternatives=("Retry with the default sampler settings.",),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation(request: Request, error: RequestValidationError) -> JSONResponse:
        issues = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        )
        return _response(
            request,
            status=422,
            error_type="validation-error",
            title="The request body is invalid",
            detail=issues or "The request did not match the documented schema.",
        )

    @app.exception_handler(EmptyQuestionError)
    async def empty_question(request: Request, error: EmptyQuestionError) -> JSONResponse:
        return _response(
            request,
            status=422,
            error_type="empty-question",
            title="A biological question is required",
            detail=str(error),
        )

    @app.exception_handler(AmbiguousQuestionError)
    async def ambiguous_question(request: Request, error: AmbiguousQuestionError) -> JSONResponse:
        return _response(
            request,
            status=422,
            error_type="ambiguous-question",
            title="The question needs clarification",
            detail=str(error),
            alternatives=error.alternatives,
        )

    @app.exception_handler(UnsupportedQuestionError)
    async def unsupported_question(
        request: Request, error: UnsupportedQuestionError
    ) -> JSONResponse:
        return _response(
            request,
            status=422,
            error_type="unsupported-offline-domain",
            title="No curated offline evidence pack matches this question",
            detail=str(error),
            alternatives=error.alternatives,
        )

    @app.exception_handler(RestrictedQueryError)
    async def restricted_query(request: Request, error: RestrictedQueryError) -> JSONResponse:
        return _response(
            request,
            status=422,
            error_type="restricted-request",
            title="The requested operational guidance is outside scope",
            detail=str(error),
        )

    @app.exception_handler(KeyError)
    async def not_found(request: Request, error: KeyError) -> JSONResponse:
        return _response(
            request,
            status=404,
            error_type="not-found",
            title="The requested research object was not found",
            detail=str(error).strip("'"),
        )

    @app.exception_handler(ValueError)
    async def invalid_value(request: Request, error: ValueError) -> JSONResponse:
        return _response(
            request,
            status=422,
            error_type="invalid-scientific-input",
            title="The supplied scientific input is invalid",
            detail=str(error),
        )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, _error: Exception) -> JSONResponse:
        return _response(
            request,
            status=500,
            error_type="internal-error",
            title="The analysis could not be completed",
            detail=(
                "An unexpected internal error occurred. Retry the request and use the correlation "
                "ID when reporting the problem. No raw stack trace is exposed."
            ),
        )


def openapi_error_responses() -> dict[int | str, dict[str, Any]]:
    return {
        404: {"model": ProblemDetail, "description": "Research object not found"},
        422: {"model": ProblemDetail, "description": "Question or scientific input invalid"},
    }
