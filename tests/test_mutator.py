"""OpenAIMutator against a local http.server. No network."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from autopoiesis.model import Cell, ChildSpec, Gradient, NullMutator
from autopoiesis.mutator import OpenAIMutator, from_env


class _Server(ThreadingHTTPServer):
    daemon_threads = True


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        fake: FakeLLM = self.server.fake  # type: ignore[attr-defined]
        fake.seen.append(
            {
                "path": self.path,
                "body": json.loads(raw.decode()),
                "authorization": self.headers.get("Authorization"),
            }
        )
        if fake.delay:
            time.sleep(fake.delay)
        payload = {"choices": [{"message": {"content": fake.content}}]}
        data = json.dumps(payload).encode()
        try:
            self.send_response(fake.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            return

    def log_message(self, fmt: str, *args: object) -> None:
        return


class FakeLLM:
    def __init__(self) -> None:
        self.status = 200
        self.content = "{}"
        self.delay = 0.0
        self.seen: list[dict] = []
        self.httpd = _Server(("127.0.0.1", 0), _Handler)
        self.httpd.fake = self  # type: ignore[attr-defined]
        self.thread = threading.Thread(
            target=self.httpd.serve_forever,
            kwargs={"poll_interval": 0.05},
            daemon=True,
        )
        self.thread.start()

    @property
    def base_url(self) -> str:
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}/v1"

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=3)


def _cell() -> Cell:
    return Cell(
        id="c-abc123",
        title="Ship the parser",
        verify_cmd="python -m pytest -q",
        instruction="Implement the parser.",
        run_cmd="python parse.py",
    )


def _upstream() -> Cell:
    return Cell(
        id="c-up1111",
        title="Lexer",
        verify_cmd="test -f lex.py",
        instruction="Write the lexer first.",
    )


def _child(index: int) -> dict[str, str]:
    return {
        "title": f"Part {index}",
        "instruction": f"Do part {index}",
        "verify_cmd": f"test -f part{index}",
    }


@pytest.fixture
def fake() -> Iterator[FakeLLM]:
    server = FakeLLM()
    try:
        yield server
    finally:
        server.close()


def _mutator(
    fake: FakeLLM,
    api_key: str | None = None,
    timeout: float = 5,
) -> OpenAIMutator:
    return OpenAIMutator(fake.base_url, "test-model", api_key=api_key, timeout=timeout)


def test_split_valid(fake: FakeLLM) -> None:
    fake.content = json.dumps(
        {
            "children": [
                _child(1),
                {**_child(2), "run_cmd": "python gen.py"},
            ]
        }
    )
    specs = _mutator(fake).split(_cell(), "boom", 3)
    assert specs == [
        ChildSpec(title="Part 1", verify_cmd="test -f part1", instruction="Do part 1"),
        ChildSpec(
            title="Part 2",
            verify_cmd="test -f part2",
            instruction="Do part 2",
            run_cmd="python gen.py",
        ),
    ]


def test_split_truncates(fake: FakeLLM) -> None:
    fake.content = json.dumps({"children": [_child(1), _child(2), _child(3)]})
    specs = _mutator(fake).split(_cell(), "boom", 2)
    assert [spec.title for spec in specs] == ["Part 1", "Part 2"]


def test_split_drops_invalid_children(fake: FakeLLM) -> None:
    fake.content = json.dumps(
        {
            "children": [
                {"instruction": "x", "verify_cmd": "true"},
                {"title": "  ", "instruction": "x", "verify_cmd": "true"},
                {"title": "Bad", "instruction": "x", "verify_cmd": 1},
                "nope",
                {"title": "Keep", "instruction": "ship it", "verify_cmd": "test -f ok"},
            ]
        }
    )
    specs = _mutator(fake).split(_cell(), "boom", 5)
    assert specs == [
        ChildSpec(title="Keep", verify_cmd="test -f ok", instruction="ship it"),
    ]


def test_split_invalid_json(fake: FakeLLM) -> None:
    fake.content = "this is not json"
    assert _mutator(fake).split(_cell(), "boom", 2) == []


def test_split_fenced_json(fake: FakeLLM) -> None:
    inner = json.dumps({"children": [_child(1)]})
    fake.content = f"```json\n{inner}\n```"
    specs = _mutator(fake).split(_cell(), "boom", 2)
    assert specs == [
        ChildSpec(title="Part 1", verify_cmd="test -f part1", instruction="Do part 1"),
    ]


def test_http_500_returns_empty(fake: FakeLLM, caplog: pytest.LogCaptureFixture) -> None:
    fake.status = 500
    mutator = _mutator(fake)
    with caplog.at_level(logging.WARNING, logger="autopoiesis.mutator"):
        assert mutator.split(_cell(), "boom", 2) == []
        assert mutator.critique(_cell(), "boom", []) is None
    assert any(record.name == "autopoiesis.mutator" for record in caplog.records)


def test_timeout_returns_empty(fake: FakeLLM) -> None:
    fake.delay = 2
    fake.content = json.dumps({"children": [_child(1)]})
    started = time.monotonic()
    assert _mutator(fake, timeout=0.2).split(_cell(), "boom", 2) == []
    assert time.monotonic() - started < 1.0


def test_critique_valid_and_upstream_in_prompt(fake: FakeLLM) -> None:
    fake.content = json.dumps(
        {
            "target_id": "c-up1111",
            "new_instruction": "Emit tokens before parsing.",
            "rationale": "The parser failed on an empty token stream.",
            "new_run_cmd": "python lex.py",
        }
    )
    gradient = _mutator(fake).critique(_cell(), "trace", [_upstream()])
    assert gradient == Gradient(
        target_id="c-up1111",
        new_instruction="Emit tokens before parsing.",
        rationale="The parser failed on an empty token stream.",
        new_run_cmd="python lex.py",
    )
    user = fake.seen[0]["body"]["messages"][1]["content"]
    assert "c-up1111" in user
    assert "Write the lexer first." in user
    assert "Implement the parser." in user


def test_critique_wrong_target_and_bad_fields(fake: FakeLLM) -> None:
    mutator = _mutator(fake)
    fake.content = json.dumps(
        {"target_id": "c-nope", "new_instruction": "x", "rationale": "y"}
    )
    assert mutator.critique(_cell(), "trace", [_upstream()]) is None
    fake.content = json.dumps(
        {"target_id": "c-abc123", "new_instruction": "", "rationale": "y"}
    )
    assert mutator.critique(_cell(), "trace", []) is None


def test_request_body(fake: FakeLLM) -> None:
    failure = "HEADMARKER" + ("x" * 4000) + "TAILMARKER"
    _mutator(fake).split(_cell(), failure, 3)
    seen = fake.seen[0]
    body = seen["body"]
    assert seen["path"] == "/v1/chat/completions"
    assert seen["authorization"] is None
    assert set(body) == {
        "model",
        "temperature",
        "response_format",
        "reasoning_effort",
        "messages",
    }
    assert body["model"] == "test-model"
    assert body["temperature"] == 0.2
    assert body["response_format"] == {"type": "json_object"}
    assert body["reasoning_effort"] == "none"
    user = body["messages"][1]["content"]
    assert "2..3" in user
    assert "verify_cmd" in user
    assert "HEADMARKER" not in user
    assert "TAILMARKER" in user
    assert "Implement the parser." in user

    _mutator(fake, api_key="sek").split(_cell(), "boom", 2)
    assert fake.seen[1]["authorization"] == "Bearer sek"


def test_from_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("APO_LLM_BASE_URL", "APO_LLM_MODEL", "APO_LLM_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert isinstance(from_env(), NullMutator)
    monkeypatch.setenv("APO_LLM_BASE_URL", "http://127.0.0.1:9/v1")
    assert isinstance(from_env(), NullMutator)


def test_from_env_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APO_LLM_BASE_URL", "http://127.0.0.1:9/v1/")
    monkeypatch.setenv("APO_LLM_MODEL", "local-model")
    monkeypatch.setenv("APO_LLM_API_KEY", "sk-test")
    mutator = from_env()
    assert isinstance(mutator, OpenAIMutator)
    assert mutator.base_url == "http://127.0.0.1:9/v1"
    assert mutator.model == "local-model"
    assert mutator.api_key == "sk-test"
    assert mutator.timeout == 120
