"""
Flask application - COMPLETE FIX WITH EXPLICIT .ENV LOADING

Key fixes:
1. Explicit .env file path loading
2. Handles 3-tuple return from LLM (message, contract, action)
3. Only updates contract when action is 'updated'
4. Preserves contracts when action is 'unchanged'
"""

# =====================
# LOAD ENVIRONMENT VARIABLES FIRST - WITH EXPLICIT PATH
# =====================
from dotenv import load_dotenv
import os
from pathlib import Path

# Get the directory where app.py is located
basedir = Path(__file__).resolve().parent

# Load .env from the same directory as app.py
env_path = basedir / '.env'
print(f"🔍 Loading .env from: {env_path}")
print(f"📄 .env exists: {env_path.exists()}")

load_dotenv(dotenv_path=env_path, verbose=True, override=True)

# Verify it loaded
openai_key = os.getenv("OPENAI_API_KEY")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
cohere_key = os.getenv("COHERE_API_KEY")

print(f"🔑 OpenAI API Key loaded: {openai_key[:20] if openai_key else 'NOT FOUND'}...")
print(f"🔑 OpenAI Key length: {len(openai_key) if openai_key else 0}")
print(f"🔑 Supabase URL loaded: {supabase_url[:30] if supabase_url else 'NOT FOUND'}...")
print(f"🔑 Cohere API Key loaded: {cohere_key[:20] if cohere_key else 'NOT FOUND'}...")

import json
import uuid
import secrets
from datetime import timedelta, datetime, timezone

from flask import Flask, render_template, request, jsonify, send_file, session

from config import APIConfig, ModelConfig
from llm_client import LLMClient
from pdf_utils import generate_pdf

try:
    from flask_session import Session
    _HAS_FLASK_SESSION = True
except ImportError:
    Session = None
    _HAS_FLASK_SESSION = False


# =====================
# APP INIT
# =====================

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_USE_SIGNER"] = True

if _HAS_FLASK_SESSION:
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = os.path.join(os.getcwd(), "flask_session")
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
    Session(app)


# =====================
# LOGGING
# =====================

LOG_DIR = os.environ.get("LOG_DIR", "logs")
CHAT_LOG_PATH = os.path.join(LOG_DIR, "chat_log.jsonl")
os.makedirs(LOG_DIR, exist_ok=True)


def _get_chat_id() -> str:
    if "chat_id" not in session:
        session["chat_id"] = str(uuid.uuid4())
    return session["chat_id"]


def _next_turn_index() -> int:
    idx = session.get("turn_index", 0) + 1
    session["turn_index"] = idx
    return idx


def _client_ip() -> str:
    xff = request.headers.get("X-Forwarded-For")
    return xff.split(",")[0].strip() if xff else (request.remote_addr or "")


def _log_event(
    event_type: str,
    user_message: str | None = None,
    assistant_message: str | None = None,
    extra: dict | None = None,
):
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "chat_id": _get_chat_id(),
        "turn_index": session.get("turn_index"),
        "ip": _client_ip(),
        "user_agent": request.headers.get("User-Agent"),
        "path": request.path,
        "user_message": user_message,
        "assistant_message": assistant_message,
    }
    if extra:
        record.update(extra)

    with open(CHAT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# =====================
# LLM CLIENT INIT
# =====================

try:
    print("\n" + "="*60)
    print("🚀 Initializing LLM Client...")
    print("="*60)
    
    api_config = APIConfig.from_env()
    
    print(f"✅ API Config loaded successfully")
    print(f"   OpenAI key: {api_config.openai_api_key[:20]}...")
    print(f"   Supabase URL: {api_config.supabase_url}")
    
    llm_client = LLMClient(
        openai_api_key=api_config.openai_api_key,
        supabase_url=api_config.supabase_url,
        supabase_key=api_config.supabase_key,
        cohere_api_key=api_config.cohere_api_key,
        config=ModelConfig(),
    )
    print("✅ LLM Client initialized successfully")
    print("="*60 + "\n")
    
except ValueError as e:
    print(f"❌ Error initializing LLM client: {e}")
    print(f"   This usually means environment variables are missing")
    print(f"   Check your .env file at: {env_path}")
    llm_client = None
except Exception as e:
    print(f"❌ Unexpected error initializing LLM client: {e}")
    import traceback
    traceback.print_exc()
    llm_client = None


# =====================
# SESSION HELPERS
# =====================

def _get_current_contract():
    """Get current contract from Flask session"""
    contract = session.get("current_contract")
    if contract:
        print(f"📄 Retrieved contract from Flask session (length: {len(contract)})")
    else:
        print("📄 No contract in Flask session")
    return contract


def _set_current_contract(contract_text):
    """Store current contract in Flask session AND sync to LLM memory"""
    session["current_contract"] = contract_text
    session.modified = True
    
    # CRITICAL: Also sync to LLM client memory
    chat_id = _get_chat_id()
    if llm_client:
        llm_client.set_current_contract(contract_text, session_id=chat_id)
    
    print(f"💾 Stored contract in session + LLM memory (length: {len(contract_text)})")


def _clear_current_contract():
    """Clear current contract from session AND LLM memory"""
    if "current_contract" in session:
        del session["current_contract"]
    session.modified = True
    
    # Clear from LLM memory too
    chat_id = _get_chat_id()
    if llm_client:
        llm_client.clear_contract(session_id=chat_id)
    
    print("🗑️ Cleared contract from session + LLM memory")


# =====================
# ROUTES
# =====================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    ✅ COMPLETE FIX: Handles 3-tuple return (message, contract, action)
    """
    if not llm_client:
        return jsonify({"error": "LLM client not initialized"}), 500

    try:
        data = request.get_json(silent=True) or {}
        user_message = (data.get("message") or "").strip()
        
        # Get contract from frontend or session
        frontend_contract = data.get("current_contract")
        session_contract = _get_current_contract()
        
        # Use frontend contract if provided, otherwise session
        current_contract = frontend_contract if frontend_contract else session_contract
        
        context_hints = data.get("context_hints")
        session.permanent = True

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        print(f"\n{'='*60}")
        print(f"📨 Incoming message: {user_message[:100]}")
        print(f"📦 Frontend contract: {'Yes' if frontend_contract else 'No'}")
        print(f"💾 Session contract: {'Yes' if session_contract else 'No'}")
        print(f"📋 Using contract: {'Yes' if current_contract else 'No'}")

        # Call LLM with contract and session ID - NOW RETURNS 3 VALUES
        chat_id = _get_chat_id()
        response, contract_returned, action = llm_client.get_chat_response(
            user_input=user_message,
            current_contract=current_contract,
            context_hints=context_hints,
            session_id=chat_id
        )
        
        print(f"🤖 LLM response length: {len(response)}")
        print(f"📄 Contract returned: {'Yes' if contract_returned else 'No'}")
        print(f"🎬 Action: {action}")
        
        # ✅ CRITICAL: Only update session when contract actually changed
        if action == 'updated':
            # Contract was created or modified
            _set_current_contract(contract_returned)
            print(f"✅ Contract UPDATED in session (length: {len(contract_returned)})")
            contract_to_send = contract_returned
        elif action == 'unchanged':
            # Contract exists but wasn't modified (e.g., illegal clause rejected)
            # Don't update session, but send it so frontend keeps displaying it
            print(f"📌 Contract UNCHANGED, keeping current display")
            contract_to_send = contract_returned
        else:  # action == 'none'
            # No contract exists
            print(f"❌ No contract")
            contract_to_send = None
        
        turn = _next_turn_index()

        _log_event(
            event_type="chat_turn",
            user_message=user_message,
            assistant_message=response,
            extra={
                "action": action,
                "has_contract": bool(current_contract),
                "contract_length": len(contract_to_send) if contract_to_send else 0
            }
        )

        return jsonify({
            "response": response,
            "contract": contract_to_send,
            "action": action,
            "chat_id": chat_id,
            "turn_index": turn,
        })

    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            _log_event(event_type="error_chat", extra={"error": str(e)})
        except Exception:
            pass
        return jsonify({"error": str(e)}), 500


@app.route("/api/review", methods=["POST"])
def review():
    if not llm_client:
        return jsonify({"error": "LLM client not initialized"}), 500

    try:
        data = request.get_json(silent=True) or {}
        contract_text = (data.get("contract_text") or "").strip()
        
        if not contract_text:
            contract_text = _get_current_contract()
        
        session.permanent = True

        if not contract_text:
            return jsonify({"error": "Contract text is required"}), 400

        review_response = llm_client.review_contract(contract_text)

        _log_event(
            event_type="review",
            user_message=contract_text[:200],
            assistant_message=review_response,
            extra={"text_len": len(contract_text)},
        )

        return jsonify({
            "review": review_response,
            "chat_id": _get_chat_id(),
        })

    except Exception as e:
        try:
            _log_event(event_type="error_review", extra={"error": str(e)})
        except Exception:
            pass
        return jsonify({"error": str(e)}), 500


@app.route("/api/export-pdf", methods=["POST"])
def export_pdf():
    try:
        data = request.get_json(silent=True) or {}
        contract_text = (data.get("contract_text") or "").strip()
        
        if not contract_text:
            contract_text = _get_current_contract()
        
        session.permanent = True

        if not contract_text:
            return jsonify({"error": "Contract text is required"}), 400

        _log_event(
            event_type="export_pdf",
            extra={"contract_len": len(contract_text)},
        )

        pdf_buffer = generate_pdf(contract_text)

        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="lease_contract.pdf",
        )

    except Exception as e:
        try:
            _log_event(event_type="error_export_pdf", extra={"error": str(e)})
        except Exception:
            pass
        return jsonify({"error": str(e)}), 500


@app.route("/api/clear-session", methods=["POST"])
def clear_session():
    """Clear session and contract memory"""
    try:
        _log_event(event_type="clear_session")
    except Exception:
        pass
    
    _clear_current_contract()
    session.clear()
    
    return jsonify({"status": "success"})


@app.route("/api/get-contract", methods=["GET"])
def get_contract():
    """Get current contract from session"""
    contract = _get_current_contract()
    return jsonify({
        "contract": contract,
        "has_contract": contract is not None,
        "contract_length": len(contract) if contract else 0
    })


@app.route("/health")
def health():
    """Health check endpoint"""
    health_info = {
        "status": "healthy",
        "llm_initialized": llm_client is not None,
        "logging": True,
        "log_path": CHAT_LOG_PATH,
        "server_side_sessions": _HAS_FLASK_SESSION,
        "session_contract_storage": True,
        "session_has_contract": _get_current_contract() is not None,
    }
    
    if llm_client:
        try:
            from config import DOC_TYPES
            count = llm_client.vector_store.count(DOC_TYPES["LEASE"])
            health_info["supabase_connection"] = "ok"
            health_info["lease_clauses_count"] = count
        except Exception as e:
            health_info["supabase_connection"] = f"error: {str(e)}"
    
    return jsonify(health_info)


# =====================
# ERROR HANDLERS
# =====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


# =====================
# MAIN
# =====================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 Starting Legal Lease Assistant")
    print("=" * 60)
    print("✅ Environment variables loaded from .env")
    print("✅ 3-tuple return handling (message, contract, action)")
    print("✅ Contract preservation on illegal clause rejection")
    print("✅ Smart contract update logic")
    print("=" * 60)
    
    # Final verification
    if llm_client:
        print("✅ LLM Client is ready")
    else:
        print("❌ LLM Client failed to initialize - check errors above")
    
    print("=" * 60)
    print(f"🌐 Server starting on http://0.0.0.0:5000")
    print("=" * 60 + "\n")
    
    app.run(host="0.0.0.0", port=5000, debug=True)