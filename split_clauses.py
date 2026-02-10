import os
import re
import json

# ======================
# CONFIG
# ======================
INPUT_DIR = "raw_text/leases"
OUTPUT = []

# ======================
# STEP 1: CLAUSE START DETECTOR
# ======================
CLAUSE_START_PATTERN = re.compile(
    r"""^(
        المادة\s+\d+ |
        البند\s+\d+ |
        المادة\s+(الأولى|الثانية|الثالثة|الرابعة|الخامسة|السادسة|السابعة|الثامنة|التاسعة|العاشرة) |
        (أولاً|ثانياً|ثالثاً|رابعاً|خامساً|سادساً|سابعاً|ثامناً|تاسعاً|عاشراً) |
        [أبجدهوزحطي]\s*[-–:] |
        \d+\s*[-–:.]
    )""",
    re.VERBOSE
)

# ======================
# STEP 2: SAFE CHUNKING
# ======================
def split_into_chunks(text):
    # Normalize whitespace
    text = re.sub(r'\n{2,}', '\n', text)

    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 0]

    chunks = []
    buffer = ""

    for line in lines:
        # If line looks like a clause start, start a new buffer
        if CLAUSE_START_PATTERN.match(line) and buffer:
            chunks.append(buffer.strip())
            buffer = line
        else:
            buffer += " " + line

    if buffer:
        chunks.append(buffer.strip())

    # Filter out very short junk
    return [c for c in chunks if len(c) > 40]


# ======================
# STEP 3: FIX BROKEN CLAUSES (FIXED!)
# ======================
def fix_broken_clauses(chunks):
    """
    Merge chunks into real clauses.
    IMPORTANT: Each chunk must keep its original source_file!
    """
    fixed = []
    current = None

    for chunk in chunks:
        text = chunk["text"].strip()

        if not text:
            continue

        # New clause starts
        if CLAUSE_START_PATTERN.match(text):
            # Save previous clause
            if current is not None:
                fixed.append(current)

            # Start new clause with THIS chunk's source file
            current = {
                "source_file": chunk["source_file"],  # ✅ Use chunk's file
                "text": text
            }
        else:
            # Continuation of current clause
            if current is not None:
                # Only merge if from SAME file
                if current["source_file"] == chunk["source_file"]:
                    current["text"] += " " + text
                else:
                    # Different file - save current and start new
                    fixed.append(current)
                    current = {
                        "source_file": chunk["source_file"],
                        "text": text
                    }
            else:
                # Metadata / intro text before first clause
                fixed.append({
                    "source_file": chunk["source_file"],
                    "text": text,
                    "type": "metadata"
                })

    if current is not None:
        fixed.append(current)

    return fixed


# ======================
# STEP 4: LOAD FILES
# ======================
print("Processing files...\n")

all_files = sorted([f for f in os.listdir(INPUT_DIR) if f.endswith(".txt")])

for filename in all_files:
    path = os.path.join(INPUT_DIR, filename)
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        
        if len(text.strip()) == 0:
            print(f"⚠️  {filename}: Empty file")
            continue
        
        chunks = split_into_chunks(text)
        
        if len(chunks) == 0:
            print(f"⚠️  {filename}: No chunks extracted")
            continue
        
        # Add all chunks with their source file
        for idx, chunk in enumerate(chunks):
            OUTPUT.append({
                "source_file": filename,  # ✅ Store correct filename
                "chunk_id": idx + 1,
                "text": chunk
            })
        
        print(f"✅ {filename}: {len(chunks)} chunks")
        
    except Exception as e:
        print(f"❌ {filename}: {e}")

print(f"\nTotal chunks from all files: {len(OUTPUT)}")

# ======================
# STEP 5: FIX CLAUSES
# ======================
OUTPUT_FIXED = fix_broken_clauses(OUTPUT)

# Assign global clause IDs
FINAL_OUTPUT = []
for i, c in enumerate(OUTPUT_FIXED, start=1):
    c["clause_id"] = i
    FINAL_OUTPUT.append(c)

print(f"After merging: {len(FINAL_OUTPUT)} final clauses\n")

# ======================
# STEP 6: VERIFY FILE DISTRIBUTION
# ======================
from collections import Counter

file_counts = Counter([c["source_file"] for c in FINAL_OUTPUT])

print("="*60)
print("CLAUSES PER FILE")
print("="*60)
for filename in sorted(file_counts.keys()):
    print(f"{filename}: {file_counts[filename]} clauses")

print(f"\nTotal unique files in output: {len(file_counts)}")
print(f"Expected files: {len(all_files)}")

if len(file_counts) < len(all_files):
    missing = set(all_files) - set(file_counts.keys())
    print(f"\n⚠️  Missing files: {missing}")

# ======================
# STEP 7: SAVE TO JSONL
# ======================
os.makedirs("prepared", exist_ok=True)

output_path = "prepared/leases_chunks.jsonl"

with open(output_path, "w", encoding="utf-8") as f:
    for c in FINAL_OUTPUT:
        record = {
            "id": f"lease:{c['source_file']}:{c['clause_id']}",
            "text": c["text"],
            "metadata": {
                "doc_type": "lease",
                "source_file": c["source_file"],
                "clause_id": c["clause_id"],
                "jurisdiction": "JO",
                "language": "ar"
            }
        }
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"\n✅ Saved {len(FINAL_OUTPUT)} clauses to {output_path}")