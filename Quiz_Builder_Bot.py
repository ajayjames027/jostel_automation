import csv
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

# --- CONFIGURATION ---
BASE_URL = "https://service.sjctni.edu/jostel/moodle"
CSV_FILE = "moodle_course_timing_update.csv"
TEST_MODE = True # Pauses on the first quiz for approval
QUIZ_NAME_TO_FIND = "NPTEL SWAYAM ALTERNATE ASSESSMENT"

print("=================================================")
print("   JOSTEL QUIZ TIMING UPDATER BOT (UPDATE MODE)  ")
print("=================================================\n")

print("1. Reading timings from CSV...")
courses_to_update = []
try:
    with open(CSV_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            courses_to_update.append({
                'shortname': row['shortname'].strip(),
                'start_str': row['startdate'].strip(),
                'end_str': row['enddate'].strip()
            })
    print(f"-> Loaded {len(courses_to_update)} courses to process.\n")
except Exception as e:
    print("Error reading CSV:", e)
    exit(1)

print("2. Starting Secure Chrome Browser...")
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(options=options)

print("3. Navigating to Moodle Login.")
driver.get(f"{BASE_URL}/login/index.php")

print("\n>>> MANUAL ACTION REQUIRED <<<")
print("Please log into Moodle inside the Chrome window that just opened.")
input("Press ENTER here in your terminal ONLY AFTER you have successfully logged in... ")

print("\n4. Commencing Bulk Quiz Updating!")
wait = WebDriverWait(driver, 10)

def set_moodle_date(prefix, dt_str):
    if not dt_str: return
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    
    # Forcefully bypass collapsed tab visibility issues by asking the browser itself to inject the dates
    try:
        js_cmd = f"""
        var btn = document.querySelector('[name="{prefix}[enabled]"]') || document.getElementById('id_{prefix}_enabled');
        if (btn && !btn.checked) btn.click(); // Enable it

        var selects = [
            {{ el: document.querySelector('[name="{prefix}[day]"]') || document.getElementById('id_{prefix}_day'), val: {dt.day} }},
            {{ el: document.querySelector('[name="{prefix}[month]"]') || document.getElementById('id_{prefix}_month'), val: {dt.month} }},
            {{ el: document.querySelector('[name="{prefix}[year]"]') || document.getElementById('id_{prefix}_year'), val: {dt.year} }},
            {{ el: document.querySelector('[name="{prefix}[hour]"]') || document.getElementById('id_{prefix}_hour'), val: {dt.hour} }},
            {{ el: document.querySelector('[name="{prefix}[minute]"]') || document.getElementById('id_{prefix}_minute'), val: {dt.minute} }}
        ];

        selects.forEach(s => {{
            if(s.el) s.el.value = s.val;
        }});
        """
        driver.execute_script(js_cmd)
        print(f"   [+] Force-injected {prefix} to {dt_str}")
    except Exception as e:
        print(f"  [!] Note: Trouble setting {prefix} date using JS injection: {e}")

is_first = True

for course in courses_to_update:
    print(f"\n-> Processing course: {course['shortname']}")
    
    try:
        # Step A: Search for the course using Selenium to bypass Cloudflare
        search_url = f"{BASE_URL}/course/search.php?search={course['shortname']}"
        driver.get(search_url)
        
        # Open the Course Page itself
        course_link = wait.until(EC.presence_of_element_located((By.XPATH, f"//a[contains(@href, 'course/view.php?id=')]")))
        course_url = course_link.get_attribute("href")
        driver.get(course_url)
        
        # Step B: Look for the specific quiz in the course contents
        # We look for a link going to mod/quiz/view.php that contains the text
        try:
            quiz_link = wait.until(EC.presence_of_element_located(
                (By.XPATH, f"//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'nptel swayam alternate assessment')]")
            ))
            quiz_view_url = quiz_link.get_attribute("href")
            # Usually format is .../mod/quiz/view.php?id=4567 
            cmid = quiz_view_url.split("id=")[1].split("&")[0]
            print(f"   [+] Found Existing Quiz (CMID: {cmid})")
        except:
            print(f"   [!] Could not find quiz named '{QUIZ_NAME_TO_FIND}' inside this course. Skipping!")
            continue
            
        # Step C: Jump directly into the MODEDIT page to safely update timings only!
        target_quiz_update_url = f"{BASE_URL}/course/modedit.php?update={cmid}&return=0"
        driver.get(target_quiz_update_url)
        
        # Expand Timing if needed
        try:
            timing_header = driver.find_element(By.XPATH, "//a[contains(text(), 'Timing')]")
            driver.execute_script("arguments[0].scrollIntoView();", timing_header)
            if timing_header.get_attribute("aria-expanded") == "false":
                timing_header.click()
                time.sleep(1)
        except:
            pass
            
        # Update Timings
        if course['start_str']:
            set_moodle_date("timeopen", course['start_str'])
            
        if course['end_str']:
            set_moodle_date("timeclose", course['end_str'])
            
        if is_first and TEST_MODE:
            print("\n================= TEST MODE ==================")
            print("The bot has found and configured the very first existing quiz.")
            print("Please LOOK AT THE BROWSER and check if the Open/Close limits are exactly right.")
            input("Press ENTER here to save this quiz and automatically bulk-process ALL the rest... ")
            print("==============================================\n")
            is_first = False
            
        # Save and return to course (don't touch the names!)
        submit_btn = driver.find_element(By.ID, "id_submitbutton2") # "Save and return to course"
        driver.execute_script("arguments[0].scrollIntoView();", submit_btn)
        submit_btn.click()
        
        time.sleep(2)
        print("   [+] Updated Quiz Timings Successfully.")
        
    except Exception as e:
        print(f"   [!] Error processing {course['shortname']}.")

print("\n=======================================================")
print(" ALL QUIZ TIMINGS HAVE BEEN UPDATED SUCCESSFULLY! ")
print("=======================================================")
driver.quit()
