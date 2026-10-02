from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
import time
import os

def fetch_grades_via_browser(username, password, quiz_url):
    print("Setting up automated browser...")
    # Configure Chrome to automatically download files to the current folder
    download_dir = os.path.abspath(".")
    options = webdriver.ChromeOptions()
    prefs = {"download.default_directory": download_dir, "download.prompt_for_download": False}
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=options)
    
    try:
        print("1. Opening Moodle login page...")
        driver.get("https://service.sjctni.edu/jostel/moodle/login/index.php")
        
        # Log in mimicking a real human
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.ID, "loginbtn").click()
        
        print(f"2. Logged in! Navigating straight to your URL: {quiz_url}...")
        time.sleep(2) # Give the dashboard a second to load cookies
        driver.get(quiz_url)
        
        print("3. Looking for Moodle's built-in download button...")
        # Moodle quiz reports always have a format dropdown box at the bottom of the table
        download_dropdown_element = wait.until(EC.presence_of_element_located((By.NAME, "download")))
        download_select = Select(download_dropdown_element)
        
        # Select "Comma separated values (.csv)"
        download_select.select_by_value("csv") 
        
        # Click the actual Download button
        download_btn = driver.find_element(By.XPATH, "//button[@type='submit' and text()='Download']")
        download_btn.click()
        
        print("\n✅ Success! The grades have been directly downloaded to this folder.")
        time.sleep(5) # Give Chrome 5 seconds to finish saving the file before we close it
        
    except Exception as e:
        print(f"\n❌ Could not grab the file. The page may not have fully loaded or there are no grades yet.")
        print(f"Error Details: {str(e)}")
    finally:
        driver.quit()

if __name__ == "__main__":
    # --- FILL THESE IN BEFORE RUNNING ---
    MY_MOODLE_USERNAME = "your_staff_username"
    MY_MOODLE_PASSWORD = "your_password"
    
    URL = "https://service.sjctni.edu/jostel/moodle/mod/quiz/report.php?id=13199"
    
    fetch_grades_via_browser(MY_MOODLE_USERNAME, MY_MOODLE_PASSWORD, URL)
