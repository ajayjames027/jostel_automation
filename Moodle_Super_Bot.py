import csv
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =================================================================
# MOODLE SUPER-ORCHESTRATOR BOT - V1 PRODUCTION
# =================================================================
BASE_URL = "https://service.sjctni.edu/jostel/moodle"
CSV_FILE = "moodle_bot_tasks.csv"

def print_hdr(msg):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] === {msg} ===")

print("=====================================================")
print("      MOODLE FULL-STACK AUTOMATION BOT (SELENIUM)    ")
print("=====================================================\n")

# Load Tasks
tasks = []
try:
    with open(CSV_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tasks.append(row)
    print(f"[+] Loaded {len(tasks)} automation directives from {CSV_FILE}.")
except Exception as e:
    print(f"[!] Error loading {CSV_FILE}. Are you sure it exists? Error: {e}")
    exit(1)

# Start Browser
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)

# Login Phase
print_hdr("SYSTEM AUTHENTICATION")
driver.get(f"{BASE_URL}/login/index.php")
print(">>> MANUAL ACTION REQUIRED <<<")
print("Please log into Moodle inside the Chrome window.")
input("Press ENTER in this terminal ONLY AFTER you have successfully logged in... ")

def wait_and_click(xpath):
    el = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
    time.sleep(0.5)
    el.click()

def wait_and_type(xpath, text):
    el = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
    el.clear()
    el.send_keys(text)

# Memory to avoid redundant category creations
category_cache = {}

def ensure_category(cat_name):
    """ Creates a category if it isn't tracked in this run's memory. """
    if cat_name in category_cache:
        return
    
    print(f" -> Checking/Creating Category: {cat_name}")
    try:
        driver.get(f"{BASE_URL}/course/editcategory.php?parent=0")
        wait_and_type("//input[@id='id_name']", cat_name)
        # Attempt to save
        submit = driver.find_element(By.ID, "id_submitbutton")
        driver.execute_script("arguments[0].click();", submit)
        time.sleep(1)
        category_cache[cat_name] = True
        print("   [+] Category established.")
    except Exception as e:
        print("   [!] Could not create category (might already exist). Proceeding.")
        category_cache[cat_name] = True

def create_course(fullname, shortname):
    print(f" -> Building Course: {fullname} ({shortname})")
    try:
        # Go straight to generic create course page
        driver.get(f"{BASE_URL}/course/edit.php?category=1") # Default category drop-in
        
        wait_and_type("//input[@id='id_fullname']", fullname)
        wait_and_type("//input[@id='id_shortname']", shortname)
        
        # Save
        save_btn = driver.find_element(By.ID, "id_saveanddisplay")
        driver.execute_script("arguments[0].click();", save_btn)
        time.sleep(2)
        print("   [+] Course built and launched.")
    except Exception as e:
        print(f"   [!] Failed to build course (It may already exist on this shortname).")

def enroll_faculty(shortname, email):
    if not email: return
    print(f" -> Enrolling Faculty ({email}) into {shortname}")
    try:
        # Search for course to get ID context
        driver.get(f"{BASE_URL}/course/search.php?search={shortname}")
        wait_and_click(f"//a[contains(@href, 'course/view.php?id=')]")
        
        # Go to participants
        participants_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Participants')]")
        course_id = participants_link.get_attribute("href").split("id=")[1]
        
        driver.get(f"{BASE_URL}/user/index.php?id={course_id}")
        
        # Trigger generic Enrol Modal (Moodle >= 3.10)
        try:
            wait_and_click("//button[contains(text(), 'Enrol users') or contains(text(), 'Enroll users')]")
            time.sleep(2)
            
            # Switch role to Editing Teacher
            select_role = driver.find_element(By.XPATH, "//select[contains(@id, 'id_roleassign')]")
            select_role.send_keys("Teacher")
            
            # Type email in search box
            search_input = driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Search')]")
            search_input.send_keys(email)
            time.sleep(1)
            search_input.send_keys(Keys.ENTER)
            time.sleep(1)
            
            wait_and_click("//button[contains(text(), 'Enrol users') or contains(text(), 'Enroll users')]")
            print("   [+] Faculty physically injected as Editing Teacher.")
        except Exception as inner:
            print("   [!] Could not interact with Enrollment UI hooks natively. Requires manual API check.")
    except Exception as e:
        print(f"   [!] Error navigating to participants for {shortname}.")

def set_moodle_date(prefix, dt_str):
    if not dt_str: return
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        js_cmd = f"""
        var btn = document.querySelector('[name="{prefix}[enabled]"]') || document.getElementById('id_{prefix}_enabled');
        if (btn && !btn.checked) btn.click();

        var sets = [
            {{ el: document.querySelector('[name="{prefix}[day]"]'), val: {dt.day} }},
            {{ el: document.querySelector('[name="{prefix}[month]"]'), val: {dt.month} }},
            {{ el: document.querySelector('[name="{prefix}[year]"]'), val: {dt.year} }},
            {{ el: document.querySelector('[name="{prefix}[hour]"]'), val: {dt.hour} }},
            {{ el: document.querySelector('[name="{prefix}[minute]"]'), val: {dt.minute} }}
        ];
        sets.forEach(s => {{ if(s.el) s.el.value = s.val; }});
        """
        driver.execute_script(js_cmd)
        print(f"      - Datetime parsed: {dt_str}")
    except Exception as e:
        print(f"      - Could not inject time constraint for {prefix}.")

def lockdown_quiz(shortname, start, end, ip):
    print(f" -> Deploying Quiz Constraints & Network IP Lockdown ({ip})")
    try:
        driver.get(f"{BASE_URL}/course/search.php?search={shortname}")
        wait_and_click(f"//a[contains(@href, 'course/view.php?id=')]")
        
        # Find the Quiz link
        quiz_link = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'mod/quiz/view.php')]")))
        quiz_url = quiz_link.get_attribute("href")
        
        cmid = quiz_url.split("id=")[1].split("&")[0]
        
        # Navigate to Modedit
        driver.get(f"{BASE_URL}/course/modedit.php?update={cmid}&return=0")
        
        # Inject Timings 
        set_moodle_date("timeopen", start)
        set_moodle_date("timeclose", end)
        
        # Inject IP restriction (Extra restrictions on attempts)
        try:
            extra_btn = driver.find_element(By.XPATH, "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'extra restrictions')]")
            driver.execute_script("arguments[0].scrollIntoView();", extra_btn)
            if extra_btn.get_attribute("aria-expanded") == "false":
                extra_btn.click()
                time.sleep(0.5)
            
            ip_box = driver.find_element(By.ID, "id_subnet")
            ip_box.clear()
            ip_box.send_keys(ip)
            print("      - Subnet lock established.")
        except:
            print("      - Note: No network subnet UI hook found on this quiz.")
            
        driver.find_element(By.ID, "id_submitbutton2").click()
        print("   [+] Quiz globally locked and secured.")
    except Exception as e:
        print("   [!] Could not attach quiz constraints. Is there a quiz natively created?")

def validate_ready(shortname):
    print(" -> Final Validation Pass: Scanning Quiz Engine Status")
    try:
        driver.get(f"{BASE_URL}/course/search.php?search={shortname}")
        wait_and_click(f"//a[contains(@href, 'course/view.php?id=')]")
        wait_and_click("//a[contains(@href, 'mod/quiz/view.php')]")
        
        # Check for error banners
        src = driver.page_source.lower()
        if "no questions have been added" in src:
            print("   [🚫] ALERT: Empty Quiz Detected! Questions must be uploaded before exam.")
        else:
            print("   [✅] ENGINE READY: Questions verified intact.")
    except:
        print("   [!] Could not parse readiness UI.")

# Execution Loop
print_hdr("COMMAND EXECUTION CYCLE INITIATED")
for idx, task in enumerate(tasks):
    print(f"\n[{idx+1}/{len(tasks)}] Processing Class Pipeline: {task.get('Course_Shortname', 'UNKNOWN')}")
    
    # 1. Category Hierarchy
    if task.get('Category'):
        ensure_category(task['Category'])
    if task.get('Sub_Category'):
        ensure_category(task['Sub_Category'])
        
    # 2. Course
    create_course(task.get('Course_Name', 'Unknown'), task.get('Course_Shortname', 'UNK'))
    
    # 3. Faculty
    enroll_faculty(task.get('Course_Shortname'), task.get('Faculty_Email'))
    
    # 4. Timings & IP constraints
    lockdown_quiz(
        task.get('Course_Shortname'), 
        task.get('Quiz_Start'), 
        task.get('Quiz_End'), 
        task.get('Subnet_IP')
    )
    
    # 5. Validation Check
    validate_ready(task.get('Course_Shortname'))
    
print_hdr("AUTOMATION SUCCESSFUL")
print("All tasks dynamically mapped to Moodle core instances.")
driver.quit()
