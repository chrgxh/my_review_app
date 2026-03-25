from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel.ext.asyncio.session import AsyncSession

from helpers.db import get_session
from helpers.auth import COOKIE_MAX_AGE, COOKIE_NAME, create_session_token
from helpers.security import verify_password, hash_password
from repositories.business_user_repository import get_business_user_by_email
from helpers.dependencies import get_current_user
from models.business_user import BusinessUser

router = APIRouter()
templates = Jinja2Templates(directory="templates")

LOGIN_ERROR_COOKIE = "login_error"
LOGIN_SUCCESS_COOKIE = "login_success"
CHANGE_PASSWORD_ERROR_COOKIE = "change_password_error"
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