from jinja2 import Environment, FileSystemLoader, select_autoescape

jinja_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"])
)


def _is_modern_email_client(email: str) -> bool:
    """Check if email domain supports modern CSS."""
    domain = email.lower().split("@")[-1]
    modern_domains = {
        "gmail.com",
        # "googlemail.com",
        # "yahoo.com",
        # "aol.com",
    }
    return domain in modern_domains


def render_feedback_email_html(
    recipient_email: str,
    identifier: str,
    message: str,
    feedback_url: str,
    token: str,
    business_name: str | None = None,
    logo_url: str | None = None,
    default_email_text: str | None = None,
    email_header: str | None = None,
) -> str:
    # Choose template based on email client
    is_modern = _is_modern_email_client(recipient_email)
    template_name = "feedback_email.html" if is_modern else "safe_feedback_email.html"
    
    template = jinja_env.get_template(template_name)

    html = template.render(
        recipient_email=recipient_email,
        identifier=identifier,
        message=message,
        feedback_url=feedback_url,
        token=token,
        business_name=business_name,
        logo_url=logo_url,
        default_email_text=default_email_text,
        email_header=email_header,
    )

    return html


def render_admin_feedback_notification_html(
    identifier: str,
    recipient_email: str,
    rating: int,
    comment: str | None,
    responded_at: str,
) -> str:
    template = jinja_env.get_template("admin_feedback_notification.html")

    html = template.render(
        identifier=identifier,
        recipient_email=recipient_email,
        rating=rating,
        comment=comment,
        responded_at=responded_at,
    )

    return html


def render_password_reset_email_html(reset_link: str) -> str:
    template = jinja_env.get_template("password_reset_email.html")

    html = template.render(
        reset_link=reset_link,
    )

    return html