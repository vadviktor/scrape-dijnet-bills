import logging
from datetime import datetime
import re

from scrape.download import file as download_file

from selenium.webdriver import Chrome, ChromeOptions, ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

USERNAME = ""
PASSWORD = ""
# [2021.03.28] Scrape next from this date:
FROM = "2021.03.28"

logging.basicConfig(
    format="%(levelname)s:%(filename)s:%(lineno)d:%(message)s", level=logging.DEBUG
)


class Spider:
    def __init__(self):
        self.url_login = "https://www.dijnet.hu/?bejelentkezes=open"
        self.url_control = "https://www.dijnet.hu/ekonto/control"
        self.url_szamla_search = f"{self.url_control}/szamla_search"
        self.username = USERNAME
        self.password = PASSWORD
        self.first_date = FROM
        self.providers = [
            "Díjbeszedő Zrt.",
            "FCSM Zrt.",
            "FŐTÁV Nonprofit Zrt.",
            "FV Zrt.",
            "Társ.díj felosz",
        ]

        options = ChromeOptions()
        options.add_argument("--headless")
        options.page_load_strategy = "eager"
        self.d = Chrome(options=options)
        self.wait = WebDriverWait(self.d, timeout=10, poll_frequency=2)

    def crawl(self):
        try:
            self.__login()
            for provider in self.providers:
                self.__bill_search(provider)
                self.__iter_over_bills(provider)

        except Exception as e:
            logging.exception(e, exc_info=True)
        finally:
            self.d.quit()

    def __login(self):
        self.d.get(self.url_login)
        form = self.d.find_element(By.ID, "loginform")
        form.find_element(By.NAME, "username").send_keys(self.username)
        form.find_element(By.NAME, "password").send_keys(self.password)
        form.submit()

        def username_is_visible(_) -> bool:
            header = self.d.find_element(By.TAG_NAME, "header")
            src: str = header.get_attribute("innerHTML")
            return self.username in src

        self.wait.until(username_is_visible, "Login failed.")

    def __bill_search(self, provider: str):
        self.d.get(self.url_szamla_search)

        szlaszolg_element = self.d.find_element(By.NAME, "szlaszolgnev")
        szlaszolg_object = Select(szlaszolg_element)
        szlaszolg_object.select_by_value(provider)

        regszolgid_element = self.d.find_element(By.NAME, "regszolgid")
        regszolgid_object = Select(regszolgid_element)
        regszolgid_object.select_by_index(1)

        self.d.find_element(By.NAME, "datumtol").send_keys(self.first_date)
        self.d.find_element(By.NAME, "datumig").send_keys(
            datetime.now().strftime("%Y.%m.%d")
        )
        self.d.find_element(By.ID, "button_szamla_search_submit").click()

    def __iter_over_bills(self, provider: str):
        self.wait.until(
            lambda _: self.d.find_element(
                By.CSS_SELECTOR, "table.szamla_table tbody tr"
            ),
            "Could not find szamla table",
        )

        rows_count = len(
            self.d.find_elements(By.CSS_SELECTOR, "table.szamla_table tbody tr")
        )

        for i in range(0, rows_count):
            row = self.d.find_element(
                By.CSS_SELECTOR, f"table.szamla_table tbody tr#r_{i}"
            )
            src = row.get_attribute("innerHTML")
            # skip if there won't be anything to download
            if "Rendezett" not in src:
                continue

            # scroll into view first
            self.d.execute_script("arguments[0].scrollIntoView();", row)
            # then move focus onto element to perform action
            ActionChains(self.d).move_to_element(row).click().perform()

            self.wait.until(
                lambda _: self.d.find_element(By.LINK_TEXT, "Letöltés"),
                "Could not find bill download tab",
            ).click()

            download_file(
                cookies=self.d.get_cookies(),
                url=f"{self.url_control}/{self.__download_filename()}",
                dir=f"bills/{provider}",
            )

            self.d.find_element(By.CSS_SELECTOR, "h1 a.xt_link__title").click()

    def __download_filename(self) -> str:
        download_pane: WebElement = self.wait.until(
            lambda _: self.d.find_element(By.ID, "tab_szamla_letolt"),
            "Could not find download panel",
        )
        src = download_pane.get_attribute("innerHTML")

        # look for combined bills first
        match = re.search(r"teho_all_pdf\?\d+", src)
        if match is not None:
            return match.group(0)

        # look for normal bills
        match = re.search(r"szamla_pdf\?\d+", src)

        if match is None:
            raise RuntimeError("Could not find document to download")

        return match.group(0)
