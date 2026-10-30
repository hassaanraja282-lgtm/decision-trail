"""Atlassian browser automation for the demo video. Modes: reset-request, set-password <url>, login-check."""
import os, sys, time, json, re, urllib.request
from playwright.sync_api import sync_playwright

EMAIL = os.environ["FORGE_EMAIL"]
import hashlib
def _derive():
    h = hashlib.sha256(("decision-trail-demo:" + os.environ.get("FORGE_API_TOKEN", "")).encode()).hexdigest()
    return "Dt!" + h[:6].upper() + h[6:13] + "9"
PW = os.environ.get("ATLASSIAN_PASSWORD") or _derive()
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
    for _ in range(3):
        if p.locator("text=Continue without two-step verification").count():
            p.get_by_text("Continue without two-step verification").first.click(); p.wait_for_timeout(8000)

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
        elif mode == "explore":
            login(p)
            p.goto("https://hassaanraja282.atlassian.net/browse/PAY-1", wait_until="domcontentloaded")
            p.wait_for_timeout(12000); shot(p, "pay1")
            btns = p.eval_on_selector_all("button, [role=button]", "els => els.map(e => (e.getAttribute('aria-label')||'') + ' | ' + (e.innerText||'').slice(0,40) + ' | ' + (e.getAttribute('data-testid')||''))")
            print("BUTTONS"); print("\n".join(b for b in btns if b.strip(' |')))
            for lab in ["Apps", "Decision Trail"]:
                try:
                    p.get_by_role("button", name=lab).first.click(timeout=4000); p.wait_for_timeout(3000); shot(p, "click-" + lab)
                    print("MENU", lab, p.inner_text("body")[:1500])
                except Exception as e: print("noclick", lab, e)
            ctx.storage_state(path="/tmp/state.json")
        elif mode == "billing":
            login(p)
            for u in ["https://admin.atlassian.com/", "https://admin.atlassian.com/billing", "https://admin.atlassian.com/billing/subscriptions"]:
                p.goto(u, wait_until="domcontentloaded"); p.wait_for_timeout(12000); shot(p, "billing")
                print("URL", p.url); print(p.inner_text("body")[:3000]); print("=====")
            links = p.eval_on_selector_all("a", "els => els.map(e => (e.innerText||'').slice(0,60) + ' -> ' + e.href)")
            print("LINKS"); print("\n".join(l for l in links if 'billing' in l or 'subscription' in l.lower()))
        elif mode == "billing2":
            login(p)
            p.goto("https://admin.atlassian.com/billing", wait_until="domcontentloaded"); p.wait_for_timeout(12000)
            k = p.get_by_role("link", name="Manage").count() or p.get_by_text("Manage", exact=True).count()
            print("MANAGE COUNT", k)
            for i in range(k):
                p.goto("https://admin.atlassian.com/billing", wait_until="domcontentloaded"); p.wait_for_timeout(10000)
                loc = p.get_by_role("link", name="Manage")
                if not loc.count(): loc = p.get_by_text("Manage", exact=True)
                loc.nth(i).click(); p.wait_for_timeout(12000); shot(p, f"acct{i}")
                print("ACCT", i, p.url); print(p.inner_text("body")[:2500]); print("=====")
                for lab in ["Subscriptions", "Manage subscriptions"]:
                    try:
                        p.get_by_text(lab, exact=True).first.click(timeout=4000); p.wait_for_timeout(10000); shot(p, f"subs{i}")
                        print("SUBS", i, p.url); print(p.inner_text("body")[:3500]); print("=====")
                        break
                    except Exception as e: print("nosubs", lab)
        elif mode == "login-check":
            login(p)
            p.goto("https://hassaanraja282.atlassian.net/browse/PAY-1", wait_until="domcontentloaded")
            p.wait_for_timeout(10000); shot(p, "pay1")
            ctx.storage_state(path="/tmp/state.json")
            print(p.inner_text("body")[:1500])
    except Exception as e:
        print("ERR", e); shot(p, "error"); print(p.inner_text("body")[:800])
    b.close()
