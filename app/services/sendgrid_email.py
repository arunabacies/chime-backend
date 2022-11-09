from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from config import Config


def send_email(**kwargs):
    try:
        message = Mail(from_email=Config.SENDGRID_EMAIL_ADDRESS, to_emails=kwargs.get("to_email"),
                       subject=kwargs.get("subject"), html_content=kwargs.get("html_content"))
        sg = SendGridAPIClient(Config.SENDGRID_API_KEY)
        return sg.send(message)
    except Exception as e:
        print(str(e))
        # from app.services.custom_errors import UnProcessable
        return False
        # raise UnProcessable(str(e))
