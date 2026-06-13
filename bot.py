import datetime as dt
import html
import json
import os
import sys
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

import requests

TEXT_KEYS = (
    "text", "hadith", "matn", "nass", "content", "body", "arabic", "ar", "quote", "message"
)
META_KEYS = (
    "number", "no", "id", "hadith_no", "hadith_number", "chapter", "bab", "book", "source", "reference", "url"
)
CONTAINER_KEYS = (
    "hadiths", "items", "data", "results", "records", "pages", "chapters", "sections", "books"
)


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_space(value: str) -> str:
    return "\n".join(line.strip() for line in value.replace("\r\n", "\n").split("\n") if line.strip())


def first_text_from_dict(obj: Dict[str, Any]) -> Optional[str]:
    for key in TEXT_KEYS:
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return normalize_space(value)
    # Some exports use nested language objects, e.g. {"text": {"ar": "..."}}
    for key in TEXT_KEYS:
        value = obj.get(key)
        if isinstance(value, dict):
            for lang_key in ("ar", "arabic", "text", "value"):
                lang_value = value.get(lang_key)
                if isinstance(lang_value, str) and lang_value.strip():
                    return normalize_space(lang_value)
    return None


def compact_meta(obj: Dict[str, Any]) -> Dict[str, str]:
    meta: Dict[str, str] = {}
    for key in META_KEYS:
        value = obj.get(key)
        if value is None:
            continue
        if isinstance(value, (str, int, float)):
            meta[key] = str(value).strip()
    return meta


def extract_records(data: Any) -> List[Dict[str, str]]:
    """Extract hadith-like records from common JSON shapes.

    Supported examples:
    - [{"number": 1, "text": "..."}, ...]
    - {"hadiths": [{"text": "..."}]}
    - ["hadith text 1", "hadith text 2"]
    - nested Turath-like exports containing pages/chapters/sections
    """
    records: List[Dict[str, str]] = []

    def walk(node: Any, inherited: Optional[Dict[str, str]] = None) -> None:
        inherited = inherited or {}
        if isinstance(node, str):
            text = normalize_space(node)
            if len(text) >= 12:
                records.append({**inherited, "text": text})
            return

        if isinstance(node, list):
            for item in node:
                walk(item, inherited)
            return

        if not isinstance(node, dict):
            return

        current_meta = {**inherited, **compact_meta(node)}
        text = first_text_from_dict(node)
        if text and len(text) >= 12:
            records.append({**current_meta, "text": text})
            return

        # Prefer common container keys, but fall back to walking all nested lists/dicts.
        walked_any_container = False
        for key in CONTAINER_KEYS:
            if key in node:
                walk(node[key], current_meta)
                walked_any_container = True
        if not walked_any_container:
            for value in node.values():
                if isinstance(value, (list, dict)):
                    walk(value, current_meta)

    walk(data)

    # Deduplicate while preserving order. Prefer identifiers when present so that
    # two separately numbered hadiths with identical wording are not collapsed.
    seen = set()
    unique: List[Dict[str, str]] = []
    for rec in records:
        text = rec.get("text", "").strip()
        if not text:
            continue
        dedupe_key = (
            rec.get("number")
            or rec.get("no")
            or rec.get("hadith_no")
            or rec.get("hadith_number")
            or rec.get("id")
            or "",
            rec.get("book", ""),
            rec.get("chapter", ""),
            text,
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        unique.append(rec)
    return unique


def choose_daily_record(records: List[Dict[str, str]]) -> Dict[str, str]:
    override = os.getenv("DAILY_INDEX_OVERRIDE")
    if override is not None:
        index = int(override) % len(records)
        return records[index]

    tz_name = os.getenv("TIMEZONE", "Europe/Istanbul")
    today = dt.datetime.now(ZoneInfo(tz_name)).date()
    start_date = dt.date.fromisoformat(os.getenv("START_DATE", "2026-01-01"))
    days = max(0, (today - start_date).days)
    index = days % len(records)
    return records[index]


def build_message(record: Dict[str, str]) -> str:
    title = os.getenv("MESSAGE_TITLE", "📚 حديث اليوم")
    default_source = os.getenv("DEFAULT_SOURCE", "رياض الصالحين")

    text = html.escape(record.get("text", "").strip())
    parts = [f"<b>{html.escape(title)}</b>", "", text]

    details = []
    number = record.get("number") or record.get("no") or record.get("hadith_no") or record.get("hadith_number") or record.get("id")
    chapter = record.get("chapter") or record.get("bab")
    book = record.get("book")
    source = record.get("source") or record.get("reference") or default_source
    url = record.get("url") or os.getenv("SOURCE_URL", "https://app.turath.io/book/2348")

    if source:
        details.append(f"المصدر: {source}")
    if book:
        details.append(f"الكتاب: {book}")
    if chapter:
        details.append(f"الباب: {chapter}")
    if number:
        details.append(f"رقم: {number}")
    if url:
        details.append(url)

    if details:
        parts.extend(["", html.escape(" | ".join(details))])

    return "\n".join(parts)


def split_message(message: str, limit: int = 3900) -> List[str]:
    """Telegram sendMessage allows 4096 chars after entity parsing; use a safety margin."""
    if len(message) <= limit:
        return [message]

    chunks: List[str] = []
    remaining = message
    while len(remaining) > limit:
        split_at = remaining.rfind("\n\n", 0, limit)
        if split_at == -1:
            split_at = remaining.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def send_telegram_message(token: str, chat_id: str, message: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chunk in split_message(message):
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        try:
            payload = response.json()
        except Exception:
            payload = {"ok": False, "description": response.text}
        if not response.ok or not payload.get("ok"):
            raise RuntimeError(f"Telegram sendMessage failed: HTTP {response.status_code} {payload}")


def main() -> int:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    json_path = os.getenv("HADITH_JSON_PATH", "hadiths.json")

    missing = [name for name, value in {
        "TELEGRAM_BOT_TOKEN": token,
        "TELEGRAM_CHAT_ID": chat_id,
    }.items() if not value]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        return 2

    data = load_json(json_path)
    records = extract_records(data)
    if not records:
        print(f"No hadith records found in {json_path}. Check JSON keys or format.", file=sys.stderr)
        return 3

    record = choose_daily_record(records)
    message = build_message(record)
    send_telegram_message(token, chat_id, message)
    print("Sent daily hadith successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
