import csv
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

# =================================================================
# MOODLE QUIZ TIMING & IP LOCKDOWN BOT (ROBUST V3)
# =================================================================
BASE_URL = "https://service.sjctni.edu/jostel/moodle"
CSV_FILE = "moodle_quiz_timing_schedule.csv"
SUBNET_IPS = "172.16.123.,172.16.139.,172.16.109.,172.16.140."

def print_hdr(msg):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] === {msg} ===")

print("=====================================================")
print("  MOODLE QUIZ TIMING & IP LOCKDOWN BOT (ROBUST V3)  ")
print("=====================================================\n")

# Load Tasks
tasks = []
try:
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tasks.append(row)
    print(f"[+] Loaded {len(tasks)} course timing schedules from {CSV_FILE}.")
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

def select_dropdown(name, val):
    try:
        elem = driver.find_element(By.NAME, name)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
        sel = Select(elem)
        sel.select_by_value(str(val))
    except Exception as e:
        driver.execute_script(f"""
        var el = document.querySelector('[name="{name}"]');
        if (el) {{
            el.value = "{val}";
            el.dispatchEvent(new Event('change'));
        }}
        """)

def set_moodle_datetime(prefix, dt_str):
    """ Enables checkbox and sets day, month, year, hour, minute dropdowns """
    if not dt_str: return
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        
        # 1. Enable Checkbox
        checkbox_name = f"{prefix}[enabled]"
        try:
            chk = driver.find_element(By.NAME, checkbox_name)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", chk)
            if not chk.is_selected():
                chk.click()
                time.sleep(0.2)
        except:
            driver.execute_script(f"""
            var btn = document.querySelector('[name="{checkbox_name}"]') || document.getElementById('id_{prefix}_enabled');
            if (btn && !btn.checked) btn.click();
            """)
            time.sleep(0.2)

        # 2. Set Dropdowns
        select_dropdown(f"{prefix}[day]", dt.day)
        select_dropdown(f"{prefix}[month]", dt.month)
        select_dropdown(f"{prefix}[year]", dt.year)
        select_dropdown(f"{prefix}[hour]", dt.hour)
        select_dropdown(f"{prefix}[minute]", dt.minute)

        print(f"      - {prefix.upper()} set to: {dt.strftime('%d %b %Y, %I:%M %p')}")
    except Exception as e:
        print(f"      - [!] Could not set datetime for {prefix}: {e}")

def configure_quiz(shortname, quiz_start, quiz_end, ip_restriction):
    print(f"\n -> Locating Course: {shortname}")
    try:
        driver.get(f"{BASE_URL}/course/search.php?search={shortname}")
        time.sleep(1)
        
        course_link = wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, 'course/view.php?id=')]")))
        course_link.click()
        time.sleep(1)
        
        # Find Quiz Activity link
        quiz_link = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'mod/quiz/view.php')]")))
        quiz_url = quiz_link.get_attribute("href")
        
        cmid = quiz_url.split("id=")[1].split("&")[0]
        
        # Direct navigate to Quiz Edit Settings page
        driver.get(f"{BASE_URL}/course/modedit.php?update={cmid}&return=0")
        time.sleep(1.5)
        
        # Expand all collapsed fieldsets
        driver.execute_script("""
        document.querySelectorAll('fieldset.collapsed').forEach(f => f.classList.remove('collapsed'));
        document.querySelectorAll('a.fheader').forEach(a => {
            if (a.getAttribute('aria-expanded') === 'false') a.click();
        });
        """)
        time.sleep(0.5)

        # Explicitly click 'Show more...' / 'Show advanced' inside Extra restrictions on attempts
        try:
            more_btns = driver.find_elements(By.XPATH, "//a[contains(@class, 'moreless-toggler') or contains(text(), 'Show more')]")
            for btn in more_btns:
                driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.3)
        except:
            pass
        
        # 1. Set Timings
        set_moodle_datetime("timeopen", quiz_start)
        set_moodle_datetime("timeclose", quiz_end)
        
        # 2. Set Subnet IP Restriction (Require network address)
        try:
            # Force unhide subnet field wrapper if hidden by Moodle JS
            driver.execute_script("""
            var el = document.getElementById('id_subnet');
            if (el) {
                var container = el.closest('.form-group') || el.closest('.fitem');
                if (container) container.style.display = 'flex';
                el.style.display = 'block';
            }
            """)
            
            ip_field = wait.until(EC.presence_of_element_located((By.ID, "id_subnet")))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", ip_field)
            ip_field.clear()
            ip_field.send_keys(ip_restriction)
            
            # Value verification check
            current_val = ip_field.get_attribute("value")
            if not current_val:
                # Direct JS value injection if send_keys failed
                driver.execute_script(f"document.getElementById('id_subnet').value = '{ip_restriction}';")
                
            print(f"      - IP SUBNET LOCK set to: {ip_restriction}")
        except Exception as ip_err:
            print(f"      - [!] Subnet IP field not found/updated: {ip_err}")

        # 3. Click Save and return to course
        save_btn = driver.find_element(By.ID, "id_submitbutton2")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_btn)
        save_btn.click()
        time.sleep(2)
        
        print(f"   [✅] SUCCESS: Configured & Saved for {shortname}")
    except Exception as e:
        print(f"   [❌] FAILED: Could not update quiz for {shortname}. Error: {e}")

# Main Batch Loop
print_hdr("QUIZ TIMING & IP LOCKDOWN BATCH PROCESS STARTED")
for idx, task in enumerate(tasks):
    shortname = task['Course_Shortname']
    q_start = task['Quiz_Start']
    q_end = task['Quiz_End']
    exam_slot = task['Exam_Time_Slot']
    exam_date = task['Exam_Date']
    
    print(f"[{idx+1}/{len(tasks)}] Processing {shortname} | Schedule: {exam_date} ({exam_slot})")
    configure_quiz(shortname, q_start, q_end, SUBNET_IPS)

print_hdr("BATCH AUTOMATION COMPLETE")
print(f"All {len(tasks)} course quizzes processed!")
driver.quit()
