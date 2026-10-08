import csv
import time
from datetime import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =================================================================
# MOODLE DEFAULTER TEACHER & EMPTY QUIZ SCANNER BOT
# =================================================================
BASE_URL = "https://service.sjctni.edu/jostel/moodle"
CSV_FILE = "moodle_quiz_timing_schedule.csv"
ROSTER_FILE = "end_spl.csv"
OUTPUT_DEFAULTER_CSV = "defaulter_teachers_report.csv"

def print_hdr(msg):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] === {msg} ===")

print("=========================================================")
print(" MOODLE DEFAULTER FACULTY & EMPTY QUIZ SCANNER (SELENIUM)")
print("=========================================================\n")

# Load Roster to map course code -> staff name & staff id
staff_map = {}
try:
    df_roster = pd.read_csv(ROSTER_FILE)
    for _, row in df_roster.iterrows():
        code = str(row.get('coursecode', '')).strip()
        sname = str(row.get('staffname', '')).strip()
        sid = str(row.get('staffid', '')).strip()
        if code and code not in staff_map:
            staff_map[code] = {'staffname': sname, 'staffid': sid}
    print(f"[+] Loaded faculty mapping for {len(staff_map)} course codes from {ROSTER_FILE}.")
except Exception as e:
    print(f"[!] Warning: Could not load {ROSTER_FILE}: {e}")

# Load Tasks (Created Courses)
tasks = []
try:
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tasks.append(row)
    print(f"[+] Loaded {len(tasks)} courses to scan from {CSV_FILE}.")
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

def scan_quiz_status(shortname, course_code):
    print(f"\n -> Auditing Quiz for Course: {shortname}")
    staff_info = staff_map.get(course_code, {'staffname': 'Unknown', 'staffid': 'Unknown'})
    
    try:
        # Search & open course
        driver.get(f"{BASE_URL}/course/search.php?search={shortname}")
        time.sleep(1)
        
        course_link = wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, 'course/view.php?id=')]")))
        course_link.click()
        time.sleep(1)
        
        # Find Quiz Activity link
        quiz_link = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'mod/quiz/view.php')]")))
        quiz_url = quiz_link.get_attribute("href")
        
        # Direct navigate to Quiz View page
        driver.get(quiz_url)
        time.sleep(1.5)
        
        page_source = driver.page_source.lower()
        
        # Check Moodle empty quiz indicators
        is_empty = False
        if "no questions have been added" in page_source or "no questions have been added yet" in page_source or "questions: 0" in page_source:
            is_empty = True
        
        # Also check quiz edit page for grade sum or question list
        cmid = quiz_url.split("id=")[1].split("&")[0]
        driver.get(f"{BASE_URL}/mod/quiz/edit.php?cmid={cmid}")
        time.sleep(1)
        
        edit_page_src = driver.page_source.lower()
        if "total of marks: 0" in edit_page_src or "questions: 0" in edit_page_src or "add question" in edit_page_src and "delete" not in edit_page_src:
            is_empty = True

        if is_empty:
            print(f"   [🚨 DEFAULTER DETECTED] No questions uploaded! Faculty: {staff_info['staffname']} ({staff_info['staffid']})")
            return {
                'Course_Shortname': shortname,
                'Course_Code': course_code,
                'Faculty_Name': staff_info['staffname'],
                'Faculty_ID': staff_info['staffid'],
                'Status': 'EMPTY (No Questions Uploaded)',
                'Quiz_URL': quiz_url
            }
        else:
            print(f"   [✅ OK] Questions uploaded intact for {shortname}")
            return None

    except Exception as e:
        print(f"   [!] Could not audit {shortname}. Error: {e}")
        return {
            'Course_Shortname': shortname,
            'Course_Code': course_code,
            'Faculty_Name': staff_info['staffname'],
            'Faculty_ID': staff_info['staffid'],
            'Status': f'ERROR: {e}',
            'Quiz_URL': 'N/A'
        }

# Main Audit Loop
print_hdr("AUDITING ALL QUIZZES FOR MISSING QUESTIONS")
defaulters = []

for idx, task in enumerate(tasks):
    shortname = task['Course_Shortname']
    code = task.get('Course_Code', shortname.split('_')[0])
    
    print(f"[{idx+1}/{len(tasks)}] Auditing {shortname}")
    result = scan_quiz_status(shortname, code)
    if result:
        defaulters.append(result)

# Export Defaulters to CSV
print_hdr("AUDIT REPORT GENERATION")
if defaulters:
    keys = defaulters[0].keys()
    with open(OUTPUT_DEFAULTER_CSV, 'w', newline='', encoding='utf-8') as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(defaulters)
    print(f"[🚨] AUDIT COMPLETE: Found {len(defaulters)} defaulter courses with missing questions!")
    print(f"[📁] Defaulters exported to: {OUTPUT_DEFAULTER_CSV}")
else:
    print("[🎉] CONGRATULATIONS! All faculty members have successfully uploaded questions into their quizzes.")

driver.quit()
