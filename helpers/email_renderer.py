from jinja2 import Environment, FileSystemLoader, select_autoescape

jinja_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"])
)


def render_feedback_email_html(
    recipient_email: str,
    identifier: str,
    message: str,
    feedback_url: str
) -> str:

    template = jinja_env.get_template("feedback_email.html")

    html = template.render(
        recipient_email=recipient_email,
        identifier=identifier,
        message=message,
        feedback_url=feedback_url
    )

    return html