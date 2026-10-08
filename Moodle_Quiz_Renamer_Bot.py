import csv
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =================================================================
# MOODLE QUIZ RENAMER BOT
# =================================================================
BASE_URL = "https://service.sjctni.edu/jostel/moodle"
CSV_FILE = "moodle_quiz_timing_schedule.csv"

def print_hdr(msg):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] === {msg} ===")

print("=====================================================")
print("     MOODLE QUIZ RENAMER AUTOMATION BOT (SELENIUM)  ")
print("=====================================================\n")

# Load Tasks
tasks = []
try:
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tasks.append(row)
    print(f"[+] Loaded {len(tasks)} courses from {CSV_FILE}.")
except Exception as e:
    print(f"[!] Error loading {CSV_FILE}. Make sure it exists! Error: {e}")
    exit(1)

# Start Browser
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

# Login Phase
print_hdr("SYSTEM AUTHENTICATION")
driver.get(f"{BASE_URL}/login/index.php")
print(">>> MANUAL ACTION REQUIRED <<<")
print("Please log into Moodle inside the opened Chrome browser.")
input("Press ENTER in this terminal ONLY AFTER you have successfully logged into Moodle... ")

def rename_course_quiz(shortname):
    print(f"\n -> Locating Course: {shortname}")
    try:
        driver.get(f"{BASE_URL}/course/search.php?search={shortname}")
        time.sleep(1)
        
        # Click on course link
        course_link = wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, 'course/view.php?id=')]")))
        course_link.click()
        time.sleep(1)
        
        # Find Quiz Activity link
        quiz_link = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'mod/quiz/view.php')]")))
        quiz_url = quiz_link.get_attribute("href")
        
        cmid = quiz_url.split("id=")[1].split("&")[0]
        
        # Direct navigate to Quiz Edit Settings page
        driver.get(f"{BASE_URL}/course/modedit.php?update={cmid}&return=0")
        time.sleep(1)
        
        # Change Quiz Name (id_name)
        name_input = wait.until(EC.presence_of_element_located((By.ID, "id_name")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", name_input)
        name_input.clear()
        name_input.send_keys(shortname)
        print(f"      - Quiz Name set to: {shortname}")
        
        # Save and return to course
        save_btn = driver.find_element(By.ID, "id_submitbutton2")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_btn)
        save_btn.click()
        time.sleep(1.5)
        
        print(f"   [✅] SUCCESS: Quiz renamed to {shortname}")
    except Exception as e:
        print(f"   [❌] FAILED: Could not rename quiz for {shortname}. Error: {e}")

# Main Batch Loop
print_hdr("QUIZ RENAMING BATCH PROCESS STARTED")
for idx, task in enumerate(tasks):
    shortname = task['Course_Shortname']
    print(f"[{idx+1}/{len(tasks)}] Renaming Quiz for Course: {shortname}")
    rename_course_quiz(shortname)

print_hdr("QUIZ RENAMING COMPLETE")
print(f"All {len(tasks)} quizzes renamed to their respective course shortnames.")
driver.quit()
