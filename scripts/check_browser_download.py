"""Read the result of a normal browser download. Never open the downloaded file."""
import hashlib
import os
from pathlib import Path
import shutil
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

version = os.environ["RELEASE_VERSION"]
name = f"AnonimizadorJudicial-{version}-Windows.zip"
release = f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/releases"
directory = Path("V:/Revision/Chrome")
directory.mkdir()
options = webdriver.ChromeOptions()
options.add_experimental_option("prefs", {"download.default_directory": str(directory),
    "download.prompt_for_download": False, "safebrowsing.enabled": True})
options.add_experimental_option("excludeSwitches", ["disable-client-side-phishing-detection",
    "safebrowsing-disable-auto-update", "disable-component-update", "disable-background-networking"])
driver_path = shutil.which("chromedriver")
with webdriver.Chrome(service=Service(executable_path=driver_path), options=options) as driver:
    print("Chrome",driver.capabilities["browserVersion"],flush=True)
    driver.get(f"{release}/tag/v{version}")
    selector = f'a[href$="/{name}"]'
    link = WebDriverWait(driver, 45).until(lambda d: next((a for a in d.find_elements(By.CSS_SELECTOR, selector) if a.is_displayed()), None))
    link.click()
    result = directory / name
    for _ in range(45):
        if result.is_file() and result.stat().st_size > 0:
            time.sleep(3)
            if result.is_file():
                with result.open("rb") as stream:
                    digest = hashlib.file_digest(stream,"sha256").hexdigest()
                if digest == os.environ["EXPECTED_SHA"]:
                    print("Descarga completa, SHA-256 coincide:",digest,flush=True)
                    break
        time.sleep(2)
    else:
        driver.get("chrome://downloads/")
        states = driver.execute_script("""return (document.querySelector('downloads-manager')?.shadowRoot?.querySelector('#downloadsList')?.items || []).map(x => ({fileName:x.fileName,state:x.state,dangerType:x.dangerType,lastReasonText:x.lastReasonText}));""")
        raise RuntimeError(f"Descarga sin confirmar: {states}")
