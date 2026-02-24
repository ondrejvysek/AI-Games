ver = "0.9.9.9"
import appdaemon.plugins.hass.hassapi as hass
import time
import datetime
import os
import sys
import shutil
import pandas as pd
import zipfile
import math
from datetime import datetime as dt
from typing import Optional, Any
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import platform
import subprocess

# --- Helper Functions ---

def print_system_info() -> None:
    print("System Information:")
    print(f"Platform: {platform.system()}")
    print(f"Platform Release: {platform.release()}")
    print(f"Platform Version: {platform.version()}")
    print(f"Architecture: {platform.machine()}")
    print(f"Processor: {platform.processor()}")
    print(f"Python Version: {platform.python_version()}")

def print_installed_modules() -> None:
    print("\nInstalled Python Modules:")
    result = subprocess.run(['pip', 'list'], stdout=subprocess.PIPE, text=True)
    print(result.stdout)

def get_chromedriver_version() -> None:
    try:
        result = subprocess.run(['chromedriver', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            version_info = result.stdout.strip()
            print(f"ChromeDriver Version: {version_info}")
        else:
            print(f"Error: {result.stderr.strip()}")
    except FileNotFoundError:
        print("ChromeDriver is not installed or not found in the system PATH.")

def delete_folder_contents(folder_path: str) -> None:
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")

class Colors:
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    RESET = '\033[0m'

def zip_folder(folder_path: str, output_path: str) -> None:
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, arcname=os.path.relpath(file_path, start=folder_path))

def quit_driver(driver: Optional[webdriver.Chrome]) -> None:
    if driver:
        driver.quit()
    try:
        pid = True
        while pid:
            pid = os.waitpid(-1, os.WNOHANG)
            try:
                if pid[0] == 0:
                    pid = False
            except:
                pass
    except ChildProcessError:
        pass

def conv_date(s: str) -> datetime.datetime:
    s = s.replace("24:00:00", "23:59:00")
    return datetime.datetime.strptime(s, "%d.%m.%Y %H:%M:%S")

def _normalize_ha_state(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return "unknown"
    if isinstance(value, datetime.timedelta):
        value = str(value)
    s = str(value)
    s = " ".join(s.replace("\xa0", " ").split())
    return s[:255]

# --- Main Class ---

class pnd(hass.Hass):
    def initialize(self) -> None:
        print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: >>>>>>>>>>>> PND Initialize")
        print_system_info()
        print_installed_modules()
        get_chromedriver_version()

        self.username = self.args["PNDUserName"]
        self.password = self.args["PNDUserPassword"]
        self.download_folder = self.args["DownloadFolder"]
        self.datainterval = self.args["DataInterval"]
        self.ELM = self.args["ELM"]
        self.id = self.args.get("id", "")
        self.suffix = f"_{self.id}" if self.id else ""
        self.entity_id_consumption = f"sensor.pnd_consumption{self.suffix}"
        self.entity_id_production = f"sensor.pnd_production{self.suffix}"

        self.listen_event(self.run_pnd, "run_pnd")

    def terminate(self) -> None:
        print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: >>>>>>>>>>>> PND Terminate")

    def set_state_safe(self, entity_id: str, state: Any, attributes: Optional[dict] = None) -> Any:
        return self.set_state(entity_id, state=_normalize_ha_state(state), attributes=attributes or {})

    def _handle_error(self, message: str, raise_exception: bool = True) -> None:
        print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.RED}ERROR: {message}{Colors.RESET}")
        self.set_state(f"binary_sensor.pnd_running{self.suffix}", state="off")
        self.set_state(f"sensor.pnd_script_status{self.suffix}", state="Error", attributes={
            "status": message,
            "friendly_name": "PND Script Status"
        })
        if raise_exception:
            raise Exception(message)

    def _download_report(self, driver: webdriver.Chrome, link_text: str, output_filename: str, screenshot_prefix: str) -> bool:
        wait = WebDriverWait(driver, 10)
        body = driver.find_element(By.TAG_NAME, 'body')

        try:
            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: Selecting {link_text}")
            first_pnd_window = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".pnd-window")))
            link = WebDriverWait(first_pnd_window, 10).until(
                EC.element_to_be_clickable((By.XPATH, f".//a[contains(text(), '{link_text}')]"))
            )
            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {link.text}")

            actions = ActionChains(driver)
            actions.move_to_element(link).perform()

            body.screenshot(os.path.join(self.download_folder, f"{screenshot_prefix}a.png"))
            time.sleep(1)
            link.click()
            body.screenshot(os.path.join(self.download_folder, f"{screenshot_prefix}b.png"))
            time.sleep(1)
            body.click()
            body.screenshot(os.path.join(self.download_folder, f"{screenshot_prefix}c.png"))
        except Exception as e:
            self._handle_error(f"ERROR: Nepodařilo se najít odkaz pro export {link_text} - {str(e)}", raise_exception=False)
            return False

        print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: Exporting data")
        try:
            # Ensure previous download file is removed
            downloaded_file = os.path.join(self.download_folder, "pnd_export.csv")
            if os.path.exists(downloaded_file):
                try:
                    os.remove(downloaded_file)
                except OSError:
                    pass

            toggle_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Exportovat data')]")))
            time.sleep(1)
            toggle_button.click()

            csv_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[normalize-space()='CSV']")))
            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: Downloading CSV file for {link_text}")
            csv_link.click()
        except Exception as e:
             self._handle_error(f"ERROR: Nepodařilo se stáhnout CSV soubor pro export {link_text} - {str(e)}", raise_exception=False)
             return False

        # Wait for download
        timeout = 30
        start_time = time.time()
        while time.time() - start_time < timeout:
            if os.path.exists(downloaded_file):
                # Simple check for now, assuming Chrome handles renaming atomically or uses .crdownload
                # A more robust check would involve checking for .crdownload file
                crdownload_file = downloaded_file + ".crdownload"
                if not os.path.exists(crdownload_file):
                    break
            time.sleep(1)

        if os.path.exists(downloaded_file):
            new_filename = os.path.join(self.download_folder, output_filename)
            if os.path.exists(new_filename):
                os.remove(new_filename)
            os.rename(downloaded_file, new_filename)
            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.GREEN}File downloaded and saved as: {new_filename} {round(os.path.getsize(new_filename)/1024,2)} KB{Colors.RESET}")
            return True
        else:
             print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.RED}ERROR: No file was downloaded for {link_text}{Colors.RESET}")
             return False

    def _process_daily_data(self) -> None:
        try:
            data_consumption = pd.read_csv(os.path.join(self.download_folder, 'daily-consumption.csv'), delimiter=';', encoding='latin1')
            latest_consumption_entry = data_consumption.iloc[-1]
            data_production = pd.read_csv(os.path.join(self.download_folder, 'daily-production.csv'), delimiter=';', encoding='latin1')
            latest_production_entry = data_production.iloc[-1]

            date_consumption_str = latest_consumption_entry.iloc[0]
            date_consumption_obj = conv_date(date_consumption_str)
            yesterday_consumption = date_consumption_obj - datetime.timedelta(days=1)

            date_production_str = latest_production_entry.iloc[0]
            date_production_obj = conv_date(date_production_str)
            yesterday_production = date_production_obj - datetime.timedelta(days=1)

            consumption_value = latest_consumption_entry.iloc[1]
            production_value = latest_production_entry.iloc[1]

            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.GREEN}Latest entry: {date_consumption_str} - {consumption_value} kWh{Colors.RESET}")
            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.GREEN}Latest entry: {date_production_str} - {production_value} kWh{Colors.RESET}")

            self.set_state(self.entity_id_consumption, state=consumption_value, attributes={
              "friendly_name": "PND Consumption",
              "device_class": "energy",
              "unit_of_measurement": "kWh",
              "date": yesterday_consumption.isoformat()
            })
            self.set_state(self.entity_id_production, state=production_value, attributes={
              "friendly_name": "PND Production",
              "device_class": "energy",
              "unit_of_measurement": "kWh",
              "date": yesterday_production.isoformat()
            })
            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: All Done - DAILY DATA PROCESSED")
        except Exception as e:
            self._handle_error(f"ERROR: Failed to process daily data - {str(e)}", raise_exception=False)

    def _process_interval_data(self) -> None:
        try:
            data_consumption = pd.read_csv(os.path.join(self.download_folder, 'range-consumption.csv'), delimiter=';', encoding='latin1', converters={0: lambda s: dt.strptime(s.replace("24:00:00","23:59:00"), "%d.%m.%Y %H:%M:%S")})
            data_production = pd.read_csv(os.path.join(self.download_folder, 'range-production.csv'), delimiter=';', encoding='latin1', converters={0: lambda s: dt.strptime(s.replace("24:00:00","23:59:00"), "%d.%m.%Y %H:%M:%S")})

            date_str = [d.date().isoformat() for d in data_consumption.iloc[:, 0]]
            consumption_str = [str(x) for x in data_consumption.iloc[:, 1].to_list()]
            production_str = [str(x) for x in data_production.iloc[:, 1].to_list()]

            now = dt.now()
            self.set_state(f"sensor.pnd_data{self.suffix}", state=now.strftime("%Y-%m-%d %H:%M:%S"), attributes={"pnddate": date_str, "consumption": consumption_str, "production": production_str})

            total_consumption = "{:.2f}".format(data_consumption.iloc[:, 1].sum())
            total_production = "{:.2f}".format(data_production.iloc[:, 1].sum())

            self.set_state(f"sensor.pnd_total_interval_consumption{self.suffix}", state=total_consumption,attributes={
              "friendly_name": "PND Total Interval Consumption",
              "device_class": "energy",
              "unit_of_measurement": "kWh"
            })
            self.set_state(f"sensor.pnd_total_interval_production{self.suffix}", state=total_production,attributes={
              "friendly_name": "PND Total Interval Production",
              "device_class": "energy",
              "unit_of_measurement": "kWh"
            })

            percentage_diff = 0
            try:
                float_total_consumption = float(total_consumption)
                float_total_production = float(total_production)
                if float_total_consumption > 0:
                    percentage_diff = round((float_total_production / float_total_consumption) * 100, 2)
            except:
                pass

            capped_percentage_diff = 0
            try:
                capped_percentage_diff = round(min(float(percentage_diff), 100), 2)
            except:
                pass

            floored_min_percentage_diff = 0
            try:
                floored_min_percentage_diff = round(max(float(percentage_diff) - 100, 0), 2)
            except:
                pass

            self.set_state_safe(f"sensor.pnd_production2consumption{self.suffix}", state=str(capped_percentage_diff), attributes={
              "friendly_name": "PND Interval Production to Consumption Max",
              "state_class": "measurement",
              "unit_of_measurement": "%"
            })
            self.set_state_safe(f"sensor.pnd_production2consumptionfull{self.suffix}", state=str(percentage_diff), attributes={
              "friendly_name": "PND Interval Production to Consumption Full",
              "state_class": "measurement",
              "unit_of_measurement": "%"
            })
            self.set_state_safe(f"sensor.pnd_production2consumptionfloor{self.suffix}", state=str(floored_min_percentage_diff), attributes={
              "friendly_name": "PND Interval Production to Consumption Floor",
              "state_class": "measurement",
              "unit_of_measurement": "%"
            })
            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: All Done - INTERVAL DATA PROCESSED")
        except Exception as e:
            self._handle_error(f"ERROR: Failed to process interval data - {str(e)}", raise_exception=False)

    def run_pnd(self, event_name: str, data: Any, kwargs: Any) -> None:
        script_start_time = dt.now()
        print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.CYAN}********************* Starting {ver} *********************{Colors.RESET}")
        self.set_state(f"binary_sensor.pnd_running{self.suffix}", state="on")
        self.set_state(f"sensor.pnd_script_status{self.suffix}", state="Running", attributes={
          "status": "OK",
          "friendly_name": "PND Script Status"
        })
        print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: ----------------------------------------------")
        print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: Hello from AppDaemon for Portal Namerenych Dat")

        delete_folder_contents(self.download_folder+"/")
        os.makedirs(self.download_folder, exist_ok=True)

        chrome_options = Options()
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": self.download_folder,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": False
        })
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument("--log-level=3")

        service = Service('/usr/bin/chromedriver')
        driver = None

        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: Driver Loaded")
            driver.set_window_size(1920, 1080)

            PNDURL = "https://pnd.cezdistribuce.cz/cezpnd2/external/dashboard/view"
            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: Opening Website: {PNDURL}")
            driver.get(PNDURL)
            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: Website Opened")

            time.sleep(3)
            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: Current URL: {driver.current_url}")

            # Cookie Banner
            try:
                cookie_banner_close_button = driver.find_element(By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowallSelection")
                cookie_banner_close_button.click()
            except:
                print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: No cookie banner found")

            time.sleep(1)

            # Login
            try:
                username_field = driver.find_element(By.XPATH, "//input[@placeholder='Zadejte svůj e-mail']")
                password_field = driver.find_element(By.XPATH, "//input[@placeholder='Zadejte své heslo']")
                login_button_selector = "//button[@type='submit' and contains(@class, 'mui-btn--primary')]"

                username_field.send_keys(self.username)
                password_field.send_keys(self.password)

                wait = WebDriverWait(driver, 10)
                print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: Login button found, clicking it")
                login_button = wait.until(EC.element_to_be_clickable((By.XPATH, login_button_selector)))

                body = driver.find_element(By.TAG_NAME, 'body')
                body.screenshot(os.path.join(self.download_folder, "00.png"))
                login_button.click()
            except Exception as e:
                self._handle_error("ERROR: Nepodařilo se vyplnit přihlašovací údaje nebo najít a kliknout na tlačítko pro přihlášení")

            time.sleep(5)
            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: Current URL: {driver.current_url}")

            wait = WebDriverWait(driver, 20)
            body = driver.find_element(By.TAG_NAME, 'body')
            h1_text = "Naměřená data"
            try:
                wait.until(EC.presence_of_element_located((By.XPATH, f"//h1[contains(text(), '{h1_text}')]")))
                print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: H1 tag with text '{h1_text}' is present.")
            except:
                try:
                    alert_widget_content = driver.find_element(By.CLASS_NAME, "alertWidget__content").text
                    print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.RED}ERROR: {alert_widget_content}{Colors.RESET}")
                except:
                    pass
                self._handle_error("ERROR: Není možné se přihlásit do aplikace")

            body.screenshot(os.path.join(self.download_folder, "01.png"))

            # Modal Dialog
            try:
                modal_dialog = driver.find_element(By.CLASS_NAME, "modal-dialog")
                print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.YELLOW}Modal Dialog found{Colors.RESET}")
                try:
                    body.screenshot(os.path.join(self.download_folder, "01-modal.png"))
                    close_button = modal_dialog.find_element(By.XPATH, ".//button[contains(@class, 'btn pnd-btn btn-primary') and contains(text(), 'Přečteno')]")
                    close_button.click()
                    print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.GREEN}Modal Dialog closed successfully, reloading page{Colors.RESET}")
                    time.sleep(2)
                    driver.refresh()
                    print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.GREEN}Page reloaded successfully{Colors.RESET}")
                except:
                    print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.RED}ERROR: Close button not found in the modal dialog.{Colors.RESET}")
                    raise Exception("Unable to click the close button in the modal dialog")
            except:
                print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.GREEN}Modal dialog not found. Continuing without closing modal.{Colors.RESET}")

            time.sleep(2)

            # App Version
            try:
                version_element = driver.find_element(By.XPATH, "//div[contains(text(), 'Verze aplikace:')]")
                version_text = (version_element.get_attribute("textContent") or version_element.text or "").replace("\xa0", " ")
                parts = version_text.split(":", 1)
                version_number = parts[1].strip() if len(parts) > 1 else version_text.strip()
                version_number = str(version_number).strip() or "unknown"
                self.set_state_safe(f"sensor.pnd_app_version{self.suffix}", state=version_number, attributes={
                    "friendly_name": "PND App Version",
                })
                print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: App Version: {version_number}")
            except:
                pass

            first_pnd_window = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".pnd-window")))

            tabulka_dat_button = WebDriverWait(first_pnd_window, 10).until(
                EC.element_to_be_clickable((By.XPATH, ".//button[@title='Export']"))
            )
            tabulka_dat_button.click()
            body.screenshot(os.path.join(self.download_folder, "02.png"))

            # Rychlá sestava
            wait = WebDriverWait(driver, 2)
            option_text = "Rychlá sestava"
            for _ in range(10):
                dropdown_label = wait.until(EC.visibility_of_element_located((By.XPATH, "//label[contains(text(), 'Sestava')]")))
                dropdown = dropdown_label.find_element(By.XPATH, "./following-sibling::div//div[contains(@class, 'multiselect__tags')]")
                dropdown.click()

                option = wait.until(EC.element_to_be_clickable((By.XPATH, f"//span[contains(text(), '{option_text}')]")))
                option.click()
                body.click()
                try:
                    wait.until(EC.text_to_be_present_in_element((By.XPATH, "//span[@class='multiselect__single']"), "Rychlá sestava"))
                    break
                except TimeoutException:
                    continue
            else:
                self._handle_error("ERROR: Nebylo možné vybrat 'Rychlá sestava' po 10 pokusech. Zkuste skript spustit později znovu.")

            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.GREEN}Rychla Sestava selected successfully!{Colors.RESET}")
            body.screenshot(os.path.join(self.download_folder, "03.png"))
            time.sleep(1)

            # BeautifulSoup logic for ELM
            try:
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                dropdown_label = wait.until(EC.visibility_of_element_located((By.XPATH, "//label[contains(text(), 'Množina zařízení')]")))
                parent_element = dropdown_label.find_element(By.XPATH, ".//ancestor::div[contains(@class, 'form-group')]")
                elm_spans = soup.find_all('span', class_='multiselect__option', text=lambda text: text and text.startswith('ELM'))
                elm_values = [span.text for span in elm_spans]
                elm_values_string = ", ".join(elm_values)
                print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: Valid ELM numbers '{elm_values_string}'")
            except Exception as e:
                print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: Failed to extract valid ELM numbers: {e}")

            # ELM Selection
            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: Selecting ELM '{self.ELM}'")
            with open(os.path.join(self.download_folder, 'debug-ELM.txt'), 'w') as file:
                file.write(">>>Debug ELM<<<\n")

            wait = WebDriverWait(driver, 2)
            dropdown_label = wait.until(EC.visibility_of_element_located((By.XPATH, "//label[contains(text(), 'Množina zařízení')]")))
            parent_element = dropdown_label.find_element(By.XPATH, ".//ancestor::div[contains(@class, 'form-group')]")

            with open(os.path.join(self.download_folder, 'debug-ELM.txt'), 'a') as file:
                file.write(parent_element.get_attribute('outerHTML') + "\n")

            dropdown = dropdown_label.find_element(By.XPATH, "./following-sibling::div//div[contains(@class, 'multiselect__select')]")

            for i in range(10):
                dropdown.click()
                time.sleep(1)
                body.screenshot(os.path.join(self.download_folder, f"03-{i}-a.png"))
                try:
                    option = wait.until(EC.element_to_be_clickable((By.XPATH, f"//span[contains(text(), '{self.ELM}')]")))
                except:
                    self._handle_error(f"ERROR: Nebylo možné najít '{self.ELM}' v nabídce. Zkontrolujte ELM atribut v nastavení aplikace.")

                option.click()
                body.screenshot(os.path.join(self.download_folder, f"03-{i}-b.png"))
                body.click()

                button = driver.find_element(By.XPATH, "//button[contains(., 'Vyhledat data')]")
                class_attribute = button.get_attribute('class')
                try:
                    span = parent_element.find_element(By.XPATH, ".//span[@class='multiselect__single']").text
                except:
                    span = ''

                print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.CYAN}ELM Status: {span} - {self.ELM}{Colors.RESET}")

                with open(os.path.join(self.download_folder, 'debug-ELM.txt'), 'a') as file:
                     file.write(f">>>Iteration {i}<<<\n")
                     file.write("ELM Span content: " + span + "\n")
                     file.write(parent_element.get_attribute('outerHTML') + "\n")

                if 'disabled' not in class_attribute and span.strip() != '':
                    print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.GREEN}Iteration {i}: Vyhledat Button NOT disabled{Colors.RESET}")
                    break
                else:
                    print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.YELLOW}Iteration {i}: Vyhledat Button IS disabled{Colors.RESET}")
            else:
                self._handle_error(f"ERROR: Nebylo možné najít '{self.ELM}' po 10 pokusech. Zkontrolujte ELM atribut v nastavení aplikace.")

            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.GREEN}Device ELM '{self.ELM}' selected successfully!{Colors.RESET}")
            body.screenshot(os.path.join(self.download_folder, "04.png"))

            # Select 'Včera'
            try:
                wait = WebDriverWait(driver, 2)
                dropdown_label = wait.until(EC.element_to_be_clickable((By.XPATH, "//label[contains(text(), 'Období')]")))
                dropdown_container = dropdown_label.find_element(By.XPATH, "./following-sibling::div//div[contains(@class, 'multiselect__select')]")
                dropdown_container.click()
                option_vcera = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Včera') and contains(@class, 'multiselect__option')]")))
                option_vcera.click()
            except:
                self._handle_error("ERROR: Nepodařilo se vybrat 'Včera' v nabídce")

            body.screenshot(os.path.join(self.download_folder, "05.png"))

            # Click Search
            try:
                button = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Vyhledat data')]")))
                button.click()
                print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.GREEN}Button 'Vyhledat data' clicked successfully!{Colors.RESET}")
            except Exception as e:
                self._handle_error("ERROR: Nepodařilo se nalézt nebo kliknout na tlačítko 'Vyhledat data'")

            body.screenshot(os.path.join(self.download_folder, "06.png"))
            time.sleep(2)
            body.click()
            wait = WebDriverWait(driver, 10)
            body.screenshot(os.path.join(self.download_folder, "07.png"))

            # Download Daily Data
            self._download_report(driver, "07 Profil spotřeby za den (+A)", "daily-consumption.csv", "daily-body-07")
            self._download_report(driver, "08 Profil výroby za den (-A)", "daily-production.csv", "daily-body-08")

            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: All Done - DAILY DATA DOWNLOADED")
            self._process_daily_data()

            # --- Interval ---
            try:
                wait = WebDriverWait(driver, 2)
                dropdown_label = wait.until(EC.element_to_be_clickable((By.XPATH, "//label[contains(text(), 'Období')]")))
                dropdown_container = dropdown_label.find_element(By.XPATH, "./following-sibling::div//div[contains(@class, 'multiselect__select')]")
                dropdown_container.click()
                option_vlastni = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Vlastní') and contains(@class, 'multiselect__option')]")))
                option_vlastni.click()

                label = wait.until(EC.visibility_of_element_located((By.XPATH, "//label[contains(text(), 'Vlastní období')]")))
                input_field = label.find_element(By.XPATH, "./following::input[1]")
                input_field.clear()
                input_field.send_keys(self.datainterval)
                input_field.send_keys(Keys.TAB)
                body.click()
            except:
                self._handle_error("ERROR: Nepodařilo se vybrat 'Vlastní období' v nabídce")

            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: Data Interval Entered - '{self.datainterval}'")
            time.sleep(1)

            try:
                tabulka_dat_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@title='Tabulka dat']")))
                tabulka_dat_button.click()
                time.sleep(1)
                tabulka_dat_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@title='Export']")))
                tabulka_dat_button.click()
                body.click()
            except:
                self._handle_error("ERROR: Nepodařilo se kliknout na tlačítko 'Tabulka dat'")

            wait = WebDriverWait(driver, 10)

            # Download Interval Data
            self._download_report(driver, "07 Profil spotřeby za den (+A)", "range-consumption.csv", "interval-body-07")
            self._download_report(driver, "08 Profil výroby za den (-A)", "range-production.csv", "interval-body-08")

            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: All Done - INTERVAL DATA DOWNLOADED")
            self._process_interval_data()

        except Exception as e:
            if "ERROR:" not in str(e):
                self._handle_error(f"Uncaught Error: {str(e)}", raise_exception=False)
            else:
                 pass # Already handled

        finally:
            if driver:
                quit_driver(driver)
                print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: All Done - BROWSER CLOSED")

            self.set_state(f"binary_sensor.pnd_running{self.suffix}", state="off")
            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: Sensor State Set to OFF")

            try:
                zip_folder(f"/homeassistant/appdaemon/apps/pnd{self.suffix}", f"/homeassistant/appdaemon/apps/debug{self.suffix}.zip")
                if os.path.exists(f"/homeassistant/appdaemon/apps/debug{self.suffix}.zip"):
                     shutil.move(f"/homeassistant/appdaemon/apps/debug{self.suffix}.zip", os.path.join(self.download_folder, "debug.zip"))
                print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: Debug Files Zipped")
            except Exception as e:
                print(f"Failed to zip debug files: {e}")

            script_end_time = dt.now()
            script_duration = script_end_time - script_start_time
            self.set_state(f"sensor.pnd_script_duration{self.suffix}", state=script_duration, attributes={
              "friendly_name": "PND Script Duration",
            })

            # Check if we ended in error or success
            status_state = self.get_state(f"sensor.pnd_script_status{self.suffix}")
            if status_state != "Error":
                 self.set_state(f"sensor.pnd_script_status{self.suffix}", state="Stopped", attributes={
                  "status": "Finished",
                })

            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.CYAN}********************* Duration: {script_duration} *********************{Colors.RESET}")
            print(f"{dt.now().strftime('%Y-%m-%d %H:%M:%S')}: {Colors.CYAN}********************* Finished {ver} *********************{Colors.RESET}")
