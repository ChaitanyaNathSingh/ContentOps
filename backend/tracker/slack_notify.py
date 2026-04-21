"""
Post plan/update entries into Slack: one parent message per (date, kind), thread replies per entry.
Uses backend/slack_config.py (SLACK_BOT_TOKEN, SLACK_CHANNEL).
"""

import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

from django.db import IntegrityError

from .models import DailyEntry, SlackDayThread

logger = logging.getLogger(__name__)


def load_slack_config():
    backend_dir = Path(__file__).resolve().parent.parent
    config_path = backend_dir / "slack_config.py"
    if not config_path.exists():
        return {}
    cfg = {}
    with open(config_path, encoding="utf-8") as f:
        exec(compile(f.read(), str(config_path), "exec"), cfg)
    return cfg


def slack_post(token, payload):
    """POST JSON to Slack Web API. Returns (ok, response_dict)."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("ok", False), body
    except urllib.error.URLError as exc:
        return False, {"error": str(exc)}


def slack_update_message(token, channel, ts, text):
    """chat.update — refresh parent summary (member list / counts)."""
    data = json.dumps(
        {"channel": channel, "ts": ts, "text": text}
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.update",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("ok", False), body
    except urllib.error.URLError as exc:
        return False, {"error": str(exc)}


def _fmt(v, fallback="—"):
    return str(v).strip() if v is not None and str(v).strip() else fallback


def _format_item_line(n, it, include_status=False):
    parts = []
    if it.jira_issue_key and it.jira_issue_url:
        parts.append(f"<{it.jira_issue_url}|{it.jira_issue_key}>")
    elif it.jira_issue_key:
        parts.append(it.jira_issue_key)
    parts.append(_fmt(it.task_type))
    if it.customer and str(it.customer).strip():
        parts.append(_fmt(it.customer))
    if it.question_type and str(it.question_type).strip():
        parts.append(_fmt(it.question_type))
    if it.count is not None:
        parts.append(f"Count: {it.count}")
    if include_status:
        status_label = _fmt(getattr(it, "status", "")).replace("_", " ").title()
        parts.append(status_label)
    line = f"{n}. " + " · ".join(parts)
    if it.notes and str(it.notes).strip():
        line += f"\n    _{_fmt(it.notes)}_"
    return line


def format_plan_thread(entry):
    lines = [f"*{entry.member.display_name}* — 📋 Plan for {entry.entry_date}"]
    items = list(entry.items.all())
    if items:
        for n, it in enumerate(items, 1):
            lines.append(_format_item_line(n, it, include_status=False))
    elif entry.raw_text:
        lines.append(entry.raw_text)
    else:
        lines.append("_No tasks logged yet._")
    return "\n".join(lines)


def format_update_thread(entry):
    lines = [f"*{entry.member.display_name}* — ✅ Update for {entry.entry_date}"]
    items = list(entry.items.all())
    if items:
        for n, it in enumerate(items, 1):
            lines.append(_format_item_line(n, it, include_status=True))
    elif entry.raw_text:
        lines.append(entry.raw_text)
    else:
        lines.append("_No update logged yet._")
    return "\n".join(lines)


def build_parent_text(target_date, kind, entries):
    date_str = target_date.strftime("%A, %d %b %Y")
    count = len(entries)
    member_names = ", ".join(e.member.display_name for e in entries)
    if kind == "plan":
        return (
            f"📋 *Daily Plans — {date_str}*\n"
            f'{count} plan{"s" if count != 1 else ""} submitted today '
            f"by: {member_names}\n"
            f"_Replies below ↓_"
        )
    return (
        f"✅ *Daily Updates — {date_str}*\n"
        f'{count} update{"s" if count != 1 else ""} submitted today '
        f"by: {member_names}\n"
        f"_Replies below ↓_"
    )


def _entries_for_day_kind(entry_date, kind):
    return (
        DailyEntry.objects.filter(entry_date=entry_date, kind=kind)
        .select_related("member")
        .prefetch_related("items")
        .order_by("created_at")
    )


def _get_or_create_thread_row(target_date, kind, channel):
    try:
        return SlackDayThread.objects.get(digest_date=target_date, kind=kind)
    except SlackDayThread.DoesNotExist:
        try:
            return SlackDayThread.objects.create(
                digest_date=target_date, kind=kind, channel=channel
            )
        except IntegrityError:
            return SlackDayThread.objects.get(
                digest_date=target_date, kind=kind
            )


def notify_entry_slack_thread(entry):
    """
    Ensure Slack parent for (entry_date, kind), update parent summary, post this entry as a thread reply.
    Skips if slack_reply_ts already set or Slack is not configured.
    """
    entry = (
        DailyEntry.objects.select_related("member")
        .prefetch_related("items")
        .filter(pk=entry.pk)
        .first()
    )
    if not entry or entry.slack_reply_ts:
        return

    cfg = load_slack_config()
    token = cfg.get("SLACK_BOT_TOKEN", "")
    channel = cfg.get("SLACK_CHANNEL", "content-dashboard")
    if not token or (isinstance(token, str) and token.startswith("xoxb-PASTE")):
        return

    target_date = entry.entry_date
    kind = entry.kind

    thread = _get_or_create_thread_row(target_date, kind, channel)

    entries_list = list(_entries_for_day_kind(target_date, kind))
    parent_text = build_parent_text(target_date, kind, entries_list)

    if not thread.parent_ts:
        ok, resp = slack_post(token, {"channel": channel, "text": parent_text})
        if not ok:
            logger.warning(
                "Slack parent post failed: %s", resp.get("error", resp)
            )
            return
        SlackDayThread.objects.filter(pk=thread.pk).update(
            parent_ts=resp.get("ts")
        )
    else:
        ok, resp = slack_update_message(
            token, channel, thread.parent_ts, parent_text
        )
        if not ok:
            logger.warning(
                "Slack parent update failed: %s", resp.get("error", resp)
            )

    thread.refresh_from_db()
    if not thread.parent_ts:
        return

    reply_text = (
        format_plan_thread(entry)
        if kind == "plan"
        else format_update_thread(entry)
    )
    ok, resp = slack_post(
        token,
        {
            "channel": channel,
            "thread_ts": thread.parent_ts,
            "text": reply_text,
        },
    )
    if not ok:
        logger.warning(
            "Slack thread reply failed: %s", resp.get("error", resp)
        )
        return

    reply_ts = resp.get("ts")
    DailyEntry.objects.filter(pk=entry.pk).update(slack_reply_ts=reply_ts)
