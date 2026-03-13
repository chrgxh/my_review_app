from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse(
        "admin.html",
        {"request": request}
    )

@app.get("/preview-email", response_class=HTMLResponse)
async def preview_email(
    request: Request,
    recipientEmail: str = "",
    identifier: str = "",
    message: str = "",
):
    return templates.TemplateResponse(
        "feedback_email.html",
        {
            "request": request,
            "recipient_email": recipientEmail,
            "identifier": identifier,
            "message": message,
        }
    )