"""
Jira Cloud REST API v3: one issue per plan/update task, transitions for status sync.

Set JIRA_API_TOKEN in backend/.env. See jira_config.py for site URL and project.
"""

import base64
import json
import logging
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path

import certifi

from django.conf import settings as dj_settings

logger = logging.getLogger(__name__)

_DEFAULT_JIRA_STATUS_NAMES = {
    # Hackerearth Jira workflow: To Do / In Progress / Blocked / Done
    "open": ["To Do"],
    "in_progress": ["In Progress"],
    "blocked": ["Blocked"],
    "closed": ["Done"],
}


def _backend_dir():
    return Path(__file__).resolve().parent.parent


def _parse_jira_error_body(raw: str) -> str:
    if not raw:
        return "Unknown error (empty response)"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw[:500]
    msgs = data.get("errorMessages") or []
    if msgs:
        return "; ".join(str(m) for m in msgs)
    errs = data.get("errors") or {}
    if errs:
        return "; ".join(f"{k}: {v}" for k, v in errs.items())
    return raw[:500]


def load_jira_settings():
    """
    Return dict with base_url, email, token, project_key, issue_type, issue_type_id,
    summary_prefix, status_name_map (dict), or None if Jira is disabled.
    """
    config_path = _backend_dir() / "jira_config.py"
    if not config_path.exists():
        logger.warning("jira_config.py missing at %s", config_path)
        return None
    cfg = {}
    with open(config_path, encoding="utf-8") as f:
        exec(compile(f.read(), str(config_path), "exec"), cfg)

    token = (
        os.environ.get("JIRA_API_TOKEN")
        or getattr(dj_settings, "JIRA_API_TOKEN", None)
        or ""
    )
    token = (token or "").strip()

    base_url = (cfg.get("JIRA_BASE_URL") or "").strip().rstrip("/")
    email = (os.environ.get("JIRA_EMAIL") or cfg.get("JIRA_EMAIL") or "").strip()
    project_key = (cfg.get("JIRA_PROJECT_KEY") or "").strip()
    issue_type = (cfg.get("JIRA_ISSUE_TYPE") or "Task").strip()
    issue_type_id = (cfg.get("JIRA_ISSUE_TYPE_ID") or "").strip()
    summary_prefix = (cfg.get("JIRA_SUMMARY_PREFIX") or "[Content]").strip()
    raw_map = cfg.get("JIRA_STATUS_TO_JIRA_NAMES")
    if isinstance(raw_map, dict) and raw_map:
        status_name_map = {str(k).lower(): list(v) for k, v in raw_map.items()}
    else:
        status_name_map = {k: list(v) for k, v in _DEFAULT_JIRA_STATUS_NAMES.items()}

    if not token:
        logger.warning(
            "Jira disabled: set JIRA_API_TOKEN in backend/.env (see jira_config.py)."
        )
        return None
    if not base_url or not email or not project_key:
        logger.warning(
            "Jira disabled: fill JIRA_BASE_URL, JIRA_EMAIL, JIRA_PROJECT_KEY in jira_config.py."
        )
        return None

    return {
        "base_url": base_url,
        "email": email,
        "token": token,
        "project_key": project_key,
        "issue_type": issue_type,
        "issue_type_id": issue_type_id,
        "summary_prefix": summary_prefix,
        "status_name_map": status_name_map,
    }


def _auth_header(cfg):
    auth = base64.b64encode(f"{cfg['email']}:{cfg['token']}".encode()).decode()
    return {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _jira_request(cfg, path, method="GET", payload=None, timeout=20):
    url = f"{cfg['base_url']}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers=_auth_header(cfg),
        method=method,
    )
    ctx = ssl.create_default_context(cafile=certifi.where())
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read().decode("utf-8")
            return True, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return False, {"_http_code": e.code, "_body": err_body}
    except urllib.error.URLError as e:
        return False, {"_url_error": str(e.reason)}


def _text_to_adf(text):
    lines = (text or "").split("\n") or [""]
    content = []
    for line in lines:
        content.append(
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": line}] if line else [],
            }
        )
    return {"type": "doc", "version": 1, "content": content}


def _format_single_item_description(entry, item):
    lines = [
        f"Content Dashboard — {entry.kind.title()} — {entry.entry_date} — {entry.member.display_name}",
        f"Source: {entry.source}",
        "",
        f"Task: {item.task_type}",
    ]
    if item.question_type:
        lines.append(f"Question type: {item.question_type}")
    if item.customer:
        lines.append(f"Customer: {item.customer}")
    if item.count is not None:
        lines.append(f"Count: {item.count}")
    if item.notes:
        lines.append("")
        lines.append(item.notes)
    if entry.raw_text and entry.kind == "update":
        lines.append("")
        lines.append(f"Entry notes: {entry.raw_text}")
    return "\n".join(lines)


def _issue_type_field(settings_dict):
    if settings_dict.get("issue_type_id"):
        return {"id": settings_dict["issue_type_id"]}
    return {"name": settings_dict["issue_type"]}


def create_item_issue(entry, item):
    """
    Create one Jira issue for this EntryItem (plan task or extra update task).

    Returns:
        {"ok": True, "key": str, "url": str} or {"ok": False, "error": str}
    """
    cfg = load_jira_settings()
    if not cfg:
        return {
            "ok": False,
            "error": (
                "Jira is not configured. Add JIRA_API_TOKEN to backend/.env "
                "and check jira_config.py for JIRA_PROJECT_KEY and JIRA_ISSUE_TYPE."
            ),
        }

    summary = (
        f"{cfg['summary_prefix']} {item.task_type} · {entry.member.display_name} · {entry.entry_date}"
    )[:254]
    description = _format_single_item_description(entry, item)
    fields = {
        "project": {"key": cfg["project_key"]},
        "summary": summary,
        "description": _text_to_adf(description),
        "issuetype": _issue_type_field(cfg),
    }
    if getattr(item, "due_at", None):
        fields["duedate"] = item.due_at.isoformat()
    ok, body = _jira_request(cfg, "/rest/api/3/issue", "POST", {"fields": fields})
    if not ok:
        code = body.get("_http_code", "?")
        detail = _parse_jira_error_body(body.get("_body", ""))
        msg = f"Jira API HTTP {code}: {detail}"
        logger.warning("Jira issue create failed: %s", msg)
        return {"ok": False, "error": msg}
    key = body.get("key")
    if not key:
        return {"ok": False, "error": f"Unexpected Jira response: {body}"}
    browse = f"{cfg['base_url']}/browse/{key}"
    return {"ok": True, "key": key, "url": browse}


_DONE_CARRY_FIELDS = (
    "summary,reporter,customfield_10230,customfield_10233,"
    "customfield_10234,customfield_10235,customfield_10521,customfield_10526"
)


def _fetch_done_fields(cfg, issue_key, due_at=None):
    """Return a fields dict safe to pass when transitioning to Done.

    The TCE Jira workflow validators require Task Type, Question type,
    Test count, and Effort Logged even though the schema marks them optional.
    We carry existing values back and fall back to neutral defaults so the
    transition never fails due to missing fields.
    """
    ok, body = _jira_request(cfg, f"/rest/api/3/issue/{issue_key}?fields={_DONE_CARRY_FIELDS}", "GET")
    f = (body.get("fields") or {}) if ok else {}

    fields = {}

    # Task Type (select) — required by validator
    task_type = f.get("customfield_10230")
    if task_type and task_type.get("id"):
        fields["customfield_10230"] = {"id": task_type["id"]}

    # Question type (multi-select) — validator requires at least one value
    raw_qt = f.get("customfield_10235")
    if raw_qt:
        if isinstance(raw_qt, list) and raw_qt:
            fields["customfield_10235"] = [{"id": str(v["id"])} for v in raw_qt if v.get("id")]
        elif isinstance(raw_qt, dict) and raw_qt.get("id"):
            fields["customfield_10235"] = [{"id": str(raw_qt["id"])}]
    if "customfield_10235" not in fields:
        # Fall back to "Diagram" (id 10244) — a neutral default
        fields["customfield_10235"] = [{"id": "10244"}]

    # Question count
    fields["customfield_10233"] = f.get("customfield_10233") or 0

    # Test count — validator requires a value; default to 0
    fields["customfield_10234"] = f.get("customfield_10234") or 0

    # Effort Logged — validator requires a value; default to 0
    fields["customfield_10526"] = f.get("customfield_10526") or 0

    # Due At
    due_val = due_at.isoformat() if due_at else (f.get("customfield_10521") or "")
    if due_val:
        fields["customfield_10521"] = str(due_val)[:10]

    return fields


def transition_issue(issue_key, app_status: str, *, comment=None, due_at=None):
    """
    Move a Jira issue toward a workflow state that matches Content Dashboard status
    (open / in_progress / blocked / closed). Picks the first matching transition.
    """
    cfg = load_jira_settings()
    if not cfg or not issue_key:
        return {"ok": False, "error": "Jira not configured or missing issue key"}

    st = (app_status or "open").strip().lower()
    want_names = cfg["status_name_map"].get(st) or _DEFAULT_JIRA_STATUS_NAMES.get(st, [])
    want_lower = {n.lower() for n in want_names}

    ok, body = _jira_request(
        cfg, f"/rest/api/3/issue/{issue_key}/transitions?expand=transitions.fields", "GET", None
    )
    if not ok:
        code = body.get("_http_code", "?")
        detail = _parse_jira_error_body(body.get("_body", ""))
        return {"ok": False, "error": f"Transitions HTTP {code}: {detail}"}

    transitions = body.get("transitions") or []
    chosen = None
    for t in transitions:
        to_name = ((t.get("to") or {}).get("name") or "").strip()
        if to_name.lower() in want_lower:
            chosen = t
            break
    if not chosen and transitions:
        for t in transitions:
            to_name = ((t.get("to") or {}).get("name") or "").strip().lower()
            for want in want_lower:
                if want in to_name or to_name in want:
                    chosen = t
                    break
            if chosen:
                break

    if not chosen:
        # Workflow may require stepping through an intermediate state first.
        # e.g. TO DO -> In Progress -> Done (Done only appears after In Progress).
        if st == "closed":
            in_progress_names = {
                n.lower()
                for n in (cfg["status_name_map"].get("in_progress")
                          or _DEFAULT_JIRA_STATUS_NAMES.get("in_progress", []))
            }
            step_t = None
            for t in transitions:
                to_name = ((t.get("to") or {}).get("name") or "").strip().lower()
                if to_name in in_progress_names or any(w in to_name for w in in_progress_names):
                    step_t = t
                    break
            if step_t:
                # Find due-at field key from the step transition's fields
                step_fields = step_t.get("fields") or {}
                step_due_key = None
                for fk, fv in step_fields.items():
                    fname = str((fv or {}).get("name") or "").strip().lower()
                    if "due" in fname:
                        step_due_key = fk
                        break
                step_payload = {"transition": {"id": step_t.get("id")}}
                if due_at and step_due_key:
                    step_payload["fields"] = {step_due_key: due_at.isoformat()}
                elif due_at:
                    step_payload["fields"] = {"customfield_10521": due_at.isoformat()}
                step_comment = comment or "Moving to Done"
                step_payload["update"] = {
                    "comment": [{"add": {"body": _text_to_adf(step_comment)}}]
                }
                ok_step, body_step = _jira_request(
                    cfg, f"/rest/api/3/issue/{issue_key}/transitions", "POST", step_payload
                )
                if ok_step:
                    # Re-fetch transitions after stepping to In Progress
                    ok_r, body_r = _jira_request(
                        cfg, f"/rest/api/3/issue/{issue_key}/transitions?expand=transitions.fields", "GET"
                    )
                    if ok_r:
                        transitions = body_r.get("transitions") or []
                        for t in transitions:
                            to_name = ((t.get("to") or {}).get("name") or "").strip()
                            if to_name.lower() in want_lower:
                                chosen = t
                                break

        if not chosen:
            names = [((x.get("to") or {}).get("name")) for x in transitions]
            return {
                "ok": False,
                "error": (
                    f"No Jira transition to match status \"{st}\". "
                    f"Available targets: {names}. "
                    "Set JIRA_STATUS_TO_JIRA_NAMES in jira_config.py if your workflow uses other names."
                ),
            }

    tid = chosen.get("id")
    payload = {"transition": {"id": tid}}
    if st == "closed":
        carry = _fetch_done_fields(cfg, issue_key, due_at=due_at)
        if carry:
            payload["fields"] = carry
    else:
        chosen_fields = chosen.get("fields") or {}
        due_key = None
        for fk, fv in chosen_fields.items():
            name = str((fv or {}).get("name") or "").strip().lower()
            if name in ("due date", "due at") or ("due" in name and "date" in name):
                due_key = fk
                break
        if due_at and due_key:
            payload["fields"] = {due_key: due_at.isoformat()}
    if comment and str(comment).strip():
        payload["update"] = {
            "comment": [{"add": {"body": _text_to_adf(str(comment).strip())}}]
        }

    ok2, body2 = _jira_request(
        cfg,
        f"/rest/api/3/issue/{issue_key}/transitions",
        "POST",
        payload,
    )
    if not ok2:
        code = body2.get("_http_code", "?")
        detail = _parse_jira_error_body(body2.get("_body", ""))
        # If workflow requires/accepts due date via transition screen, this instance likely
        # does not expose that field; fall back to transition-only so status can still move.
        if "duedate" in (detail or "").lower():
            ok3, body3 = _jira_request(
                cfg,
                f"/rest/api/3/issue/{issue_key}/transitions",
                "POST",
                {"transition": {"id": tid}},
            )
            if ok3:
                return {"ok": True}
            code = body3.get("_http_code", "?")
            detail = _parse_jira_error_body(body3.get("_body", ""))
        return {"ok": False, "error": f"Transition POST HTTP {code}: {detail}"}
    return {"ok": True}


def add_issue_comment(issue_key, text):
    """Append a plain-text comment (ADF) to an issue."""
    cfg = load_jira_settings()
    if not cfg or not issue_key or not (text or "").strip():
        return {"ok": False, "error": "Missing config, key, or comment text"}
    payload = {"body": _text_to_adf(text.strip())}
    ok, body = _jira_request(
        cfg, f"/rest/api/3/issue/{issue_key}/comment", "POST", payload
    )
    if not ok:
        code = body.get("_http_code", "?")
        detail = _parse_jira_error_body(body.get("_body", ""))
        return {"ok": False, "error": f"Comment HTTP {code}: {detail}"}
    return {"ok": True}


def sync_item_jira_status(item, new_status: str, notes_for_comment=None, due_at=None):
    """
    Transition Jira for this item's issue to new_status; optional comment from notes.
    """
    key = (item.jira_issue_key or "").strip()
    if not key:
        return {"ok": True, "skipped": True}
    tr = transition_issue(key, new_status, comment=notes_for_comment, due_at=due_at)
    if not tr.get("ok"):
        return tr
    return {"ok": True}

