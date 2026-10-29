p.get_by_role("button", name="Edit").first.click(); p.wait_for_timeout(4000)
shot(p, "edit"); dump(p)
