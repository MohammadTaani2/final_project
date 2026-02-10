# ⚖️ Jordanian Legal Lease Assistant (AI-Powered)

An AI-powered legal assistant specialized in **Jordanian lease contracts**, built with **Flask**, **LLMs**, **Supabase (pgvector)**, and **Cohere reranking**.
The system can **create, edit, review, and explain lease contracts** in **Arabic or English**, while strictly enforcing **Jordanian landlord–tenant law**.

---

## 🚀 Features

* 📄 **Lease Contract Generation**

  * Residential, commercial, furnished, student, office, and more
  * Uses placeholders for missing personal data (legally safe)
  * Generates 12–18 legally compliant clauses

* ✏️ **Smart Contract Editing**

  * Preserves all existing data
  * Modifies only what the user requests
  * Prevents illegal or invalid edits

* 🔍 **Legal Review & Validation**

  * Detects illegal clauses
  * Highlights risky or missing terms
  * Validates contract dates automatically

* 📚 **Legal RAG System**

  * Jordanian lease clauses
  * Jordanian landlord–tenant law
  * Common legal mistakes

* 🌍 **Arabic & English Support**

  * Automatic language detection
  * Responses always match user language

* 📤 **PDF Export**

  * Generates RTL-safe Arabic PDFs

---

## 🧠 System Architecture

```
User (Browser)
   ↓
Flask Web App
   ↓
LLM Client (OpenAI GPT-4o-mini)
   ↓
Supabase Vector Store (pgvector)
   ↓
Cohere Reranker (Multilingual)
```

---

## 🗂️ Project Structure

```
mohammadtaani2-final_project/
├── flask_app.py            # Main Flask application
├── llm_client.py           # LLM logic + intent routing
├── supabase_client.py      # Vector search + Cohere reranking
├── config.py               # API & model configuration
├── prompts.py              # System & task prompts
├── pdf_utils.py            # PDF generation (Arabic RTL)
├── date_validator.py       # Date extraction & validation
├── utils.py                # Helper utilities
│
├── ingest_to_supabase.py   # Data migration to Supabase
├── split_clauses.py        # Lease clause chunking
├── split_law.py            # Law article chunking
├── split_mistakes.py       # Mistakes chunking
│
├── raw_text/               # Original legal texts
├── prepared/               # Chunked JSONL files
├── templates/
│   └── index.html          # Frontend UI
│
└── requirements.txt
```

---

## 🧪 Data Sources

* **Lease Contracts** (Arabic)
* **Jordanian Landlord–Tenant Law**
* **Common Legal Mistakes in Contracts**

All data is chunked, embedded, and stored in **Supabase pgvector** for semantic retrieval.

---

## 🔐 Environment Variables

Create a `.env` file or export the following:

```bash
OPENAI_API_KEY=your_openai_key
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key
COHERE_API_KEY=your_cohere_api_key
```

---

## 📦 Installation

```bash
# Clone repository
git clone https://github.com/your-username/jordanian-legal-lease-assistant.git
cd jordanian-legal-lease-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🗄️ Vector Database Setup (Supabase)

1. Create a Supabase project
2. Enable **pgvector**
3. Create tables:

   * `lease_clauses`
   * `law_documents`
   * `mistake_documents`
4. Run migration script:

```bash
python ingest_to_supabase.py
```

---

## ▶️ Run the Application

```bash
python flask_app.py
```

Open in browser:

```
http://localhost:5000
```

---

## 🧪 Health Check

```bash
GET /health
```

Returns:

* Supabase connection status
* Vector count
* Session & logging status

---

## 🛡️ Legal Safety Rules

The assistant **will refuse** to:

* Add illegal clauses
* Waive tenant rights
* Allow lock changes without court order
* Permit entry without 24-hour notice
* Draft non-lease contracts (employment, marriage, sales)

---

## 📄 Example Capabilities

* ✅ “Create a furnished apartment lease in Amman”
* ✏️ “Change rent to 400 JOD”
* 🔍 “Review this contract for legal issues”
* 💡 “Explain clause 7”
* 📤 “Export contract as PDF”

---

## 🏫 Academic Use

This project was developed as a **final academic project** demonstrating:

* Retrieval-Augmented Generation (RAG)
* Legal AI safety constraints
* Multilingual LLM orchestration
* Vector databases & reranking
* Real-world law-aware AI systems

---

## 👤 Author

**Mohammad Taani**
Final Project — AI & Legal Systems

---

## 📜 License

This project is for **educational and academic purposes only**.
Not intended to replace professional legal advice.

