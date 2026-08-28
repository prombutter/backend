import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

async def send_reset_password_email(to_email: str, token: str) -> None:
    if not settings.SENDGRID_API_KEY:
        logger.warning(
            "SENDGRID_API_KEY is not set. Skipping email dispatch to %s", to_email
        )
        return

    # 프론트엔드 URL이 명확히 정해지지 않았다면 OAUTH_FRONTEND_REDIRECT 베이스를 활용하거나
    # 임시 URL(localhost:3000)을 사용한다.
    base_url = "http://localhost:3000"
    if settings.OAUTH_FRONTEND_REDIRECT:
        base_url = settings.OAUTH_FRONTEND_REDIRECT.replace("/auth/callback", "")
        
    reset_link = f"{base_url}/auth/reset-password?token={token}"
    
    payload = {
        "personalizations": [
            {
                "to": [{"email": to_email}],
                "subject": "[Prombutter] 비밀번호 재설정 안내"
            }
        ],
        "from": {"email": settings.MAIL_FROM_ADDRESS, "name": "Prombutter"},
        "content": [
            {
                "type": "text/html",
                "value": f"""
                <p>안녕하세요,</p>
                <p>비밀번호 재설정 요청이 접수되었습니다.</p>
                <p>아래 링크를 클릭하여 새 비밀번호를 설정해주세요. (이 링크는 10분 동안 유효합니다.)</p>
                <p><a href="{reset_link}">{reset_link}</a></p>
                <p>본인이 요청하지 않은 경우 이 메일을 무시하셔도 됩니다.</p>
                """
            }
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            logger.info("Password reset email successfully sent to %s", to_email)
    except httpx.HTTPStatusError as e:
        logger.error(
            "Failed to send email via SendGrid: %s - %s", 
            e.response.status_code, 
            e.response.text
        )
    except Exception as e:
        logger.error("Exception occurred while sending email: %s", str(e))
