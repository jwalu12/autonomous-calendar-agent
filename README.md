# Autonomous Agent Lomi

This is a cron-job version of the calendar agent. It does not run a website or API server.

Each scheduled Render run:

1. Loads instructions from environment variables.
2. Loads calendar events from `CALENDAR_EVENTS_JSON` or `CALENDAR_EVENTS_URL`.
3. Calls an OpenAI-compatible AI model API.
4. Prints the model response to Render logs.
5. Optionally posts the result to `RESULT_WEBHOOK_URL`.
6. Exits.

Render cron jobs are ephemeral, so this project does not use SQLite or persistent disks.

## Files

```text
.
+-- run_agent.py
+-- requirements.txt
+-- render.yaml
+-- runtime.txt
+-- .env.example
```

## Render Settings

Use this as a Render Cron Job, not a Web Service.

Build Command:

```bash
pip install -r requirements.txt
```

Command:

```bash
python run_agent.py
```

Example schedule:

```text
*/15 * * * *
```

Render cron schedules use UTC.

## Required Environment Variables

```text
MODEL_API_KEY=your_api_key
MODEL_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4.1-mini
AGENT_INSTRUCTIONS=Review the calendar and recommend useful preparation steps.
```

## Calendar Input

Option A: put calendar events directly in `CALENDAR_EVENTS_JSON`:

```json
[
  {
    "title": "Planning meeting",
    "starts_at": "2026-06-01T10:00:00-05:00",
    "ends_at": "2026-06-01T10:30:00-05:00",
    "description": "Discuss roadmap"
  }
]
```

Option B: set `CALENDAR_EVENTS_URL` to an endpoint that returns the same JSON array.

## Optional Webhook Output

Set `RESULT_WEBHOOK_URL` if you want the cron job to send its result somewhere:

```text
RESULT_WEBHOOK_URL=https://example.com/calendar-agent-result
```

The webhook receives JSON:

```json
{
  "created_at": "2026-06-01T00:00:00Z",
  "instructions": "...",
  "events": [],
  "model_response": "..."
}
```

## Deploy

1. Upload this folder to a GitHub repo.
2. In Render, create a new Cron Job or Blueprint.
3. Add `MODEL_API_KEY` and any calendar/webhook environment variables.
4. Trigger a manual run to test it.
