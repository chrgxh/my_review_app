import httpx
from loguru import logger


async def send_email_with_resend(
    resend_api_key: str,
    from_email: str,
    to_email: str,
    subject: str,
    html: str,
    reply_to_email: str | None = None,
) -> dict:
    url = "https://api.resend.com/emails"

    headers = {
        "Authorization": f"Bearer {resend_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }

    if reply_to_email:
        payload["reply_to"] = reply_to_email

    logger.info(f"Sending email to {to_email} via Resend")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)

    logger.info(f"Resend response status: {response.status_code}")
    response.raise_for_status()

    data = response.json()
    logger.info(f"Resend email sent successfully: {data}")

    return data