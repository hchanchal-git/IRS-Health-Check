# Created By Himanshu Kumar (Cloud Ops)
#!/usr/bin/env python3
"""
IRS Daily Health Check - cross-platform Python script.

- Opens an email-draft HTML file in the default browser (new window),
  then opens every URL from URLS as tabs in that same browser window.
- Works on Windows and macOS (also Linux via webbrowser).
- Checks each URL using requests (if available) or urllib, with realistic
  browser headers, retries, and an SSL fallback (verify=False).
- Shows results in a Tkinter GUI (or print to console with --no-gui).
"""

from __future__ import annotations

import argparse
import datetime
import os
import platform
import socket
import subprocess
import tempfile
import time
import webbrowser
from pathlib import Path
from typing import List, Tuple

# GUI
try:
    import tkinter as tk
    from tkinter import ttk
except Exception:
    tk = None

# HTTP libraries
try:
    import requests
    from requests.exceptions import ConnectionError as RequestsConnectionError
    from requests.exceptions import RequestException, SSLError, Timeout
    from urllib3.exceptions import InsecureRequestWarning

    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    HAVE_REQUESTS = True
except Exception:
    import urllib.error as urllib_error  # noqa: F401
    import urllib.request as urllib_request

    HAVE_REQUESTS = False
    RequestsConnectionError = OSError  # type: ignore[misc, assignment]
    RequestException = OSError  # type: ignore[misc, assignment]
    SSLError = OSError  # type: ignore[misc, assignment]
    Timeout = OSError  # type: ignore[misc, assignment]

# --------------------------- Configuration ----------------------------------
CASE_ID = "3805724"

TO_EMAILS = [
    "Vaishali.P.Narkhede@irs.gov","roshan.m.patel@irs.gov", "Donald.W.Russell@irs.gov","Christopher.S.Fuller@irs.gov",
    "jb551t@att.com", "Michael.A.Harrison@irs.gov", "George.B.Lenoir@irs.gov",
    "Erik.C.Schlenker@irs.gov", "Darren.E.Jackson@irs.gov",
    "Jeronima.G.Gomez@irs.gov", "Wayne.M.Garrido@irs.gov",
    "Melissa.Shuman@irs.gov", "Kartez.I.Harris@irs.gov",
    "Anthony.G.Clark@irs.gov", "Amit.R.Mohite@irs.gov", "sankar.b.mandalika@irs.gov",
    "Wenjun.du@irs.gov", "Lashelle.lewis@irs.gov", "Jasmine.A.Lee@irs.gov",
    "Jennifer.L.Nunley@irs.gov", "Robin.S.Ferguson2@irs.gov",
]

CC_EMAILS = [
    "pgawande@eGain.com", "PBoyle@egain.com","dnewell@egain.com", "AGupta@eGain.com",
    "achan@eGain.com", "BUfoegbune@egain.com", "support@eGain.com",
    "radhav@eGain.com", "JKinderman@egain.com",
    "eGainCloudNotifications@egain.com","cbu-tsops@egain.com"]

# Put your full list of IRS URLs here — every entry opens as a tab with the draft
URLS = [
    "https://sa.www4.irs.gov/idp/startSSO.ping?PartnerSpId=IRS-eGain-IDP&TargetResource=https%3A%2F%2Fconnect.irs.gov%2Fsystem%2Ftemplates%2Fmessagecenter%2Firssecure%2Fen-US%2FIRS%3Fpoa%3Dyes%26lp%3Dhttps%3A%2F%2Fsa.www4.irs.gov%2Fsso%2Fprotected%2Flogout",
    "https://connect.irs.gov/system/templates/messagecenter/irscorp/en-US/LBIEXAM",
    "https://connect.irs.gov/system/templates/messagecenter/irsaca/en-US/LBI",
    "https://connect.irs.gov/acalogin/irs_teb",
    "https://connect.irs.gov/system/templates/chat/irs_us/index.html?entryPointId=1004&templateName=irs_us&ver=v11&locale=en-US&eglvrefname=VBD009&referer=",
    "https://connect.irs.gov/system/templates/chat/irs_us/index.html?entryPointId=1003&templateName=irs_us&ver=v11&locale=es-ES&eglvrefname=VBD009&referer=",
    "https://www.irs.gov/payments",
    "https://www.irs.gov/es/payments",
    "https://www.irs.gov/refunds",
    "https://www.irs.gov/es/refunds",
    "https://www.irs.gov/cp2000",
    "https://www.irs.gov/cp2501",
    "https://www.irs.gov/cp3219A",
    "https://www.irs.gov/individuals/understanding-your-566-t-letter",
    "https://www.jobs.irs.gov/careers",
    "https://sa.www4.irs.gov/ola/",
    "https://sa.www4.irs.gov/ola/es/",
    "https://connect.irs.gov/system/web/custom/vascripts/erc_launch_va.html",
    "https://connect.irs.gov/system/web/custom/vascripts/erc_travel_launch_va.html",
    "https://connect.irs.gov/system/templates/chat/sbse_nlp_va2/index.html?entryPointId=1001&locale=en-US&postChatAttributes=false&templateName=sbse_nlp_va2&ver=v11&VAEnabled=true&vaChatEntryPointId=&vaChatServerURL=&VATenantAccId=TMPROD10067889&VATenantToken=TMPROD10067889&VAName=sbseenprod&ShowPreChatOnEscalation=&serverURL=https://connect.irs.gov/system&vaLastAvatar=&providerId=186A7&wsname=https://www.irs.gov&EGAIN_AV_CHAT_STATE_DATA=null&parentLost=false&referer=https%3A%2F%2Fwww.irs.gov%2Fpayments&useCustomButton=false&storage=true&docked=true",
    "https://connect.irs.gov/system/templates/chat/sbse_nlp_va2_spanish/index.html?entryPointId=1001&locale=es-ES&postChatAttributes=false&templateName=sbse_nlp_va2_spanish&ver=v11&VAEnabled=true&vaChatEntryPointId=&vaChatServerURL=&VATenantAccId=TMPROD10067889&VATenantToken=TMPROD10067889&VAName=sbseesprod&ShowPreChatOnEscalation=&serverURL=https://connect.irs.gov/system&vaLastAvatar=&providerId=186A7&wsname=https://www.irs.gov&EGAIN_AV_CHAT_STATE_DATA=null&parentLost=false&referer=https%3A%2F%2Fwww.irs.gov%2Fes%2Fpayments&useCustomButton=false&storage=true&docked=true",
    "https://connect.irs.gov/system/templates/chat/wni_va_rel1_ie/index.html?entryPointId=1001&locale=en-US&postChatAttributes=false&templateName=wni_va_rel1_ie&ver=v11&VAEnabled=true&vaChatEntryPointId=&vaChatServerURL=&VATenantAccId=TMPROD10067889&VATenantToken=TMPROD10067889&VAName=wnienprod&ShowPreChatOnEscalation=&serverURL=https://connect.irs.gov/system&vaLastAvatar=&providerId=186A7&wsname=https://www.irs.gov&EGAIN_AV_CHAT_STATE_DATA=null&parentLost=false&referer=https%3A%2F%2Fwww.irs.gov%2Frefunds&useCustomButton=false&storage=true&docked=true",
    "https://connect.irs.gov/system/templates/chat/wni_va_rel1_spanish_ie/index.html?entryPointId=1001&locale=es-ES&postChatAttributes=false&templateName=wni_va_rel1_spanish_ie&ver=v11&VAEnabled=true&vaChatEntryPointId=&vaChatServerURL=&VATenantAccId=TMPROD10067889&VATenantToken=TMPROD10067889&VAName=wniesprod&ShowPreChatOnEscalation=&serverURL=https://connect.irs.gov/system&vaLastAvatar=&providerId=186A7&wsname=https://www.irs.gov&EGAIN_AV_CHAT_STATE_DATA=null&parentLost=false&referer=https%3A%2F%2Fwww.irs.gov%2Fes%2Frefunds&useCustomButton=false&storage=true&docked=true",
    "https://connect.irs.gov/system/templates/chat/aur_nlp_va_en/index.html?entryPointId=1001&locale=en-US&postChatAttributes=false&templateName=aur_nlp_va_en&ver=v11&VAEnabled=true&vaChatEntryPointId=&vaChatServerURL=&VATenantAccId=TMPROD10067889&VATenantToken=TMPROD10067889&VAName=wniesprod&ShowPreChatOnEscalation=&serverURL=https://connect.irs.gov/system&vaLastAvatar=https://va.connect.irs.gov/assistantIMG/Zoe/Emotions/neutral2.gif&providerId=186A7&wsname=https://www.irs.gov&egChatWindowState=false&VASessionId=6361c244-cbfe-43c0-9438-9227dcf03f80&VAActive=true&VAEscalated=null&EGAIN_AV_CHAT_STATE_DATA=null&parentLost=false&referer=https%3A%2F%2Fwww.irs.gov%2Findividuals%2Funderstanding-your-cp3219a-notice%3Futm_source%3DOTC%26utm_medium%3DMail%26utm_term%3Dcp3219a%26utm_campaign%3DNotices&useCustomButton=false&storage=true&docked=true",
    "https://connect.irs.gov/system/templates/chat/sbse_campus_exam/index.html?entryPointId=1001&locale=en-US&postChatAttributes=false&templateName=sbse_campus_exam&ver=v11&VAEnabled=true&vaChatEntryPointId=&vaChatServerURL=&VATenantAccId=TMPROD10067889&VATenantToken=TMPROD10067889&VAName=sbsecampusexamenprod&ShowPreChatOnEscalation=&serverURL=https://connect.irs.gov/system&vaLastAvatar=&providerId=186A7&wsname=https://www.irs.gov&EGAIN_AV_CHAT_STATE_DATA=null&parentLost=false&referer=https%3A%2F%2Fwww.irs.gov%2Findividuals%2Funderstanding-your-566-t-letter&useCustomButton=false&storage=true&docked=true",
    "https://connect.irs.gov/system/templates/chat/irsjobsva/index.html?entryPointId=1001&locale=en-US&postChatAttributes=false&templateName=irsjobsva&ver=v11&VAEnabled=true&vaChatEntryPointId=&vaChatServerURL=&VATenantAccId=TMPROD10067889&VATenantToken=TMPROD10067889&VAName=jobsenprod&ShowPreChatOnEscalation=&serverURL=https://connect.irs.gov/system&vaLastAvatar=&providerId=186A7&wsname=https://www.jobs.irs.gov&EGAIN_AV_CHAT_STATE_DATA=null&parentLost=false&referer=https%3A%2F%2Fwww.jobs.irs.gov%2Fcareers&useCustomButton=false&storage=true&docked=true",
    "https://connect.irs.gov/system/templates/chat/ola_va/index.html?entryPointId=1001&locale=en-US&postChatAttributes=false&templateName=ola_va&ver=v11&VAEnabled=true&vaChatEntryPointId=&vaChatServerURL=&VATenantAccId=TMPROD10067889&VATenantToken=TMPROD10067889&VAName=olaenprod&ShowPreChatOnEscalation=&serverURL=https://connect.irs.gov/system&vaLastAvatar=https://va.connect.its.gov/assistantIMG/Zoe/Emotions/neutral2.gif&providerId=186A7&wsname=https://sa.www4.irs.gov&EGAINAVCHATSTATEDATA=nul1&parentLost=false&referer=https%3A$2F$2Fsa.www4.irs.gov%2Fola$2Fpaymentoptions&useCustomButton=false&storage=true&docked=true",
    "https://connect.irs.gov/system/templates/chat/irs_intl/index.html?entryPointId=1111&templateName=irs_intl&languageCode=en&countryCode=US&ver=v11&postChatAttributes=false",
    "https://connect.irs.gov/system/templates/chat/ola_va_spanish/index.html?entryPointId=1001&locale=es-ES&postChatAttributes=false&templateName=ola_va_spanish&ver=v11&VAEnabled=true&vaChatEntryPointId=&vaChatServerURL=&VATenantAccId=TMPROD10067889&VATenantToken=TMPROD10067889&VAName=olaesprod&ShowPreChatOnEscalation=&serverURL=https://connect.irs.gov/system&vaLastAvatar=&providerId=186A7&wsname=https://sa.www4.irs.gov&EGAINAVCHATSTATEDATA=null&parentLost=false&referer=https%3A$2F$2Fsa.www4.irs.gov%2Fola%2Fes%2F&useCustomButton=false&storage=true&docked=true",
    "https://groundwork8.egain.cloud/status?link=best&hostName=connect.irs.gov",
]

# --------------------------- Helpers ----------------------------------------
def get_date_with_ordinal(dt: datetime.datetime) -> str:
    day = dt.day
    if 11 <= day <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return dt.strftime(f"%B {day}{suffix}, %Y")


def _display_name(email: str) -> str:
    """Turn an email into a short Outlook-style display name."""
    local = email.split("@", 1)[0]
    if "." not in local and len(local) <= 12:
        return local.upper() if local.lower().startswith("jb") else local
    parts = [p for p in local.replace("_", ".").split(".") if p]
    if not parts:
        return email
    return " ".join(p.capitalize() for p in parts)


def _recipient_chips(emails: List[str], max_show: int = 4) -> str:
    shown = emails[:max_show]
    chips = "; ".join(_display_name(e) for e in shown)
    remaining = len(emails) - len(shown)

    if remaining > 0:
        chips += f'; <span class="more">+{remaining} others</span>'

    return chips


def build_email_html(
    subject: str,
    body: str,
    to: List[str],
    cc: List[str],
    bcc: List[str],
    sent_at=None,
) -> str:
    """Outlook-style email reading draft (matches the health-check email layout)."""
    sent_at = sent_at or datetime.datetime.now()
    stamp = sent_at.strftime("%a %Y-%m-%d %H:%M")
    attach_name = f"IRS Daily Health Check Report - {get_date_with_ordinal(sent_at)}.xlsx"
    to_line = _recipient_chips(to, 4)
    cc_line = _recipient_chips(cc, 3)
    bcc_line = _recipient_chips(bcc, 3) if bcc else ""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{subject}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: #f3f2f1;
    font-family: "Segoe UI", Calibri, Arial, sans-serif;
    color: #252423;
  }}
  .outlook {{
    max-width: 920px;
    margin: 24px auto;
    background: #fff;
    border: 1px solid #e1dfdd;
    box-shadow: 0 2px 8px rgba(0,0,0,.08);
  }}
  .subject-bar {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 20px 12px;
    border-bottom: 1px solid #edebe9;
  }}
  .irs-badge {{
    flex: 0 0 auto;
    width: 36px;
    height: 36px;
    border-radius: 4px;
    background: #ffcd00;
    color: #000;
    font-weight: 700;
    font-size: 13px;
    display: flex;
    align-items: center;
    justify-content: center;
    letter-spacing: 0.5px;
  }}
  .subject {{
    font-size: 20px;
    font-weight: 600;
    line-height: 1.3;
    margin: 0;
  }}
  .meta {{
    padding: 14px 20px 10px;
    border-bottom: 1px solid #edebe9;
  }}
  .from-row {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    margin-bottom: 8px;
  }}
  .from {{
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .avatar {{
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: #6264a7;
    color: #fff;
    font-size: 12px;
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .from-name {{
    font-weight: 600;
    font-size: 15px;
  }}
  .timestamp {{
    color: #605e5c;
    font-size: 13px;
    white-space: nowrap;
  }}
  .field {{
    margin: 4px 0 0 46px;
    font-size: 13px;
    color: #605e5c;
    line-height: 1.45;
  }}
  .field b {{
    color: #323130;
    font-weight: 600;
    margin-right: 6px;
  }}
  .more {{ color: #0078d4; }}
  .attachment {{
    margin: 12px 20px 0 66px;
    display: inline-flex;
    align-items: center;
    gap: 10px;
    border: 1px solid #e1dfdd;
    border-radius: 4px;
    padding: 8px 12px;
    background: #faf9f8;
    max-width: 360px;
  }}
  .xlsx-icon {{
    width: 28px;
    height: 32px;
    background: #107c41;
    color: #fff;
    font-size: 10px;
    font-weight: 700;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding-bottom: 3px;
    border-radius: 2px;
  }}
  .attach-name {{
    font-size: 13px;
    color: #323130;
  }}
  .attach-size {{
    font-size: 12px;
    color: #605e5c;
  }}
  .body {{
    padding: 28px 20px 36px 66px;
    font-size: 15px;
    line-height: 1.55;
  }}
  .body p {{ margin: 0 0 14px; }}
  .reminder {{
    margin-top: 28px;
    padding: 12px 14px;
    background: #fff4ce;
    border-left: 4px solid #ffb900;
    font-size: 13px;
    color: #323130;
  }}
  .full-lists {{
    margin: 0 20px 24px;
    padding: 16px;
    background: #faf9f8;
    border: 1px solid #edebe9;
    border-radius: 4px;
    font-size: 13px;
  }}
  .full-lists h3 {{
    margin: 0 0 8px;
    font-size: 13px;
    color: #323130;
  }}
  .full-lists ul {{
    margin: 0 0 14px 18px;
    padding: 0;
  }}
  .full-lists li {{ margin: 2px 0; color: #605e5c; }}
</style>
</head>
<body>
  <div class="outlook">
    <div class="subject-bar">
      <div class="irs-badge">IRS</div>
      <h1 class="subject">{subject}</h1>
    </div>

    <div class="meta">
      <div class="from-row">
        <div class="from">
          <div class="avatar">EN</div>
          <div class="from-name">eGain Cloud Notifications</div>
        </div>
        <div class="timestamp">{stamp}</div>
      </div>
      <div class="field"><b>To:</b> {to_line}</div>
      <div class="field"><b>Cc:</b> {cc_line}</div>
      {f'<div class="field"><b>Bcc:</b> {bcc_line}</div>' if bcc_line else ''}

      <div class="attachment" title="Attach the Excel report before sending">
        <div class="xlsx-icon">XLS</div>
        <div>
          <div class="attach-name">{attach_name}</div>
          <div class="attach-size">Attach before send · ~20 KB</div>
        </div>
      </div>
    </div>

    <div class="body">
      {body}
      <div class="reminder">
        <b>Reminder:</b> Please attach the Daily Health Check Excel report before sending this email.
      </div>
    </div>

    <div class="full-lists">
      <h3>To (full list)</h3>
      <ul>
        {''.join(f'<li>{x}</li>' for x in to)}
      </ul>
      <h3>Cc (full list)</h3>
      <ul>
        {''.join(f'<li>{x}</li>' for x in cc)}
      </ul>
      <h3>Bcc (full list)</h3>
      <ul>
        {''.join(f'<li>{x}</li>' for x in bcc)}
      </ul>
    </div>
  </div>
</body>
</html>"""
    return html


def save_temp_html(content: str, filename: str = "IRS_EmailDraft.html") -> str:
    """
    Save draft next to this script (easy to find), and also under TEMP.
    Returns the primary path (script folder) used for opening in the browser.
    """
    script_dir = Path(__file__).resolve().parent
    primary = script_dir / filename
    with open(primary, "w", encoding="utf-8") as f:
        f.write(content)

    temp_path = Path(tempfile.gettempdir()) / filename
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass

    return str(primary)


def path_to_file_uri(path: str) -> str:
    """Cross-platform file:// URI (Windows + macOS)."""
    return Path(path).resolve().as_uri()


def find_windows_browser():
    """Prefer Edge/Chrome so local HTML is not handed to Internet Explorer."""
    candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def open_draft_and_urls(draft_path: str, urls: List[str]) -> None:
    """
    Open ONE new browser window where:
      - Tab 1 = email draft
      - Tab 2+ = every URL in URLS
    """
    draft_path = str(Path(draft_path).resolve())
    if not os.path.isfile(draft_path):
        print("ERROR: Draft file was not created:", draft_path)
        return

    draft_uri = path_to_file_uri(draft_path)
    system = platform.system()
    print("Opening draft as first tab:", draft_path)

    try:
        if system == "Windows":
            browser = find_windows_browser()
            if browser:
                print("Using browser:", browser)
                subprocess.Popen(
                    [browser, "--new-window", draft_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                time.sleep(1.8)
                batch_size = 4
                for i in range(0, len(urls), batch_size):
                    batch = urls[i : i + batch_size]
                    subprocess.Popen(
                        [browser] + batch,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    time.sleep(0.45)
                print(f"Opened draft (tab 1) + {len(urls)} link tab(s) in one window.")
                return

            print("Edge/Chrome not found; opening draft then links via start...")
            subprocess.Popen(
                ["cmd", "/c", "start", "", draft_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(1.5)
            for u in urls:
                subprocess.Popen(
                    ["cmd", "/c", "start", "", u],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                time.sleep(0.3)
            return

        if system == "Darwin":
            subprocess.Popen(
                ["open", "-n", draft_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(1.2)
            for u in urls:
                subprocess.Popen(
                    ["open", u],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                time.sleep(0.25)
            return

        webbrowser.open(draft_uri, new=1)
        time.sleep(1.0)
        for u in urls:
            webbrowser.open(u, new=2)
            time.sleep(0.25)
    except Exception as e:
        print("Failed to open browser:", e)
        try:
            if system == "Windows":
                os.startfile(draft_path)  # type: ignore[attr-defined]
            else:
                webbrowser.open(draft_uri)
        except Exception as e2:
            print("Could not open draft at all:", e2)
            print("Please open this file manually:", draft_path)


def open_urls_in_default_browser(urls: List[str]) -> None:
    """Backward-compatible helper: first item is draft URI/path, rest are links."""
    if not urls:
        return
    first, rest = urls[0], urls[1:]
    if first.startswith("file:"):
        try:
            from urllib.parse import urlparse, unquote

            parsed = urlparse(first)
            draft_path = unquote(parsed.path)
            if os.name == "nt" and draft_path.startswith("/"):
                draft_path = draft_path.lstrip("/")
        except Exception:
            draft_path = first
        open_draft_and_urls(str(draft_path), rest)
    else:
        open_draft_and_urls(first, rest)


def timestamp_now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# --------------------------- Improved URL checker ---------------------------
def test_url_status(url: str, timeout: float = 12.0, retry_delay: float = 2.0) -> str:
    ts = timestamp_now()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def ok(msg: str = "OK") -> str:
        return f"{ts} - {msg}"

    if HAVE_REQUESTS:
        sess = requests.Session()
        sess.headers.update(headers)
        try:
            r = sess.get(url, timeout=timeout, allow_redirects=True)
            code = r.status_code
            if 200 <= code < 300:
                return ok(f"OK ({code})")
            if 300 <= code < 400:
                return ok(f"Redirect ({code})")
            time.sleep(retry_delay)
            r2 = sess.get(url, timeout=timeout, allow_redirects=True)
            if 200 <= r2.status_code < 300:
                return ok(f"OK (Retry {r2.status_code})")
            return f"{ts} - NOT OK ({r2.status_code})"
        except SSLError as e:
            try:
                r = sess.get(url, timeout=timeout, allow_redirects=True, verify=False)
                if 200 <= r.status_code < 300:
                    return ok("OK (Insecure TLS - verify=False) - CERT/SSL verification issue detected")
                return f"{ts} - NOT OK (SSL -> {r.status_code})"
            except Exception:
                return f"{ts} - NOT OK (SSL Error: {e})"
        except (RequestsConnectionError, Timeout, RequestException, socket.error) as e:
            try:
                time.sleep(retry_delay)
                r = sess.get(url, timeout=timeout, allow_redirects=True)
                if 200 <= r.status_code < 300:
                    return ok(f"OK (Retry {r.status_code})")
                return f"{ts} - NOT OK ({r.status_code})"
            except Exception as e2:
                return f"{ts} - NOT OK ({e2})"

    try:
        req = urllib_request.Request(url, headers=headers)
        resp = urllib_request.urlopen(req, timeout=timeout)
        code = resp.getcode()
        if 200 <= code < 300:
            return ok(f"OK ({code})")
        time.sleep(retry_delay)
        resp2 = urllib_request.urlopen(req, timeout=timeout)
        if 200 <= resp2.getcode() < 300:
            return ok(f"OK (Retry {resp2.getcode()})")
        return f"{ts} - NOT OK ({resp2.getcode()})"
    except Exception:
        try:
            time.sleep(retry_delay)
            req = urllib_request.Request(url, headers=headers)
            resp = urllib_request.urlopen(req, timeout=timeout)
            if 200 <= resp.getcode() < 300:
                return ok("OK (Retry)")
            return f"{ts} - NOT OK ({resp.getcode()})"
        except Exception as e2:
            return f"{ts} - NOT OK ({e2})"


# --------------------------- GUI --------------------------------------------
class UrlStatusGUI:
    def __init__(self, master, results: List[Tuple[str, str]]):
        self.master = master
        master.title("IRS URL Health Check Status")
        master.geometry("1000x600")
        master.minsize(600, 300)

        self.tree = ttk.Treeview(master, columns=("url", "status"), show="headings")
        self.tree.heading("url", text="URL")
        self.tree.heading("status", text="Status with Timestamp")
        self.tree.column("url", width=700)
        self.tree.column("status", width=300)
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)

        self.tree.tag_configure("bad", foreground="red")
        self.tree.tag_configure("warn", foreground="darkorange")
        self.tree.tag_configure("good", foreground="green")

        for url, status in results:
            self._insert_row(url, status)

        btn_frame = tk.Frame(master)
        btn_frame.pack(fill="x", padx=6, pady=(0, 6))
        tk.Button(btn_frame, text="Refresh Check", command=self._refresh).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Close", command=master.quit).pack(side="right", padx=4)
        self._results = results

    def _tag_for(self, status: str) -> str:
        upper = status.upper()
        if "NOT OK" in upper:
            return "bad"
        if "INSECURE" in upper or "VERIFY=FALSE" in upper:
            return "warn"
        return "good"

    def _insert_row(self, url: str, status: str) -> None:
        iid = self.tree.insert("", "end", values=(url, status))
        self.tree.item(iid, tags=(self._tag_for(status),))

    def _refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        new_results = []
        for url, _ in self._results:
            status = test_url_status(url)
            new_results.append((url, status))
            self._insert_row(url, status)
        self._results = new_results


# --------------------------- Main flow -------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(
        description="IRS Daily Health Check - cross-platform Python script"
    )
    parser.add_argument(
        "--no-gui", action="store_true", help="Don't show GUI (prints results to console)"
    )
    parser.add_argument(
        "--skip-browser", action="store_true", help="Don't open browser tabs"
    )
    args = parser.parse_args(argv)

    now = datetime.datetime.now()
    date_str = get_date_with_ordinal(now)
    subject = f"IRS Daily Health Check Report - {date_str} [#{CASE_ID}]"
    body = (
        f"<p>Dear Customer,</p>"
        f"<p>Please find the attached Daily Health Check Report - {date_str}.</p>"
        f"<p>Regards,<br>eGain Corp</p>"
    )

    email_html = build_email_html(
        subject, body, TO_EMAILS, CC_EMAILS, BCC_EMAILS, sent_at=now
    )
    draft_path = save_temp_html(email_html)
    draft_uri = path_to_file_uri(draft_path)
    print("Email draft saved to:", draft_path)
    print("Draft URI:", draft_uri)

    if not args.skip_browser:
        print(
            f"Opening browser: draft first, then {len(URLS)} link(s) "
            f"in the same window ({platform.system()})..."
        )
        open_draft_and_urls(draft_path, list(URLS))
    else:
        print("Skipping browser opening as requested.")

    results = []
    print("Checking URLs...")
    for url in URLS:
        print("Checking", url)
        status = test_url_status(url)
        print(url, "->", status)
        results.append((url, status))

    if (not args.no_gui) and (tk is not None):
        root = tk.Tk()
        UrlStatusGUI(root, results)
        try:
            root.mainloop()
        except KeyboardInterrupt:
            print("Interrupted. Exiting.")
    else:
        print("\nURL Results:")
        for url, status in results:
            print(f"{url} -> {status}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Exiting.")
