import os
import logging
import json
import base64
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
# { session_id: RatchetSession }
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
        shared_key = b'0'*32 # MOCK SHARED SECRET for DEMO
        if SDK_AVAILABLE:
            SESSIONS[req.session_id] = RatchetSession(is_initiator=False, shared_key=shared_key)
        else:
            SESSIONS[req.session_id] = {"mock": True}

    session = SESSIONS[req.session_id]
    user_message = ""
    is_secure = False

    # 2. Decrypt or Use Plaintext
    if req.message and SDK_AVAILABLE and not isinstance(session, dict):
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

    # 3. Simulate AI Logic (Echo + Mock Response)
    response_text = f"Secure Echo: {user_message}"
    
    # 4. Return standard response (Dashboard Expected Format)
    return {
        "response": response_text,
        "message_id": f"msg_{os.urandom(4).hex()}",
        "conversation_id": req.session_id,
        "secure": is_secure
    }

@app.get("/v1/chat/summary")
def get_summary(session_id: str):
    # Mock summary
    return {
        "session_id": session_id,
        "message_count": 5, # Mock
        "security_level": "maximum"
    }
