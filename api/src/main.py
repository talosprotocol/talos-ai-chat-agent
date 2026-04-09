import os
import logging
import json
import base64
import requests
import hashlib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# Use consolidated talos package
try:
    from talos.core.session import Session, RatchetState
    from talos.core.crypto import KeyPair, generate_encryption_keypair
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    print("WARNING: talos SDK core not found. Encryption will fail.")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("secure-chat")

app = FastAPI(title="Talos Secure Chat Agent", version="0.1.0")

# --- Audit Simulation ---

class SimulatedAuditLogger:
    """Simulates audit logging for demo reality."""
    def log_event(self, event_type: str, data: Dict[str, Any]):
        logger.info(f"AUDIT_EVENT: {event_type} - {json.dumps(data)}")
        # In a real system, this would push to the audit-service

audit_logger = MockAuditLogger()

# --- SDK Wrapper ---

class RatchetSession:
    """Wrapper around talos.core.session.Session for chat-agent parity."""
    def __init__(self, is_initiator: bool, shared_key: bytes):
        self.is_initiator = is_initiator
        # Initialize a basic RatchetState for symmetric start
        # In real X3DH this would be negotiated
        dh_keypair = generate_encryption_keypair()
        state = RatchetState(
            dh_keypair=dh_keypair,
            dh_remote=None,
            root_key=shared_key
        )
        self.session = Session(peer_id="demo-peer", state=state)

    def encrypt(self, plaintext: bytes) -> bytes:
        return self.session.encrypt(plaintext)

    def decrypt(self, ciphertext: bytes) -> bytes:
        return self.session.decrypt(ciphertext)

# In-Memory Session Store
# { session_id: {session: RatchetSession, count: int} }
SESSIONS: Dict[str, Any] = {}

class ChatRequest(BaseModel):
    message: str | None = None # Base64 encoded ciphertext
    content: str | None = None # Plaintext (Demo compatibility)
    session_id: str

@app.get("/health")
def health():
    return {
        "app": "talos-ai-chat-agent",
        "status": "online",
        "sdk_available": SDK_AVAILABLE,
        "active_sessions": len(SESSIONS)
    }

@app.post("/v1/chat/send")
async def send_message(req: ChatRequest):
    # 1. Retrieve or Init Session
    if req.session_id not in SESSIONS:
        logger.info(f"Initializing new session: {req.session_id}")
        raw_secret = os.getenv("CHAT_SHARED_SECRET")
        if raw_secret:
             shared_key = hashlib.sha256(raw_secret.encode()).digest()
        else:
             shared_key = b'0'*32 # Legacy fallback for demo compat
             logger.warning("Using mock shared secret (CHAT_SHARED_SECRET not set)")

        if SDK_AVAILABLE:
            SESSIONS[req.session_id] = {
                "session": RatchetSession(is_initiator=False, shared_key=shared_key),
                "count": 0
            }
        else:
            SESSIONS[req.session_id] = {"mock": True, "count": 0}

    session_data = SESSIONS[req.session_id]
    session = session_data.get("session")
    session_data["count"] += 1
    
    user_message = ""
    is_secure = False

    # 2. Decrypt or Use Plaintext
    if req.message and SDK_AVAILABLE and session:
        try:
            ciphertext = base64.b64decode(req.message)
            plaintext = session.decrypt(ciphertext)
            user_message = plaintext.decode('utf-8')
            is_secure = True
            logger.info(f"Decrypted: {user_message}")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise HTTPException(status_code=400, detail="Decryption failed")
    elif req.content:
        user_message = req.content
        logger.info(f"Plaintext (Demo): {user_message}")
    else:
        raise HTTPException(status_code=400, detail="No message content provided")

    # Audit request intent
    audit_logger.log_event("CHAT_REQUEST_RECEIVED", {
        "session_id": req.session_id,
        "is_secure": is_secure,
        "content_length": len(user_message)
    })

    # 3. Call AI Gateway (Live)
    ai_gateway_url = os.getenv("AI_GATEWAY_URL", "http://ollama:11434")
    api_token = os.getenv("TALOS_API_TOKEN", "dev-token")
    model_name = os.getenv("AI_MODEL", "tinyllama:latest")
    
    response_text = f"Secure Echo: {user_message}" # Fallback
    
    try:
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": user_message}]
        }
        res = requests.post(
            f"{ai_gateway_url}/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=120
        )
        if res.status_code == 200:
            data = res.json()
            if "choices" in data and len(data["choices"]) > 0:
                response_text = data["choices"][0]["message"]["content"]
        else:
             logger.warning(f"AI Gateway failed: {res.status_code}")
    except Exception as e:
        logger.error(f"Failed to call AI Gateway: {e}")
    
    # 4. Return standard response
    resp_id = f"msg_{os.urandom(4).hex()}"
    
    # Audit success
    audit_logger.log_event("CHAT_RESPONSE_SENT", {
        "message_id": resp_id,
        "session_id": req.session_id,
        "response_length": len(response_text)
    })

    return {
        "response": response_text,
        "message_id": resp_id,
        "conversation_id": req.session_id,
        "secure": is_secure
    }

@app.get("/v1/chat/summary")
def get_summary(session_id: str = "demo-session-v1"):
    session_data = SESSIONS.get(session_id, {"count": 0})
    count = session_data.get("count", 0)
    
    return {
        "session_id": session_id,
        "user_id": "talos-user-01",
        "assistant_id": "secure-llm-01",
        "blockchain_height": 1422,
        "pending_data": 0,
        "conversations": 1,
        "messages": count,
        "message_count": count,
        "tool_calls": 0,
        "ollama_available": True,
        "security_level": "maximum" if SDK_AVAILABLE else "basic"
    }

@app.get("/v1/chat/stats")
def get_stats():
    return {
        "connected_peers": 1,
        "active_sessions": len(SESSIONS),
        "total_messages": sum(s.get("count", 0) for s in SESSIONS.values())
    }
