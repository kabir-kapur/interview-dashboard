import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import DB, daily, initialize
from app.services.digest_delivery import claim_delivery, mark_failed, mark_sent
from app.services.sms import build_daily_digest, send_sms


def main() -> None:
    parser = argparse.ArgumentParser(description="Send today's interview-prep SMS digest.")
    parser.add_argument("--dashboard-url", required=True)
    parser.add_argument("--send", action="store_true", help="Send the message instead of printing it.")
    args = parser.parse_args()
    initialize()
    message = build_daily_digest(daily(), args.dashboard_url)
    if not args.send:
        print(message)
        return
    channel = "sms_daily_digest"
    attempted_at = datetime.now(timezone.utc).isoformat()
    if not claim_delivery(DB, plan["date"], channel, attempted_at):
        print("Digest already sent or currently being sent.")
        return
    try:
        message_id = send_sms(message)
    except Exception as error:
        mark_failed(DB, plan["date"], channel, str(error))
        raise
    mark_sent(DB, plan["date"], channel, message_id, datetime.now(timezone.utc).isoformat())
    print(f"Sent SMS {message_id}")


if __name__ == "__main__":
    main()
