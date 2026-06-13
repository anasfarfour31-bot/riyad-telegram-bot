import os, json, requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

JSON_PATH = "hadiths.json"
STATE_PATH = "used.json"


def load_hadiths():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_used():
    if not os.path.exists(STATE_PATH):
        return []
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_used(used):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(used, f)


def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})


def pick_hadith(hadiths, used):
    for h in hadiths:
        if h["number"] not in used:
            return h
    return hadiths[0]  # reset if finished


def format_hadith(h):
    return f"""📚 حديث اليوم

{h.get('text','')}

📖 الكتاب: {h.get('book','')}
📌 الباب: {h.get('chapter','')}
🔢 الرقم: {h.get('number','')}
"""


def main():
    hadiths = load_hadiths()
    used = load_used()

    hadith = pick_hadith(hadiths, used)

    send_message(format_hadith(hadith))

    used.append(hadith["number"])
    save_used(used)


if __name__ == "__main__":
    main()
