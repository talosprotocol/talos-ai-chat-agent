import os
import logging
import json
import base64
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

# Talos SDK
try:
    from talos_sdk_py.crypto.ratchet import RatchetSession
    from talos_sdk_py.crypto.primitives import KeyPair
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    print("WARNING: talos-sdk-py not found. Encryption will fail.")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("secure-chat")

app = FastAPI(title="Talos Secure Chat Agent", version="0.1.0")

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
             import hashlib
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

    # 3. Call AI Gateway (Live)
    ai_gateway_url = os.getenv("AI_GATEWAY_URL", "http://talos-ai-gateway:8000")
    api_token = os.getenv("TALOS_API_TOKEN", "dev-token")
    
    response_text = f"Secure Echo: {user_message}" # Fallback
    
    try:
        # We need a proper chat request structure
        payload = {
            "model": "gpt-3.5-turbo", # Default or from env
            "messages": [{"role": "user", "content": user_message}]
        }
        res = requests.post(
            f"{ai_gateway_url}/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=10
        )
        if res.status_code == 200:
            data = res.json()
            if "choices" in data and len(data["choices"]) > 0:
                response_text = data["choices"][0]["message"]["content"]
            else:
                 logger.warning("AI Gateway returned no choices")
        else:
             logger.warning(f"AI Gateway failed: {res.status_code} {res.text}")
             if res.status_code == 404:
                  response_text += " [AI Gateway Not Found]"
    except Exception as e:
        logger.error(f"Failed to call AI Gateway: {e}")
        response_text += " [AI Offline]"
    
    # 4. Return standard response (Dashboard Expected Format)
    return {
        "response": response_text,
        "message_id": f"msg_{os.urandom(4).hex()}",
        "conversation_id": req.session_id,
        "secure": is_secure
    }

@app.get("/v1/chat/summary")
def get_summary(session_id: str):
    count = SESSIONS.get(session_id, {}).get("count", 0)
    return {
        "session_id": session_id,
        "message_count": count,
        "security_level": "maximum" if SDK_AVAILABLE else "basic"
    }
