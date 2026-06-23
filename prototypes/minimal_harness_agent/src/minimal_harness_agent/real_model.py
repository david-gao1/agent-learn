from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_MODEL = "gpt-5.4-mini"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


@dataclass
class OpenAIResponsesModel:
    api_key: str
    model: str = DEFAULT_MODEL
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "OpenAIResponsesModel":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for real model tests")
        return cls(
            api_key=api_key,
            model=os.environ.get("OPENAI_MODEL", DEFAULT_MODEL),
        )

    def complete(self, instructions: str, prompt: str) -> str:
        payload = {
            "model": self.model,
            "instructions": instructions,
            "input": prompt,
            "max_output_tokens": 160,
        }
        request = self.build_request(payload)

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API error {exc.code}: {body}") from exc

        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        return _extract_text_from_output(data)

    def build_request(self, payload: dict[str, Any]) -> urllib.request.Request:
        return urllib.request.Request(
            OPENAI_RESPONSES_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )


def _extract_text_from_output(data: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)

    text = "\n".join(parts).strip()
    if not text:
        raise RuntimeError("OpenAI response did not contain output text")
    return text


def real_model_plan_act_smoke(model: OpenAIResponsesModel) -> dict[str, str]:
    instructions = (
        "You are testing a Harness Agent learning prototype. "
        "Return concise plain text. Do not use markdown."
    )
    plan = model.complete(
        instructions=instructions,
        prompt=(
            "Create exactly three short Plan-Act steps for analyzing a tiny Python "
            "repository. Prefix each step with STEP."
        ),
    )
    reflection = model.complete(
        instructions=instructions,
        prompt=(
            "Critique this plan in one sentence. If it is good enough for a smoke "
            f"test, say ACCEPT: {plan}"
        ),
    )
    return {"plan": plan, "reflection": reflection}
