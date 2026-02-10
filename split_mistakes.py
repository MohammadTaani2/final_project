import os
import re
import json
import unicodedata

INPUT_DIR = "raw_text/mistakes"
OUT_FILE = "prepared/mistakes_chunks.jsonl"

os.makedirs("prepared", exist_ok=True)

def normalize_ar(text: str) -> str:
    # Fix Arabic presentation forms (ﻼ etc.) -> normal Arabic
    text = unicodedata.normalize("NFKC", text)
    # Normalize newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text

def split_mistakes(text: str, min_len=80, max_chars=2500):
    text = normalize_ar(text).strip()

    # Split at numbered headings like:
    # 1- , 2- , 1. , ١- , ٢-
    pattern = r"(?=^\s*(?:\d+|[٠-٩]+)\s*[-\.]\s*)"
    parts = re.split(pattern, text, flags=re.MULTILINE)

    parts = [p.strip() for p in parts if len(p.strip()) >= min_len]

    # Fallback if numbering isn't detected well
    if len(parts) < 2:
        parts = [p.strip() for p in re.split(r"\n{2,}", text) if len(p.strip()) >= min_len]

    # Safety split if any chunk is too long
    final_parts = []
    for p in parts:
        if len(p) <= max_chars:
            final_parts.append(p)
        else:
            # split by punctuation/newline
            sentences = re.split(r"(?<=[\.،؛:\n])", p)
            buf = ""
            for s in sentences:
                if len(buf) + len(s) <= max_chars:
                    buf += s
                else:
                    if len(buf.strip()) >= min_len:
                        final_parts.append(buf.strip())
                    buf = s
            if len(buf.strip()) >= min_len:
                final_parts.append(buf.strip())

    return final_parts

def read_text_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(path, "r", encoding="cp1256", errors="replace") as f:
            return f.read()

count = 0

with open(OUT_FILE, "w", encoding="utf-8") as out:
    for fname in sorted(os.listdir(INPUT_DIR)):
        if not fname.lower().endswith(".txt"):
            continue

        path = os.path.join(INPUT_DIR, fname)
        text = read_text_file(path)

        chunks = split_mistakes(text)

        base = os.path.splitext(fname)[0]

        for i, chunk in enumerate(chunks, start=1):
            rec = {
                "id": f"mistake:{base}:{i}",
                "text": chunk,
                "metadata": {
                    "doc_type": "mistake",
                    "jurisdiction": "JO",
                    "language": "ar",
                    "source_file": fname,
                    "severity": "unknown",
                    "chunk_index": i
                }
            }
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1

print(f"✅ Saved {count} mistake chunks to {OUT_FILE}")
