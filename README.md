## Content Dashboard Daily Tracker (Slack → Dashboard)

This project captures **daily plans** and **daily updates** from your team (e.g., posted in Slack via a workflow/webhook), stores them in a local DB, and provides a **dashboard** to view work by **week/month/member/task type/question type**.

### What you get

- **Slack intake (webhook)**: a single endpoint you can call from Slack Workflow Builder (“Send a web request”) or any form tool.
- **SQLite storage**: easy local persistence (no external DB required).
- **Dashboard**:
  - This week / last week
  - Current month totals + trends
  - Member-wise breakdown
  - Task type + question type breakdown
  - Searchable activity table

---

## Repo structure

- `server/` Node.js API (Express) + SQLite
- `client/` React (Vite) dashboard

---

## Quick start (local)

### 1) Install

```bash
npm install
```

### 2) Configure

Copy env templates and update values if needed:

```bash
cp server/.env.example server/.env
cp client/.env.example client/.env
```

### 3) Run

```bash
npm run dev
```

- API: `http://localhost:8787`
- Dashboard: `http://localhost:5173`

---

## Slack setup (recommended approach)

Use **Slack Workflow Builder** → add a step **“Send a web request”** and POST JSON to:

`http://<your-public-url>/api/intake/slack`

Payload example:

```json
{
  "member": "Shivendra",
  "date": "2026-03-18",
  "kind": "plan",
  "items": [
    {
      "taskType": "Assessment Review",
      "questionType": "AutoCode",
      "customer": "Internal",
      "count": 1,
      "notes": "AutoCode refinement"
    }
  ],
  "rawText": "AutoCode Refinement"
}
```

If you don’t have a public URL yet, you can use something like `ngrok` during setup.

---

## Seed sample data

```bash
npm run seed
```

---

## Next enhancements (easy follow-ups)

- Google Sheets import/export
- Slack App (interactive modal + thread reminders)
- Role-based access, SSO, and team admin UI

