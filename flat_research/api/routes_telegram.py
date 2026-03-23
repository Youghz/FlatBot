"""Telegram webhook: auto-link chat_id via /link CODE."""

import logging
import os
import secrets
import string

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from flat_research.api.dependencies import get_current_user, get_db
from flat_research.db import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["telegram"])


def _generate_code(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class LinkCodeResponse(BaseModel):
    code: str
    bot_username: str


@router.post("/api/me/telegram-code", response_model=LinkCodeResponse)
def generate_telegram_code(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate a one-time code for linking Telegram."""
    code = _generate_code()
    user.telegram_link_code = code
    db.commit()

    bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "FlatBotMtl")
    return LinkCodeResponse(code=code, bot_username=bot_username)


@router.post("/api/telegram/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive messages from Telegram. Handles /start and /link CODE."""
    body = await request.json()

    message = body.get("message", {})
    text = message.get("text", "").strip()
    chat_id = str(message.get("chat", {}).get("id", ""))

    if not text or not chat_id:
        return {"ok": True}

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")

    if text.startswith("/start"):
        msg = (
            "Bienvenue sur FlatBot!\n\n"
            "Pour lier votre compte, allez dans votre profil sur l'app "
            'et cliquez "Lier Telegram".\n'
            "Vous recevrez un code à envoyer ici avec:\n/link VOTRE_CODE"
        )
        _reply(bot_token, chat_id, msg)
        return {"ok": True}

    if text.startswith("/link"):
        parts = text.split()
        if len(parts) != 2:
            _reply(bot_token, chat_id, "Usage: /link VOTRE_CODE")
            return {"ok": True}

        code = parts[1].upper()
        user = db.query(User).filter(User.telegram_link_code == code).first()

        if not user:
            _reply(bot_token, chat_id, "Code invalide ou expiré. Générez un nouveau code depuis l'app.")
            return {"ok": True}

        user.telegram_chat_id = chat_id
        user.telegram_link_code = None
        db.commit()

        _reply(bot_token, chat_id, f"Compte lié ! Vous recevrez les notifications pour {user.email}.")
        return {"ok": True}

    return {"ok": True}


def _reply(bot_token: str, chat_id: str, text: str) -> None:
    if not bot_token:
        return
    import requests

    try:
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": int(chat_id), "text": text},
            timeout=10,
        )
    except Exception as e:
        logger.error(f"Telegram reply failed: {e}")
