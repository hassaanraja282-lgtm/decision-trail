"""Developer console automation (distribution / sharing). Reuses the encrypted CI session."""
import os, sys, json, time, re, hashlib, subprocess, urllib.request
from playwright.sync_api import sync_playwright
EMAIL = os.environ["FORGE_EMAIL"]; TOKEN = os.environ["FORGE_API_TOKEN"]
h = hashlib.sha256(("decision-trail-demo:" + TOKEN).encode()).hexdigest(); PW = "Dt!" + h[:6].upper() + h[6:13] + "9"
APP = "e812f02b-836c-4c5c-a3f0-18fa8b21f9d0"
OUT = "out"; os.makedirs(f"{OUT}/frames", exist_ok=True)
n = [0]
def shot(p, name):
    n[0] += 1; p.screenshot(path=f"{OUT}/frames/{n[0]:02d}-{name}.png", full_page=True); print("SHOT", name, p.url, flush=True)
def gh_code(after_ts):
    repo = os.environ["GITHUB_REPOSITORY"]; tok = os.environ["GH_TOKEN"]
    for _ in range(45):
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues/1/comments?per_page=100", headers={"Authorization": f"Bearer {tok}"})
        for c in reversed(json.load(urllib.request.urlopen(req))):
            m = re.search(r"CODE:\s*([A-Za-z0-9-]+)", c["body"])
            if m and c["created_at"] > after_ts: return m.group(1)
        time.sleep(8)
    raise SystemExit("no code")
def ensure_login(p):
    if "id.atlassian.com" not in p.url and "login" not in p.url: return
    p.goto("https://id.atlassian.com/login", wait_until="domcontentloaded"); p.wait_for_timeout(3000)
    p.fill("input[name=username], #username", EMAIL); p.keyboard.press("Enter")
    p.wait_for_selector("input[type=password]", timeout=30000); p.fill("input[type=password]", PW); p.keyboard.press("Enter")
    p.wait_for_timeout(9000)
    if p.locator("text=Continue without two-step verification").count():
        p.get_by_text("Continue without two-step verification").first.click(); p.wait_for_timeout(8000)
    if "mfa" in p.url:
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 90)); print("NEED_CODE", flush=True)
        p.keyboard.type(gh_code(ts)); p.keyboard.press("Enter"); p.wait_for_timeout(9000)
        if p.locator("text=Continue without two-step verification").count():
            p.get_by_text("Continue without two-step verification").first.click(); p.wait_for_timeout(8000)
def dump(p):
    print("TEXT", p.inner_text("body")[:3000], flush=True)
    els = p.eval_on_selector_all("button, a, input, textarea, [role=radio], [role=checkbox], select", "els => els.map(e => e.tagName + ' | ' + (e.getAttribute('aria-label')||'') + ' | ' + (e.innerText||e.value||'').slice(0,50).replace(/\\n/g,' ') + ' | ' + (e.getAttribute('name')||e.getAttribute('data-testid')||'') + ' | ' + (e.getAttribute('href')||''))")
    print("ELEMS"); print("\n".join(els[:200]), flush=True)

mode = sys.argv[1]
KEYF = hashlib.sha256(("state-key:" + TOKEN).encode()).hexdigest()
ENC = os.path.expanduser("~/.cache/atl/state.enc"); os.makedirs(os.path.dirname(ENC), exist_ok=True)
have = os.path.exists(ENC) and subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", "pass:" + KEYF, "-in", ENC, "-out", "/tmp/state.json"]).returncode == 0
with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="en-US", **({"storage_state": "/tmp/state.json"} if have else {}))
    p = ctx.new_page()
    url = f"https://developer.atlassian.com/console/myapps/{APP}/distribution"
    p.goto(url, wait_until="domcontentloaded"); p.wait_for_timeout(8000)
    if "login" in p.url or "id.atlassian.com" in p.url:
        ensure_login(p); p.goto(url, wait_until="domcontentloaded"); p.wait_for_timeout(8000)
    try:
        shot(p, "distribution"); dump(p)
        if mode == "share":
            exec(open("demo/share_steps.py").read())
    except Exception as e:
        print("ERR", e); shot(p, "error")
    ctx.storage_state(path="/tmp/state.json")
    subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-pass", "pass:" + KEYF, "-in", "/tmp/state.json", "-out", ENC], check=True)
    b.close()
