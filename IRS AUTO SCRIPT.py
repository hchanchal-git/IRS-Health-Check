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
    "Vaishali.P.Narkhede@irs.gov", "Moriah.D.Cardona@irs.gov", "Donald.W.Russell@irs.gov",
    "jb551t@att.com", "Michael.A.Harrison@irs.gov", "George.B.Lenoir@irs.gov",
    "Erik.C.Schlenker@irs.gov", "Darren.E.Jackson@irs.gov", "Geoffrey.T.Dang@irs.gov",
    "Venus.M.Hutson@irs.gov", "Jeronima.G.Gomez@irs.gov", "Wayne.M.Garrido@irs.gov",
    "Dionecio.Headley@irs.gov", "Melissa.Shuman@irs.gov", "Kartez.I.Harris@irs.gov",
    "Anthony.G.Clark@irs.gov", "Amit.R.Mohite@irs.gov", "sankar.b.mandalika@irs.gov",
    "Wenjun.du@irs.gov", "Lashelle.lewis@irs.gov", "Jasmine.A.Lee@irs.gov",
    "Jennifer.L.Nunley@irs.gov", "Robin.S.Ferguson2@irs.gov",
]

CC_EMAILS = [
    "VPadmanaban@eGain.com", "pgawande@eGain.com", "PBoyle@egain.com", "AGupta@eGain.com",
    "achan@eGain.com", "BUfoegbune@egain.com", "EKozlowski@egain.com", "support@eGain.com",
    "jmallory@egain.com", "radhav@eGain.com", "JKinderman@egain.com",
    "eGainCloudNotifications@egain.com",
]

BCC_EMAILS = ["cbu-tsops@egain.com"]

# Put your full list of IRS URLs here — every entry opens as a tab with the draft
URLS = [
    "https://www.irs.gov/payments",
    "https://www.irs.gov/es/payments",
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


def build_email_html(subject: str, body: str, to: List[str], cc: List[str], bcc: List[str]) -> str:
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{subject}</title>

<style>
body {{
    font-family: "Segoe UI", Arial, sans-serif;
    background:#f4f6f9;
    margin:0;
    padding:30px;
}}

.card {{
    max-width:1100px;
    margin:auto;
    background:white;
    border-radius:10px;
    padding:25px;
    box-shadow:0 4px 12px rgba(0,0,0,.15);
}}

h2 {{
    color:#0066cc;
    margin-top:0;
}}

.section {{
    margin-top:20px;
}}

.label {{
    font-weight:bold;
    color:#333;
    margin-bottom:6px;
}}

ul {{
    margin:6px 0 0 20px;
}}

.footer {{
    margin-top:25px;
    padding-top:15px;
    border-top:1px solid #ddd;
    color:#666;
}}
</style>

</head>

<body>

<div class="card">

<h2>IRS Daily Health Check Draft</h2>

<div class="section">
<div class="label">Subject</div>
{subject}
</div>

<div class="section">
<div class="label">Body</div>
{body}
</div>

<div class="section">
<div class="label">To</div>
<ul>
{''.join(f'<li>{x}</li>' for x in to)}
</ul>
</div>

<div class="section">
<div class="label">CC</div>
<ul>
{''.join(f'<li>{x}</li>' for x in cc)}
</ul>
</div>

<div class="section">
<div class="label">BCC</div>
<ul>
{''.join(f'<li>{x}</li>' for x in bcc)}
</ul>
</div>

<div class="footer">
<b>Reminder:</b> Please attach the Daily Health Check Excel report before sending the email.
</div>

</div>

</body>
</html>"""
    return html


def save_temp_html(content: str, filename: str = "IRS_EmailDraft.html") -> str:
    path = os.path.join(tempfile.gettempdir(), filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def path_to_file_uri(path: str) -> str:
    """Cross-platform file:// URI (Windows + macOS)."""
    return Path(path).resolve().as_uri()


def _open_url_os(url: str) -> None:
    """Open a URL with the OS default browser handler."""
    system = platform.system()
    if system == "Darwin":
        subprocess.Popen(["open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif system == "Windows":
        os.startfile(url)  # type: ignore[attr-defined]
    else:
        webbrowser.open(url)


def open_urls_in_default_browser(urls: List[str]) -> None:
    """
    Open the first URL in a NEW browser window, then open every remaining URL
    as a new tab in that same window (default browser on Windows / macOS).

    Add more links to the URLS list — they will all open together with the draft.
    """
    if not urls:
        return
    try:
        system = platform.system()
        if system == "Darwin":
            subprocess.Popen(
                ["open", "-n", urls[0]],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif system == "Windows":
            webbrowser.open(urls[0], new=1)  # new=1 -> new window
        else:
            webbrowser.open(urls[0], new=1)

        time.sleep(1.0)

        for u in urls[1:]:
            if system == "Darwin":
                subprocess.Popen(
                    ["open", u],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif system == "Windows":
                webbrowser.open(u, new=2)  # new=2 -> new tab
            else:
                webbrowser.open(u, new=2)
            time.sleep(0.35)
    except Exception as e:
        print("Failed to open browser tabs:", e)
        for u in urls:
            try:
                _open_url_os(u)
                time.sleep(0.3)
            except Exception as e2:
                print(f"  Could not open {u}: {e2}")


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
                return f"{ts} - NOT OK (SSL -> {r.status_code})")
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
        f"Dear Customer,<br><br>"
        f"Please find the attached Daily Health Check Report - {date_str}."
        f"<br><br>Regards,<br>eGain Corp"
    )

    email_html = build_email_html(subject, body, TO_EMAILS, CC_EMAILS, BCC_EMAILS)
    temp_html_path = save_temp_html(email_html)
    draft_uri = path_to_file_uri(temp_html_path)
    print("Email draft saved to:", temp_html_path)
    print("Draft URI:", draft_uri)

    all_tabs = [draft_uri] + list(URLS)

    if not args.skip_browser:
        print(
            f"Opening default browser: draft + {len(URLS)} link(s) "
            f"in one window ({platform.system()})..."
        )
        open_urls_in_default_browser(all_tabs)
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
