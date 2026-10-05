    page.goto("https://www.interzoo.com/en/exhibitors-products/find-exhibitors")
    page.get_by_role("button", name="Allow all services").click()
    page.get_by_test_id("search-result-list").get_by_role("button", name="Show more arrow_forward_ios").click()