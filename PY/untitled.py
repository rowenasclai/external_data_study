from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        #page.goto("https://playwright.dev/")

        page.goto("https://exhibitors.inhorgenta.com/exhibitordirectory/2026/list-of-exhibitors/")
        page.get_by_role("button", name="Accept All").click()
        page.get_by_role("button", name="Alphabet Filter - all").click()

        #print(page.title())
        browser.close()

if __name__ == "__main__":
    run()
