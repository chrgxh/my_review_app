from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from fastapi import APIRouter, Request, Form, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config import settings

from helpers.db import get_session
from helpers.feedback_validation import validate_feedback_token
from helpers.datetime_formatter import format_datetime_for_business
from helpers.email_renderer import render_admin_feedback_notification_html
from helpers.email_sender import send_email_with_resend
from helpers.rate_limit import limiter
from helpers.request import get_client_ip, mask_token

from repositories.feedback_requests import respond_to_feedback_request
from repositories.businesses import get_business_by_id

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/feedback/{token}", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def feedback_page(
    request: Request,
    token: str,
    score: int = Query(..., ge=1, le=10),
    session: AsyncSession = Depends(get_session),
):
    client_ip = get_client_ip(request)
    logger.info(
        f"Feedback form opened | action=feedback_page | client_ip={client_ip} "
        f"| token={mask_token(token)}"
    )

    feedback_request, error_response = await validate_feedback_token(
        request=request,
        session=session,
        templates=templates,
        token=token,
    )

    if error_response:
        return error_response

    business = await get_business_by_id(session, feedback_request.business_id)

    logger.info(
        f"Feedback form loaded | action=feedback_page | client_ip={client_ip} "
        f"| token={mask_token(token)} | request_id={feedback_request.id} "
        f"| business_id={feedback_request.business_id} "
        f"| identifier={feedback_request.identifier}"
    )

    return templates.TemplateResponse(
        "feedback_page.html",
        {
            "request": request,
            "token": token,
            "score": score,
            "business_name": business.name if business else None,
            "logo_url": business.logo_url if business else None,
        },
    )


@router.post("/submit-feedback", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def submit_feedback(
    request: Request,
    token: str = Form(...),
    score: int = Form(...),
    comment: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    client_ip = get_client_ip(request)
    logger.info(
        f"Feedback submission attempted | action=submit_feedback | client_ip={client_ip} "
        f"| token={mask_token(token)} | score={score}"
    )

    feedback_request, error_response = await validate_feedback_token(
        request=request,
        session=session,
        templates=templates,
        token=token,
    )

    if error_response:
        return error_response

    feedback_request = await respond_to_feedback_request(
        session=session,
        feedback_request=feedback_request,
        score=score,
        comment=comment,
    )

    logger.info(
        f"Feedback submission success | action=submit_feedback | client_ip={client_ip} "
        f"| token={mask_token(token)} | score={score} | request_id={feedback_request.id} "
        f"| business_id={feedback_request.business_id}"
    )

    business = await get_business_by_id(session, feedback_request.business_id)

    if business and business.reply_to_email:
        admin_html = render_admin_feedback_notification_html(
            identifier=feedback_request.identifier,
            recipient_email=feedback_request.recipient_email,
            rating=feedback_request.rating,
            comment=feedback_request.comment,
            responded_at=format_datetime_for_business(
                feedback_request.responded_at,
                business.timezone if business else "UTC",
            ),
        )

        try:
            await send_email_with_resend(
                resend_api_key=settings.resend_api_key,
                from_email=business.from_email,
                to_email=business.reply_to_email,
                subject=f"New feedback received for {feedback_request.identifier}",
                html=admin_html,
                reply_to_email=business.reply_to_email,
            )
            logger.info(
                f"Admin feedback notification sent | token={mask_token(token)} "
                f"| to={business.reply_to_email}"
            )
        except Exception as exc:
            logger.exception(
                f"Failed to send admin feedback notification | token={mask_token(token)} "
                f"| error={exc}"
            )

    review_url = business.review_redirect_url if business else None
    show_review_link = bool(review_url)

    return templates.TemplateResponse(
        "thank_you.html",
        {
            "request": request,
            "title": "Thank you for your feedback",
            "message": "We appreciate you taking the time to share your experience.",
            "show_review_link": show_review_link,
            "review_url": review_url,
            "business_name": business.name if business else None,
            "logo_url": business.logo_url if business else None,
        },
    )