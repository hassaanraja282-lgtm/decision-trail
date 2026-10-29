R = "https://github.com/hassaanraja282-lgtm/decision-trail"
p.get_by_role("button", name="Edit").first.click(); p.wait_for_timeout(4000)
p.check("input[name=distributionStatus][value=public]", force=True); p.wait_for_timeout(800)
p.fill("input[name=vendorName]", "Raja Hassaan")
p.fill("input[name=supportUrl]", R + "/issues")
p.fill("input[name=privacyPolicyUrl]", R + "/blob/main/PRIVACY.md")
p.fill("input[name=termsOfServiceUrl]", R + "/blob/main/TERMS.md")
# personal data select -> Yes (we store Atlassian account IDs)
sel = p.get_by_text("PERSONAL DATA DECLARATION").locator("xpath=following::*[contains(@class,'select') or @role='combobox'][1]")
try:
    p.get_by_text("No", exact=True).last.click(timeout=4000)
except Exception:
    sel.click()
p.wait_for_timeout(1000)
p.get_by_role("option", name="Yes").click(timeout=5000); p.wait_for_timeout(1500)
shot(p, "filled"); print("AFTER FILL", p.inner_text("main")[:2500] if p.locator("main").count() else "", flush=True)
dump(p)
p.get_by_role("button", name="Save changes").click(); p.wait_for_timeout(6000)
shot(p, "saved"); print("AFTER SAVE", p.inner_text("body")[-2500:], flush=True)
try:
    p.locator("label:has(input[name='jira-checkbox--hidden-checkbox']), [data-testid='jira-checkbox']").first.click(timeout=5000)
except Exception:
    p.check("input[name='jira-checkbox--hidden-checkbox']", force=True)
p.wait_for_timeout(5000)
shot(p, "jira")
txt = p.inner_text("body"); print("AFTER JIRA", txt[-2000:], flush=True)
links = p.eval_on_selector_all("input, a, code", "els => els.map(e => e.value || e.href || e.innerText).filter(v => v && v.includes('install'))")
print("INSTALL_LINKS", links, flush=True)
for m in re.findall(r"https://developer\.atlassian\.com/console/install/[^\s\"']+", txt): print("INSTALL_LINK", m, flush=True)
