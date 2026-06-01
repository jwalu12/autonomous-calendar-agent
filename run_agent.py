import json
import os
import sys
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def request_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {details}") from exc

    if not raw:
        return None
    return json.loads(raw)


def load_calendar_events() -> list[dict[str, Any]]:
    events_url = env("CALENDAR_EVENTS_URL")
    if events_url:
        data = request_json(events_url)
    else:
        raw_events = env("CALENDAR_EVENTS_JSON", "[]")
        data = json.loads(raw_events)

    if not isinstance(data, list):
        raise ValueError("Calendar input must be a JSON array of event objects.")

    events: list[dict[str, Any]] = []
    for event in data:
        if not isinstance(event, dict):
            raise ValueError("Each calendar event must be a JSON object.")
        events.append(event)
    return events


def call_model(instructions: str, events: list[dict[str, Any]]) -> str:
    api_key = env("MODEL_API_KEY")
    base_url = env("MODEL_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = env("MODEL_NAME", "gpt-4.1-mini")

    if not api_key:
        return "MODEL_API_KEY is not configured. No autonomous action was taken."

    system_prompt = (
        "You are an autonomous calendar agent running as a scheduled cron job. "
        "Review the user's instructions and calendar events. Return concise, "
        "practical next actions. Do not claim to contact anyone or modify any "
        "external system unless a tool or webhook result explicitly says it happened."
    )
    user_prompt = json.dumps(
        {
            "current_time": utc_now(),
            "instructions": instructions,
            "calendar_events": events,
            "available_actions": [
                "recommend_preparation",
                "flag_conflicts",
                "suggest_reminders",
                "do_nothing",
            ],
        },
        indent=2,
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    request = Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Model API request failed with HTTP {exc.code}: {details}") from exc

    return data["choices"][0]["message"]["content"]


def post_result(result: dict[str, Any]) -> None:
    webhook_url = env("RESULT_WEBHOOK_URL")
    if not webhook_url:
        return
    request_json(webhook_url, method="POST", payload=result)


def main() -> int:
    instructions = env(
        "AGENT_INSTRUCTIONS",
        "Review the calendar and recommend useful preparation steps.",
    )
    events = load_calendar_events()
    model_response = call_model(instructions, events)

    result = {
        "created_at": utc_now(),
        "instructions": instructions,
        "events": events,
        "model_response": model_response,
    }
    print(json.dumps(result, indent=2))
    post_result(result)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Calendar cron agent failed: {exc}", file=sys.stderr)
        raise
