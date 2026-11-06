"""
Lumbini EDL Slot Checker - Runner for GitHub Actions
"""

import os
import sys
import json
import ssl
import logging
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_WEB_URL = "https://edlvrs.lumbini.gov.np"
BASE_API_URL = "https://edl-public-api.lumbini.gov.np/api/v1/web"

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def get_headers(token: Optional[str] = None, ref_uuid: str = "") -> Dict[str, str]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Origin': BASE_WEB_URL,
        'Referer': f"{BASE_WEB_URL}/edl/{ref_uuid}",
    }
    if token:
        headers['Authorization'] = f"Bearer {token}"
    return headers


def resume_session(initial_uuid: str) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
    resume_url = f"{BASE_API_URL}/applications/{initial_uuid}/resume"
    try:
        req = urllib.request.Request(resume_url, headers=get_headers(ref_uuid=initial_uuid))
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            token = data.get("access_token")

        if not token:
            logging.error("Failed to retrieve access token.")
            return None, None, {}

        # Query existing active application
        active_uuid = initial_uuid
        try:
            exists_url = f"{BASE_API_URL}/applicant/application/exists"
            req = urllib.request.Request(exists_url, headers=get_headers(token=token, ref_uuid=initial_uuid))
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
                exists_data = json.loads(resp.read().decode('utf-8')).get("data", {})
                if exists_data.get("exists") and exists_data.get("application_uuid"):
                    active_uuid = exists_data.get("application_uuid")
        except Exception as e:
            logging.warning(f"Could not check application/exists: {e}")

        # Fetch active application details
        app_details = {}
        try:
            app_url = f"{BASE_API_URL}/applicant/get-application?type=1&application_uuid={active_uuid}"
            req = urllib.request.Request(app_url, headers=get_headers(token=token, ref_uuid=initial_uuid))
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
                app_res = json.loads(resp.read().decode('utf-8'))
                data_node = app_res.get("data", {})
                if isinstance(data_node, dict):
                    app_details = data_node.get("data") or data_node
        except Exception as e:
            logging.warning(f"Could not fetch application details: {e}")

        return token, active_uuid, app_details
    except Exception as e:
        logging.error(f"Error resuming session: {e}")
        return None, None, {}


def check_date_availability(token: str, active_uuid: str, test_type: str = "TRIAL", days_ahead: int = 30) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    today = datetime.now()
    from_date = today.strftime("%Y-%m-%d")
    to_date = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    avail_url = f"{BASE_API_URL}/applicant/application/date-availability?type={test_type}&from={from_date}&to={to_date}&application_uuid={active_uuid}"

    try:
        req = urllib.request.Request(avail_url, headers=get_headers(token=token, ref_uuid=active_uuid))
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            days = data.get("data", [])

            available_dates = []
            for day in days:
                is_avail = day.get("is_bookable", False) or (day.get("available", 0) > 0) or (day.get("total", 0) > day.get("booked", 0) and day.get("total", 0) > 0)
                if is_avail:
                    available_dates.append(day)

            return days, available_dates
    except Exception as e:
        logging.error(f"Error querying date availability: {e}")
        return [], []


def send_telegram_alert(bot_token: str, chat_id: str, message: str) -> bool:
    if not bot_token or not chat_id:
        logging.warning("Telegram Bot Token or Chat ID not provided.")
        return False
    try:
        url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
        payload = json.dumps({
            "chat_id": chat_id.strip(),
            "text": message,
            "parse_mode": "HTML"
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception as e:
        logging.error(f"Failed to send Telegram message: {e}")
        return False


def main():
    initial_uuid = os.environ.get("EDL_UUID", "92a75ad3-4a1a-4ae3-8f10-5435eac485e4").strip()
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    test_type = os.environ.get("TEST_TYPE", "TRIAL").strip().upper()
    days_ahead = int(os.environ.get("DAYS_AHEAD", "30"))
    notify_on_empty = os.environ.get("NOTIFY_ON_EMPTY", "false").strip().lower() in ("true", "1", "yes")

    logging.info(f"Checking slots for UUID: {initial_uuid} | Type: {test_type} | Scanning: {days_ahead} days")

    token, active_uuid, app_details = resume_session(initial_uuid)
    if not token or not active_uuid:
        logging.error("Failed to authenticate session with government portal.")
        sys.exit(1)

    app_id = app_details.get("application_id", "N/A")
    office = app_details.get("office", {}).get("name", "TMO Lumbini")
    cat = app_details.get("license_category", {}).get("name", "Category A")
    logging.info(f"Target: App ID={app_id} | Office={office} | Category={cat}")

    all_days, available_days = check_date_availability(token, active_uuid, test_type=test_type, days_ahead=days_ahead)
    logging.info(f"Total dates scanned: {len(all_days)}")

    booking_url = f"{BASE_WEB_URL}/edl/{active_uuid}"

    if available_days:
        logging.info(f"🚨 SLOT AVAILABLE! Found {len(available_days)} dates with open quota:")
        for d in available_days:
            logging.info(f"  -> Date: {d.get('date')} | Available: {d.get('available', 0)} / {d.get('total', 0)}")

        dates_text = "\n".join([
            f"• <b>{d['date']}</b>: {d.get('available', 0)} slots available (Total: {d.get('total', 0)})"
            for d in available_days
        ])

        tg_message = (
            f"🚨 <b>LUMBINI DRIVING TEST SLOT AVAILABLE!</b>\n\n"
            f"<b>Application ID:</b> {app_id}\n"
            f"<b>Category:</b> {cat}\n"
            f"<b>Office:</b> {office}\n\n"
            f"<b>Dates Available:</b>\n{dates_text}\n\n"
            f"👉 <a href='{booking_url}'>Click here to book immediately</a>"
        )

        if tg_token and tg_chat:
            sent = send_telegram_alert(tg_token, tg_chat, tg_message)
            if sent:
                logging.info("Telegram notification delivered successfully.")
            else:
                logging.error("Failed to send Telegram notification.")
        else:
            logging.warning("Telegram secrets not configured. Notification skipped.")
    else:
        logging.info("Result: 0 slots currently available across the next 30 days.")
        if notify_on_empty and tg_token and tg_chat:
            sent = send_telegram_alert(tg_token, tg_chat, "✅ No slots available in the next 30 days. Keep checking!")
            if sent:
                logging.info("Status heartbeat notification sent to Telegram.")
            else:
                logging.error("Failed to send status Telegram notification.")


if __name__ == "__main__":
    main()
