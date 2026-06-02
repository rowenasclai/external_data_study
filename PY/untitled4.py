import re
from playwright.sync_api import Playwright, sync_playwright, expect
import csv

import asyncio
import json
import pandas as pd

import datetime


def run(playwright1: Playwright) -> None:

    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto(url, wait_until="domcontentloaded")
    
    page.get_by_text("Profile").click()

    print(page.inner_text())

    page.get_by_text("Contact Us").first.click()
    print(page.inner_text())



    context.close()
    browser.close()  
        

    

with sync_playwright() as playwright:
    run(playwright)