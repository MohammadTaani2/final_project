import os
import re
import json

INPUT_DIR = "raw_text/law"
OUT_FILE = "prepared/laws_chunks.jsonl"

os.makedirs("prepared", exist_ok=True)

import re
import unicodedata

def split_law_by_article(text: str, min_len=80, max_chars=3500):
    # 1) Normalize Arabic presentation forms -> normal Arabic
    text = unicodedata.normalize("NFKC", text)

    # 2) Normalize newlines
    text = re.sub(r"\n{2,}", "\n", text).strip()

    # 3) Split by lines that start with "المادة" or "مادة" + number (Arabic or Western digits)
    pattern = r"(?=^\s*(?:المادة|مادة)\s*[0-9٠-٩]+\s*$)"
    parts = re.split(pattern, text, flags=re.MULTILINE)

    # 4) Clean + filter + safety split (too long chunks)
    chunks = []
    for p in parts:
        p = p.strip()
        if len(p) < min_len:
            continue

        if len(p) <= max_chars:
            chunks.append(p)
        else:
            for i in range(0, len(p), max_chars):
                sub = p[i:i+max_chars].strip()
                if len(sub) >= min_len:
                    chunks.append(sub)

    return chunks

def read_text_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        # common Arabic fallback
        with open(path, "r", encoding="cp1256", errors="replace") as f:
            return f.read()

count = 0

with open(OUT_FILE, "w", encoding="utf-8") as out:
    for fname in sorted(os.listdir(INPUT_DIR)):
        if not fname.lower().endswith(".txt"):
            continue

        path = os.path.join(INPUT_DIR, fname)
        text = read_text_file(path)

        chunks = split_law_by_article(text)

        # law_name can just be filename for now
        law_name = os.path.splitext(fname)[0]

        for i, chunk in enumerate(chunks, start=1):
            rec = {
                "id": f"law:{law_name}:{i}",
                "text": chunk,
                "metadata": {
                    "doc_type": "law",
                    "jurisdiction": "JO",
                    "language": "ar",
                    "source_file": fname,
                    "law_name": law_name,
                    "chunk_index": i
                }
            }
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1

print(f"✅ Saved {count} law chunks to {OUT_FILE}")



