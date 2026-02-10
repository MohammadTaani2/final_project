import pdfplumber
import os
import arabic_reshaper
from bidi.algorithm import get_display

input_dir = "raw_pdfs/mistakes"
output_dir = "raw_text/mistakes"

os.makedirs(output_dir, exist_ok=True)

def fix_arabic(text):
    reshaped = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped)
    return bidi_text

for file in os.listdir(input_dir):
    if file.endswith(".pdf"):
        print("Processing:", file)
        text = ""
        with pdfplumber.open(os.path.join(input_dir, file)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += fix_arabic(page_text) + "\n"

        with open(os.path.join(output_dir, file.replace(".pdf", ".txt")),
                  "w", encoding="utf-8") as f:
            f.write(text)

print('done')