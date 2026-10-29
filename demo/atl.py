"""Atlassian browser automation for the demo video. Modes: reset-request, set-password <url>, login-check."""
import os, sys, time, json, re, urllib.request
from playwright.sync_api import sync_playwright

EMAIL = os.environ["FORGE_EMAIL"]
PW = os.environ.get("ATLASSIAN_PASSWORD", "")
OUT = "out"; os.makedirs(OUT, exist_ok=True)
mode = sys.argv[1]
n = [0]
def shot(p, name):
    n[0] += 1; p.screenshot(path=f"{OUT}/{n[0]:02d}-{name}.png", full_page=False)
    print("SHOT", name, p.url, flush=True)

def gh_code(after_ts):
    """Poll issue #1 comments for 'CODE: 123456' posted after after_ts."""
    repo = os.environ["GITHUB_REPOSITORY"]; tok = os.environ["GH_TOKEN"]
    for _ in range(60):
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues/1/comments?per_page=100",
                                     headers={"Authorization": f"Bearer {tok}"})
        for c in reversed(json.load(urllib.request.urlopen(req))):
            m = re.search(r"CODE:\s*([A-Za-z0-9-]+)", c["body"])
            if m and c["created_at"] > after_ts: return m.group(1)
        time.sleep(10)
    raise SystemExit("no code")

def login(p):
    p.goto("https://id.atlassian.com/login", wait_until="domcontentloaded"); p.wait_for_timeout(3000)
    p.fill("input[name=username], #username", EMAIL); shot(p, "email")
    p.keyboard.press("Enter"); p.wait_for_timeout(4000); shot(p, "after-email")
    p.wait_for_selector("input[type=password]", timeout=20000)
    p.fill("input[type=password]", PW); p.keyboard.press("Enter")
    p.wait_for_timeout(8000); shot(p, "after-password")
    body = p.inner_text("body").lower()
    if "verification code" in body or "enter the code" in body or "we sent" in body:
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 60))
        print("NEED_CODE", flush=True)
        code = gh_code(ts)
        p.keyboard.type(code); p.keyboard.press("Enter"); p.wait_for_timeout(8000); shot(p, "after-code")

with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="en-US")
    p = ctx.new_page()
    try:
        if mode == "reset-request":
            p.goto("https://id.atlassian.com/login/resetpassword", wait_until="domcontentloaded"); p.wait_for_timeout(4000)
            shot(p, "reset-page")
            p.fill("input[name=username], #username, input[type=email]", EMAIL)
            p.keyboard.press("Enter"); p.wait_for_timeout(6000); shot(p, "reset-sent")
            print(p.inner_text("body")[:800])
        elif mode == "set-password":
            p.goto(os.environ["RESET_URL"], wait_until="domcontentloaded"); p.wait_for_timeout(6000); shot(p, "reset-link")
            fields = p.locator("input[type=password]")
            for i in range(fields.count()): fields.nth(i).fill(PW)
            shot(p, "filled"); p.keyboard.press("Enter"); p.wait_for_timeout(8000); shot(p, "after-set")
            print(p.inner_text("body")[:800])
        elif mode == "login-check":
            login(p)
            p.goto("https://hassaanraja282.atlassian.net/browse/PAY-1", wait_until="domcontentloaded")
            p.wait_for_timeout(10000); shot(p, "pay1")
            ctx.storage_state(path=f"{OUT}/state.json")
            print(p.inner_text("body")[:1500])
    except Exception as e:
        print("ERR", e); shot(p, "error"); print(p.inner_text("body")[:800])
    b.close()
