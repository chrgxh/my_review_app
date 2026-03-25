from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel.ext.asyncio.session import AsyncSession

from helpers.db import get_session
from helpers.auth import COOKIE_MAX_AGE, COOKIE_NAME, create_session_token
from helpers.security import verify_password
from repositories.business_user_repository import get_business_user_by_email
from helpers.dependencies import get_current_user
from models.business_user import BusinessUser

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    error = None
    if request.cookies.get("login_error") == "1":
        error = "Invalid email or password."

    response = templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error},
    )

    response.delete_cookie("login_error")
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
            key="login_error",
            value="1",
            max_age=10,
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
            key="login_error",
            value="1",
            max_age=10,
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