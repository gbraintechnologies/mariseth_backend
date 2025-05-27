from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Content, Email, Mail, To


def sendgrid_send_email(
        sender: str,
        recipients: list[str],
        subject: str,
        body_text: str,
        body_html: str = None,
        attachments: list = None,
        bcc: list[str] = None,
        cc: list[str] = None
):
    message = Mail(
        from_email=Email(sender),
        to_emails=[To(email) for email in recipients],
        subject=subject,
        plain_text_content=Content("text/plain", body_text),
        html_content=Content("text/html", body_html) if body_html else None
    )

    if cc:
        message.cc = [Email(email) for email in cc]
    if bcc:
        message.bcc = [Email(email) for email in bcc]

    sg = SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
    return sg.send(message)
