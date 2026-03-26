from jinja2 import Environment, FileSystemLoader, select_autoescape

jinja_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"])
)


def render_feedback_email_html(
    recipient_email: str,
    identifier: str,
    message: str,
    default_email_text: str | None,
    feedback_url: str,
    token: str,
    business_name: str | None,
    logo_url: str | None,
) -> str:

    template = jinja_env.get_template("feedback_email.html")

    html = template.render(
        recipient_email=recipient_email,
        identifier=identifier,
        message=message,
        default_email_text=default_email_text,
        feedback_url=feedback_url,
        token=token,
        business_name=business_name,
        logo_url=logo_url,
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