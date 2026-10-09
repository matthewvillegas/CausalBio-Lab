"""Actual streamed-body bounds and safe numerical-failure contracts."""

import asyncio

import pytest
from causalbio.inference.hmc import HMCInferenceError
from causalbio_api.middleware import CorrelationAndSecurityMiddleware
from fastapi.testclient import TestClient
from helpers import assert_problem
from starlette.types import Message, Receive, Scope, Send


def test_chunked_body_is_stopped_before_parsing_when_limit_is_exceeded() -> None:
    called = False
    received = 0
    responses: list[Message] = []

    async def downstream(_scope: Scope, _receive: Receive, _send: Send) -> None:
        nonlocal called
        called = True

    async def receive() -> Message:
        nonlocal received
        received += 1
        return {"type": "http.request", "body": b"12345", "more_body": True}

    async def send(message: Message) -> None:
        responses.append(message)

    scope: Scope = {"type": "http", "method": "POST", "path": "/", "headers": []}
    asyncio.run(
        CorrelationAndSecurityMiddleware(downstream, max_request_bytes=8)(scope, receive, send)
    )
    assert not called
    assert received == 2
    assert responses[0]["status"] == 413
    assert dict(responses[0]["headers"])[b"x-content-type-options"] == b"nosniff"


@pytest.mark.parametrize("length", ["oops", "-1", "+12"])
def test_malformed_content_length_is_a_safe_client_error(client: TestClient, length: str) -> None:
    response = client.post(
        "/api/v1/questions/interpret", content=b"{}", headers={"content-length": length}
    )
    assert_problem(response, status=400, problem_suffix="/invalid-content-length")


def test_failed_sampler_returns_typed_problem_without_invalid_numbers(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise HMCInferenceError("Chains have zero variance; retry with default tuning.")

    monkeypatch.setattr("causalbio_api.routers.v1.run_hmc_demo", fail)
    response = client.post("/api/v1/bayes/demo/run", json={})
    problem = assert_problem(response, status=422, problem_suffix="/inference-failed")
    assert "default" in str(problem["alternatives"])
    assert "NaN" not in response.text
