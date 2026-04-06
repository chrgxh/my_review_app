from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel.ext.asyncio.session import AsyncSession

from config import settings
from helpers.business_config import (
    build_from_email_from_slug,
    build_timezone_options,
    is_valid_timezone,
    normalize_slug,
    update_logo_asset,
)
from helpers.cache import business_cache
from helpers.db import get_session
from helpers.dependencies import get_current_user, get_current_business
from models.business import Business
from models.business_user import BusinessUser
from repositories.businesses import (
    get_business_by_id,
    is_business_slug_unique,
    save_business,
)


router = APIRouter()
templates = Jinja2Templates(directory="templates")


def render_business_config_template(
    request: Request,
    current_user: BusinessUser,
    current_business: Business,
    success_message: str | None = None,
    error_message: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    return templates.TemplateResponse(
        "business_config.html",
        {
            "request": request,
            "current_user": current_user,
            "current_business": current_business,
            "timezone_options": build_timezone_options(),
            "success_message": success_message,
            "error_message": error_message,
        },
        status_code=status_code,
    )


@router.get("/business-config", response_class=HTMLResponse)
async def business_config_page(
    request: Request,
    current_user: BusinessUser = Depends(get_current_user),
    current_business: Business = Depends(get_current_business),
):
    status = request.query_params.get("status")

    success_message = None
    error_message = None

    if status == "success":
        success_message = "Business settings updated successfully."
    elif status == "error":
        error_message = "Something went wrong while updating the business settings."

    return render_business_config_template(
        request=request,
        current_user=current_user,
        current_business=current_business,
        success_message=success_message,
        error_message=error_message,
    )


@router.post("/business-config", response_class=HTMLResponse)
async def update_business_config(
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    reply_to_email: str = Form(""),
    email_subject: str = Form(""),
    email_header: str = Form(""),
    default_email_text: str = Form(""),
    review_redirect_url: str = Form(""),
    timezone: str = Form(...),
    logo: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_session),
    current_user: BusinessUser = Depends(get_current_user),
    current_business: Business = Depends(get_current_business),
):
    current_business_id = current_business.id

    business = await get_business_by_id(session, current_business_id)

    if business is None:
        return RedirectResponse(url="/business-config?status=error", status_code=303)

    try:
        normalized_slug = normalize_slug(slug)
    except ValueError as exc:
        return render_business_config_template(
            request=request,
            current_user=current_user,
            current_business=current_business,
            error_message=str(exc),
            status_code=400,
        )

    if not is_valid_timezone(timezone):
        return render_business_config_template(
            request=request,
            current_user=current_user,
            current_business=current_business,
            error_message="Invalid timezone selected.",
            status_code=400,
        )

    is_unique = await is_business_slug_unique(
        session=session,
        slug=normalized_slug,
        exclude_business_id=business.id,
    )
    if not is_unique:
        return render_business_config_template(
            request=request,
            current_user=current_user,
            current_business=current_business,
            error_message="This email name is already in use.",
            status_code=400,
        )

    try:
        generated_from_email = build_from_email_from_slug(
            slug=normalized_slug,
            configured_from_email=settings.from_email,
        )
    except ValueError as exc:
        return render_business_config_template(
            request=request,
            current_user=current_user,
            current_business=current_business,
            error_message=str(exc),
            status_code=500,
        )

    old_slug = business.slug
    old_logo_url = business.logo_url

    business.name = name.strip()
    business.slug = normalized_slug
    business.from_email = generated_from_email
    business.reply_to_email = reply_to_email.strip() or None
    business.email_subject = email_subject.strip() or None
    business.email_header = email_header.strip() or None
    business.default_email_text = default_email_text.strip() or None
    business.review_redirect_url = review_redirect_url.strip() or None
    business.timezone = timezone

    try:
        business.logo_url = await update_logo_asset(
            logo=logo,
            old_slug=old_slug,
            new_slug=normalized_slug,
            old_logo_url=old_logo_url,
            base_url=settings.base_url,
        )
    except ValueError as exc:
        return render_business_config_template(
            request=request,
            current_user=current_user,
            current_business=business,
            error_message=str(exc),
            status_code=400,
        )

    business = await save_business(session, business)

    cache_key = f"business:{current_business_id}"
    business_cache.delete(cache_key)

    return RedirectResponse(url="/business-config?status=success", status_code=303)