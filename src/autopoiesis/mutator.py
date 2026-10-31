"""LLM mutator: split a stuck cell, or critique its DNA, via an OpenAI-compatible endpoint."""

from __future__ import annotations

import json
import logging
import os
import urllib.request

from autopoiesis.model import Cell, ChildSpec, Gradient, Mutator, NullMutator

log = logging.getLogger("autopoiesis.mutator")

_SYSTEM = "You repair a task graph. Reply with one JSON object and no other text."


class OpenAIMutator:
    """POST `{base_url}/chat/completions` on any OpenAI-compatible server."""

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 120,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def split(self, cell: Cell, failure_log: str, max_children: int) -> list[ChildSpec]:
        try:
            data = _load_json(self._chat(self._split_prompt(cell, failure_log, max_children)))
            if not isinstance(data, dict) or not isinstance(data.get("children"), list):
                log.warning("split rejected: children missing or not a list")
                return []
            limit = max(0, max_children)
            specs: list[ChildSpec] = []
            dropped = 0
            for item in data["children"][:limit]:
                spec = _child(item)
                if spec is None:
                    dropped += 1
                    continue
                specs.append(spec)
            if dropped:
                log.warning("split dropped %d invalid children", dropped)
            return specs
        except Exception as exc:
            log.warning("split failed: %s", exc)
            return []

    def critique(self, cell: Cell, failure_log: str, upstream: list[Cell]) -> Gradient | None:
        try:
            data = _load_json(self._chat(self._critique_prompt(cell, failure_log, upstream)))
            if not isinstance(data, dict):
                log.warning("critique rejected: not an object")
                return None
            grad = _gradient(data)
            allowed = {cell.id, *(dep.id for dep in upstream)}
            if grad is None:
                log.warning("critique rejected: invalid fields")
                return None
            if grad.target_id not in allowed:
                log.warning("critique rejected: target_id %s not allowed", grad.target_id)
                return None
            return grad
        except Exception as exc:
            log.warning("critique failed: %s", exc)
            return None

    def _chat(self, user: str) -> str:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            # Local thinking models otherwise stall or wrap the JSON in reasoning.
            "reasoning_effort": "none",
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            parsed = json.loads(response.read().decode())
        content = parsed["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise TypeError("message content is not a string")
        return content

    def _split_prompt(self, cell: Cell, failure_log: str, max_children: int) -> str:
        return (
            f"Split this failed cell into 2..{max_children} smaller subtasks.\n"
            "Each child needs a concrete, machine-checkable verify_cmd "
            "(shell, exit 0 = done).\n"
            'Reply JSON: {"children":[{"title","instruction","verify_cmd","run_cmd"?}]}\n'
            f"id: {cell.id}\n"
            f"title: {cell.title}\n"
            f"instruction: {cell.instruction}\n"
            f"run_cmd: {cell.run_cmd}\n"
            f"verify_cmd: {cell.verify_cmd}\n"
            f"failure_log:\n{failure_log[-3000:]}"
        )

    def _critique_prompt(self, cell: Cell, failure_log: str, upstream: list[Cell]) -> str:
        allowed = ", ".join([cell.id, *(dep.id for dep in upstream)])
        lines = [
            "Textual gradient: blame exactly one cell, the failed one or an upstream id.",
            f"Allowed target_id values: {allowed}",
            'Reply JSON: {"target_id","new_instruction","rationale","new_run_cmd"?}',
            f"id: {cell.id}",
            f"title: {cell.title}",
            f"instruction: {cell.instruction}",
            f"run_cmd: {cell.run_cmd}",
            f"failure_log:\n{failure_log[-3000:]}",
            "upstream:",
        ]
        if not upstream:
            lines.append("(none)")
        for dep in upstream:
            lines.append(f"id: {dep.id} | title: {dep.title} | instruction: {dep.instruction}")
        return "\n".join(lines)


def from_env() -> Mutator:
    """Build OpenAIMutator from APO_LLM_BASE_URL and APO_LLM_MODEL, else NullMutator."""
    base = os.environ.get("APO_LLM_BASE_URL", "").strip()
    model = os.environ.get("APO_LLM_MODEL", "").strip()
    if not base or not model:
        return NullMutator()
    key = os.environ.get("APO_LLM_API_KEY", "").strip() or None
    return OpenAIMutator(base, model, api_key=key)


def _load_json(text: str) -> object:
    return json.loads(_strip_fences(text))


def _strip_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    body = stripped.split("\n", 1)[1] if "\n" in stripped else ""
    body = body.strip()
    if body.endswith("```"):
        body = body[:-3].strip()
    return body


def _nonempty_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _optional_cmd(data: dict, key: str) -> tuple[str | None, bool]:
    """Missing or null is allowed. A present value must be a non-empty string."""
    if key not in data or data[key] is None:
        return None, True
    command = _nonempty_str(data[key])
    if command is None:
        return None, False
    return command, True


def _child(item: object) -> ChildSpec | None:
    if not isinstance(item, dict):
        return None
    title = _nonempty_str(item.get("title"))
    instruction = _nonempty_str(item.get("instruction"))
    verify_cmd = _nonempty_str(item.get("verify_cmd"))
    run_cmd, run_ok = _optional_cmd(item, "run_cmd")
    if not title or not instruction or not verify_cmd or not run_ok:
        return None
    return ChildSpec(
        title=title,
        verify_cmd=verify_cmd,
        instruction=instruction,
        run_cmd=run_cmd,
    )


def _gradient(data: dict) -> Gradient | None:
    target_id = _nonempty_str(data.get("target_id"))
    new_instruction = _nonempty_str(data.get("new_instruction"))
    rationale = _nonempty_str(data.get("rationale"))
    new_run_cmd, run_ok = _optional_cmd(data, "new_run_cmd")
    if not target_id or not new_instruction or not rationale or not run_ok:
        return None
    return Gradient(
        target_id=target_id,
        new_instruction=new_instruction,
        rationale=rationale,
        new_run_cmd=new_run_cmd,
    )
