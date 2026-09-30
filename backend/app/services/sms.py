import base64
import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class SmsNotConfigured(RuntimeError):
    """Raised when the deployment has not supplied SMS credentials."""


def build_daily_digest(plan: dict, dashboard_url: str) -> str:
    """Create a concise, one-message summary for the daily problem plan."""
    problems = " · ".join(problem["title"] for problem in plan["problems"])
    return f"Interview prep: {problems}. Open your daily console: {dashboard_url}"


def send_sms(body: str) -> str:
    """Send one SMS through Twilio and return the provider message identifier."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    api_key = os.getenv("TWILIO_API_KEY")
    api_secret = os.getenv("TWILIO_API_SECRET")
    sender = os.getenv("TWILIO_FROM_NUMBER")
    recipient = os.getenv("SMS_TO_NUMBER")
    if not all([account_sid, api_key, api_secret, sender, recipient]):
        raise SmsNotConfigured("Set Twilio credentials and SMS phone numbers before sending.")
    token = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
    request = Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
        data=urlencode({"To": recipient, "From": sender, "Body": body}).encode(),
        headers={"Authorization": f"Basic {token}", "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read())["sid"]
