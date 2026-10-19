"""Environment-only Resend delivery with bounded requests and sanitized failures."""

import os
from dataclasses import dataclass, field
from urllib.parse import urlencode

import httpx
from pydantic import AnyHttpUrl, EmailStr, SecretStr, TypeAdapter, ValidationError


class EmailDeliveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class PasswordResetSettings:
    api_key: SecretStr = field(repr=False)
    sender: str
    frontend_url: str
    expire_minutes: int = 30


def load_password_reset_settings() -> PasswordResetSettings:
    key = os.environ.get("RESEND_API_KEY", "").strip()
    try:
        if not key or any(not 33 <= ord(character) <= 126 for character in key):
            raise ValueError
        sender = str(TypeAdapter(EmailStr).validate_python(os.environ.get("RESEND_FROM_EMAIL", "")))
        origin = TypeAdapter(AnyHttpUrl).validate_python(os.environ.get("NEXOVA_FRONTEND_URL", ""))
        if (
            origin.username is not None
            or origin.password is not None
            or origin.path not in (None, "", "/")
            or origin.query is not None
            or origin.fragment is not None
            or origin.port == 0
            or (
                origin.scheme != "https"
                and origin.host not in ("localhost", "127.0.0.1", "[::1]")
            )
        ):
            raise ValueError
        minutes = int(os.environ.get("PASSWORD_RESET_EXPIRE_MINUTES", "30"))
        if not 15 <= minutes <= 60:
            raise ValueError
    except (ValueError, ValidationError):
        raise RuntimeError("Invalid password reset configuration") from None
    return PasswordResetSettings(SecretStr(key), sender, str(origin).rstrip("/"), minutes)


def send_password_reset_email(
    email: str,
    token: SecretStr,
    settings: PasswordResetSettings,
    *,
    transport: httpx.BaseTransport | None = None,
) -> None:
    query = urlencode({"token": token.get_secret_value()})
    link = f"{settings.frontend_url}/reset-password?{query}"
    payload = {
        "from": settings.sender,
        "to": [email],
        "subject": "Restablece tu contrase\u00f1a de Nexova",
        "text": (
            "Recibimos una solicitud para restablecer tu contrase\u00f1a.\n\n"
            f"{link}\n\n"
            f"El enlace vence en {settings.expire_minutes} minutos y solo puede usarse una vez.\n"
            "Si no solicitaste el cambio, ignora este correo."
        ),
    }
    try:
        with httpx.Client(
            timeout=10.0, follow_redirects=False, trust_env=False, transport=transport
        ) as client:
            response = client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.api_key.get_secret_value()}"},
                json=payload,
            )
        if not 200 <= response.status_code < 300:
            raise EmailDeliveryError("Password reset email delivery failed")
    except httpx.HTTPError:
        raise EmailDeliveryError("Password reset email delivery failed") from None