import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import DB, daily, initialize
from app.services.sms import build_daily_digest, send_sms


def main() -> None:
    parser = argparse.ArgumentParser(description="Send today's interview-prep SMS digest.")
    parser.add_argument("--dashboard-url", required=True)
    parser.add_argument("--send", action="store_true", help="Send the message instead of printing it.")
    args = parser.parse_args()
    initialize()
    plan = daily()
    message = build_daily_digest(plan, args.dashboard_url)
    if not args.send:
        print(message)
        return
    message_id = send_sms(message)
    print(f"Sent SMS {message_id}")


if __name__ == "__main__":
    main()
