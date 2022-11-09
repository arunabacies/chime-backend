import re
from app.services.custom_errors import *


def email_validation(email: str) -> bool:
    # checks whether the email formats are in proper format or not
    match = re.search(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', email, re.I)
    try:
        match.group()
    except:
        raise BadRequest("Please give a valid email address.")
    return True