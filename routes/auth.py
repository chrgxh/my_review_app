from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from config import settings

from helpers.email_renderer import render_password_reset_email_html
from helpers.email_sender import send_email_with_resend
from helpers.reset_tokens import (
    generate_raw_reset_token,
    get_reset_token_expiry,
    hash_reset_token,
)
from helpers.db import get_session
from helpers.auth import COOKIE_MAX_AGE, COOKIE_NAME, create_session_token
from helpers.security import verify_password, hash_password
from helpers.dependencies import get_current_user
from repositories.business_user_repository import get_business_user_by_email
from repositories.password_reset_token_repository import (
    create_password_reset_token,
    invalidate_user_password_reset_tokens,
    get_valid_password_reset_token,
    mark_password_reset_token_used,
)
from models.business_user import BusinessUser

router = APIRouter()
templates = Jinja2Templates(directory="templates")

LOGIN_ERROR_COOKIE = "login_error"
LOGIN_SUCCESS_COOKIE = "login_success"
CHANGE_PASSWORD_ERROR_COOKIE = "change_password_error"
FORGOT_PASSWORD_SUCCESS_COOKIE = "forgot_password_success"
FORGOT_PASSWORD_ERROR_COOKIE = "forgot_password_error"
RESET_PASSWORD_ERROR_COOKIE = "reset_password_error"
FLASH_COOKIE_MAX_AGE = 10


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    error = None
    success = None

    if request.cookies.get(LOGIN_ERROR_COOKIE) == "1":
        error = "Invalid email or password."

    if request.cookies.get(LOGIN_SUCCESS_COOKIE) == "password_changed":
        success = "Password updated successfully. Please log in again."

    response = templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": error,
            "success": success,
        },
    )

    response.delete_cookie(LOGIN_ERROR_COOKIE)
    response.delete_cookie(LOGIN_SUCCESS_COOKIE)
    return response


@router.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    user = await get_business_user_by_email(session, email)

    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        response = RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        response.set_cookie(
            key=LOGIN_ERROR_COOKIE,
            value="1",
            max_age=FLASH_COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=False,
        )
        return response

    if user.id is None:
        response = RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        response.set_cookie(
            key=LOGIN_ERROR_COOKIE,
            value="1",
            max_age=FLASH_COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=False,
        )
        return response

    token = create_session_token(user.id)

    response = RedirectResponse(
        url="/dashboard",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=COOKIE_MAX_AGE,
        samesite="lax",
        secure=False,
    )
    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: BusinessUser = Depends(get_current_user),
):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "current_user": current_user},
    )


@router.post("/logout")
async def logout():
    response = RedirectResponse(
        url="/login",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("/change-password", response_class=HTMLResponse)
async def change_password_page(
    request: Request,
    current_user: BusinessUser = Depends(get_current_user),
):
    error = None

    if request.cookies.get(CHANGE_PASSWORD_ERROR_COOKIE) == "incorrect_current":
        error = "Current password is incorrect."

    response = templates.TemplateResponse(
        "change_password.html",
        {
            "request": request,
            "error": error,
            "success": None,
        },
    )

    response.delete_cookie(CHANGE_PASSWORD_ERROR_COOKIE)
    return response


@router.post("/change-password")
async def change_password(
    current_user: BusinessUser = Depends(get_current_user),
    current_password: str = Form(...),
    new_password: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    if not verify_password(current_password, current_user.password_hash):
        response = RedirectResponse(
            url="/change-password",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        response.set_cookie(
            key=CHANGE_PASSWORD_ERROR_COOKIE,
            value="incorrect_current",
            max_age=FLASH_COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=False,
        )
        return response

    current_user.password_hash = hash_password(new_password)
    session.add(current_user)
    await session.commit()

    response = RedirectResponse(
        url="/login",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.delete_cookie(COOKIE_NAME)
    response.set_cookie(
        key=LOGIN_SUCCESS_COOKIE,
        value="password_changed",
        max_age=FLASH_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return response

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    success = None

    if request.cookies.get(FORGOT_PASSWORD_SUCCESS_COOKIE) == "1":
        success = "If an account exists for that email, a reset link has been sent."

    response = templates.TemplateResponse(
        "forgot_password.html",
        {
            "request": request,
            "success": success,
            "error": None,
        },
    )

    response.delete_cookie(FORGOT_PASSWORD_SUCCESS_COOKIE)
    return response


@router.post("/forgot-password")
async def forgot_password(
    email: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    user = await get_business_user_by_email(session, email)

    if user is not None and user.is_active and user.id is not None:
        user_id = user.id
        user_email = user.email

        raw_token = generate_raw_reset_token()
        token_hash = hash_reset_token(raw_token)
        expires_at = get_reset_token_expiry()

        await invalidate_user_password_reset_tokens(session, user_id)
        await create_password_reset_token(
            session=session,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        reset_link = f"{settings.base_url}/reset-password?token={raw_token}"
        html = render_password_reset_email_html(reset_link)

        await send_email_with_resend(
            resend_api_key=settings.resend_api_key,
            from_email=settings.from_email,
            to_email=user_email,
            subject="Reset your password",
            html=html,
        )

    response = RedirectResponse(
        url="/forgot-password",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.set_cookie(
        key=FORGOT_PASSWORD_SUCCESS_COOKIE,
        value="1",
        max_age=FLASH_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return response

@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    token: str | None = None,
):
    error = None

    if token is None:
        error = "Invalid or expired reset link."

    if request.cookies.get(RESET_PASSWORD_ERROR_COOKIE) == "invalid_token":
        error = "Invalid or expired reset link."

    response = templates.TemplateResponse(
        "reset_password.html",
        {
            "request": request,
            "error": error,
            "success": None,
            "token": token or "",
        },
    )

    response.delete_cookie(RESET_PASSWORD_ERROR_COOKIE)
    return response

@router.post("/reset-password")
async def reset_password(
    token: str = Form(...),
    new_password: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    token_hash = hash_reset_token(token)

    reset_token = await get_valid_password_reset_token(session, token_hash)
    if reset_token is None:
        response = RedirectResponse(
            url="/reset-password",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        response.set_cookie(
            key=RESET_PASSWORD_ERROR_COOKIE,
            value="invalid_token",
            max_age=FLASH_COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=False,
        )
        return response

    user_result = await session.exec(
        select(BusinessUser).where(BusinessUser.id == reset_token.user_id)
    )
    user = user_result.first()

    if user is None or not user.is_active:
        response = RedirectResponse(
            url="/reset-password",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        response.set_cookie(
            key=RESET_PASSWORD_ERROR_COOKIE,
            value="invalid_token",
            max_age=FLASH_COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=False,
        )
        return response

    user.password_hash = hash_password(new_password)
    session.add(user)
    await session.commit()

    await mark_password_reset_token_used(session, reset_token)

    response = RedirectResponse(
        url="/login",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.delete_cookie(COOKIE_NAME)
    response.set_cookie(
        key=LOGIN_SUCCESS_COOKIE,
        value="password_changed",
        max_age=FLASH_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return response