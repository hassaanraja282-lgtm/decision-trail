"""Records the narrated Decision Trail demo in CI.
Env: FORGE_EMAIL, FORGE_API_TOKEN, GH_TOKEN, GITHUB_REPOSITORY. Output: out/demo.mp4 + out/frames/*.png
"""
import os, sys, json, time, re, hashlib, subprocess, base64, urllib.request
from playwright.sync_api import sync_playwright

EMAIL = os.environ["FORGE_EMAIL"]
TOKEN = os.environ["FORGE_API_TOKEN"]
h = hashlib.sha256(("decision-trail-demo:" + TOKEN).encode()).hexdigest()
PW = "Dt!" + h[:6].upper() + h[6:13] + "9"
SITE = "https://hassaanraja282.atlassian.net"
OUT = "out"; os.makedirs(f"{OUT}/frames", exist_ok=True); os.makedirs("/tmp/vid", exist_ok=True)
LINES = json.load(open("demo/narration.json"))
VOICE = "en-US-AndrewNeural"

# ---------- narration ----------
durs = []
for i, t in enumerate(LINES):
    subprocess.run(["edge-tts", "--voice", VOICE, "--rate", "+4%", "--text", t, "--write-media", f"/tmp/s{i}.mp3"], check=True)
    d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"/tmp/s{i}.mp3"]).decode())
    durs.append(d)
print("durations", durs, flush=True)

def gh_code(after_ts):
    repo = os.environ["GITHUB_REPOSITORY"]; tok = os.environ["GH_TOKEN"]
    for _ in range(90):
        req = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues/1/comments?per_page=100",
                                     headers={"Authorization": f"Bearer {tok}"})
        for c in reversed(json.load(urllib.request.urlopen(req))):
            m = re.search(r"CODE:\s*([A-Za-z0-9-]+)", c["body"])
            if m and c["created_at"] > after_ts: return m.group(1)
        time.sleep(8)
    raise SystemExit("no code")

def jira(method, path, body=None):
    auth = "Basic " + base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()
    req = urllib.request.Request(SITE + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": auth, "Content-Type": "application/json", "Accept": "application/json"})
    return urllib.request.urlopen(req).read()

nshot = [0]
def shot(p, name):
    nshot[0] += 1
    p.screenshot(path=f"{OUT}/frames/{nshot[0]:02d}-{name}.png")
    print("SHOT", name, flush=True)

def slide(p, title, sub, small=""):
    p.set_content(f"""<html><body style="margin:0;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;
    background:linear-gradient(135deg,#0c66e4,#1d2125);font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#fff;text-align:center">
    <div style="font-size:84px;font-weight:700;letter-spacing:-1px">{title}</div>
    <div style="font-size:32px;margin-top:22px;opacity:.9;max-width:1100px;line-height:1.4">{sub}</div>
    <div style="font-size:22px;margin-top:40px;opacity:.75;max-width:1150px;line-height:1.7">{small}</div></body></html>""")

def open_panel(p, key):
    p.goto(f"{SITE}/browse/{key}", wait_until="domcontentloaded")
    p.wait_for_selector("h1", timeout=60000); p.wait_for_timeout(5000)
    for s in ["#onetrust-accept-btn-handler", "button:has-text('Accept all')"]:
        try: p.click(s, timeout=1500)
        except Exception: pass
    if p.locator("text=Decisions on").count() == 0:
        try:
            p.click("[data-testid='issue-view-foundation.quick-add.quick-add-items-compact.apps-button-dropdown--trigger']", timeout=8000)
            p.wait_for_timeout(1200)
            p.get_by_text("Decision Trail", exact=True).last.click(timeout=8000)
        except Exception as e:
            print("panel open err", key, e, flush=True)
    p.wait_for_selector("text=Decisions on", timeout=45000)
    p.wait_for_timeout(2500)
    try: p.locator("text=Decisions on").first.scroll_into_view_if_needed(); p.mouse.wheel(0, 150)
    except Exception: pass
    p.wait_for_timeout(1500)

marks = []
T0 = [None]
def scene(i, fn, p):
    st = time.time(); marks.append(st - T0[0])
    try: fn(p)
    except Exception as e: print("scene", i, "err", repr(e)[:300], flush=True); shot(p, f"err{i}")
    rem = st + durs[i] + 0.7 - time.time()
    if rem > 0: p.wait_for_timeout(int(rem * 1000))
    else: print("scene", i, "overran by", -rem, flush=True)

def s0(p): slide(p, "Decision Trail", "Stop re-litigating decisions in Jira.", "Auto-captured decisions &middot; related context on every issue &middot; conflict warnings &middot; Rovo agent<br>Built on Atlassian Forge for Codegeist 2026")
def s1(p):
    open_panel(p, "PAY-1"); shot(p, "pay1")
def s2(p):
    open_panel(p, "PAY-5"); p.locator("text=Already decided elsewhere").first.scroll_into_view_if_needed(); p.wait_for_timeout(800); shot(p, "pay5")
def s3(p):
    ta = p.locator("textarea").last
    ta.scroll_into_view_if_needed(); ta.click(); p.keyboard.type("Use Mongo for the billing refund database", delay=45)
    p.get_by_role("button", name="Log decision").click()
    p.wait_for_selector("text=may contradict", timeout=30000); p.wait_for_timeout(600)
    p.locator("text=may contradict").first.scroll_into_view_if_needed(); p.wait_for_timeout(600); shot(p, "conflict")
def s4(p):
    open_panel(p, "PAY-6"); p.locator("text=Already decided elsewhere").first.scroll_into_view_if_needed(); p.wait_for_timeout(500); shot(p, "pay6")
def s5(p):
    adf = {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "DECISION: Merchant portal SSO goes through Okta, same as internal tools."}]}]}
    jira("POST", "/rest/api/3/issue/PAY-6/comment", {"body": adf})
    p.wait_for_timeout(7000)
    p.reload(wait_until="domcontentloaded"); p.wait_for_selector("h1", timeout=60000); p.wait_for_timeout(4000)
    open_panel(p, "PAY-6"); shot(p, "captured")
    try: p.locator("text=Merchant portal SSO goes through Okta").last.scroll_into_view_if_needed()
    except Exception: pass
def s6(p):
    p.goto(f"{SITE}/jira", wait_until="domcontentloaded"); p.wait_for_timeout(5000)
    opened = False
    for sel in ["[data-testid*='rovo-chat'] button", "button[aria-label*='Rovo']", "button:has-text('Ask Rovo')", "button[aria-label*='Chat']", "button:has-text('Rovo')"]:
        try: p.click(sel, timeout=2500); opened = True; break
        except Exception: pass
    p.wait_for_timeout(3000); shot(p, "rovo-open")
    if not opened: raise RuntimeError("no rovo button")
    try:
        p.get_by_text("Decision Keeper").first.click(timeout=4000)
    except Exception:
        for sel in ["text=Browse agents", "text=Agents", "text=View all agents"]:
            try: p.click(sel, timeout=2500); p.wait_for_timeout(1500); p.get_by_text("Decision Keeper").first.click(timeout=4000); break
            except Exception: pass
    p.wait_for_timeout(2000)
    box = p.locator("[contenteditable=true], textarea").last
    box.click(); p.keyboard.type("What did we decide about the billing database?", delay=35); p.keyboard.press("Enter")
    p.wait_for_timeout(14000); shot(p, "rovo-answer")
def s7(p): slide(p, "Decision Trail", "Built 100% on Forge.", "jira:issuePanel (UI Kit) &middot; avi:jira:commented:issue trigger &middot; rovo:agent + 2 actions &middot; Forge KVS storage<br>github.com/hassaanraja282-lgtm/decision-trail")

with sync_playwright() as pw:
    b = pw.chromium.launch(args=["--disable-blink-features=AutomationControlled"])
    ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    c1 = b.new_context(viewport={"width": 1440, "height": 900}, locale="en-US", user_agent=ua)
    p = c1.new_page()
    p.goto("https://id.atlassian.com/login", wait_until="domcontentloaded"); p.wait_for_timeout(3000)
    p.fill("input[name=username], #username", EMAIL); p.keyboard.press("Enter")
    p.wait_for_selector("input[type=password]", timeout=30000); p.fill("input[type=password]", PW); p.keyboard.press("Enter")
    p.wait_for_timeout(9000)
    if "mfa" in p.url or "verif" in p.inner_text("body").lower():
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 90)); print("NEED_CODE", flush=True)
        p.keyboard.type(gh_code(ts)); p.keyboard.press("Enter"); p.wait_for_timeout(9000)
    print("after login", p.url, flush=True)
    # warm up: make sure the panel is added on each issue before recording
    for k in ["PAY-1", "PAY-5", "PAY-6"]:
        try: open_panel(p, k)
        except Exception as e: print("warm", k, e, flush=True)
    c1.storage_state(path="/tmp/state.json"); c1.close()

    c2 = b.new_context(viewport={"width": 1440, "height": 900}, locale="en-US", user_agent=ua, storage_state="/tmp/state.json",
                       record_video_dir="/tmp/vid", record_video_size={"width": 1440, "height": 900})
    p = c2.new_page(); T0[0] = time.time()
    for i, fn in enumerate([s0, s1, s2, s3, s4, s5, s6, s7]):
        scene(i, fn, p)
    vpath = p.video.path(); c2.close(); b.close()

json.dump(marks, open(f"{OUT}/marks.json", "w"))
# audio track: each clip placed at its scene start
inputs, filt = [], []
for i, m in enumerate(marks):
    inputs += ["-i", f"/tmp/s{i}.mp3"]; filt.append(f"[{i+1}:a]adelay={int(m*1000)}|{int(m*1000)}[a{i}]")
filt.append("".join(f"[a{i}]" for i in range(len(marks))) + f"amix=inputs={len(marks)}:normalize=0[aout]")
subprocess.run(["ffmpeg", "-y", "-i", vpath, *inputs, "-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[aout]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest",
                f"{OUT}/demo.mp4"], check=True)
print("DONE", subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{OUT}/demo.mp4"]).decode(), flush=True)
