import csv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# =================================================================
# MOODLE READINESS SCANNER BOT
# =================================================================
BASE_URL = "https://service.sjctni.edu/jostel/moodle"
CSV_FILE = "moodle_course_upload_ready_v2.csv"

print("=====================================================")
print("      MOODLE QUIZ UPLOAD VERIFICATION SCANNER        ")
print("=====================================================\n")

courses = []
try:
    with open(CSV_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            courses.append(row)
    print(f"[+] Loaded {len(courses)} courses from {CSV_FILE}.")
except Exception as e:
    print(f"[!] Error loading {CSV_FILE}. Error: {e}")
    exit(1)

print("\n[*] INIT: Checking Moodle Cloud Health...")
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 10)

driver.get(f"{BASE_URL}/login/index.php")
src = driver.page_source
if "503 Service Temporarily Unavailable" in src:
    print("[CRITICAL ERROR] The College Moodle Server is currently OFFLINE (HTTP 503).")
    print("Cannot perform scan. Please check your network or wait for server recovery.")
    driver.quit()
    exit(1)

print(">>> MANUAL ACTION REQUIRED <<<")
print("Please log into Moodle inside the Chrome window.")
input("Press ENTER in this terminal ONLY AFTER you have successfully logged in... ")

report_ready = []
report_pending = []

print("\n[*] SCANNING COURSE QUIZZES IN REAL-TIME...\n")
for idx, course in enumerate(courses):
    shortname = course['shortname'].strip()
    if not shortname: continue
    
    status = "UNKNOWN"
    
    try:
        # Search Course
        driver.get(f"{BASE_URL}/course/search.php?search={shortname}")
        search_results = driver.find_elements(By.XPATH, f"//a[contains(@href, 'course/view.php?id=')]")
        
        if not search_results:
            status = "NOT FOUND"
            print(f"[{idx+1}/{len(courses)}] {shortname} >> {status}")
            continue
            
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_results[0])
        search_results[0].click()
        
        # Look for Quiz link
        time.sleep(1) # Let DOM load
        try:
            quiz_link = driver.find_element(By.XPATH, "//a[contains(@href, 'mod/quiz/view.php')]")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", quiz_link)
            quiz_link.click()
            time.sleep(1)
            
            # Check for Empty warning
            page_text = driver.page_source.lower()
            if "no questions have been added" in page_text:
                status = "PENDING - EMPTY QUIZ"
                report_pending.append(shortname)
            else:
                status = "READY - UPLOADED"
                report_ready.append(shortname)
        except:
            status = "PENDING - NO QUIZ MODULE FOUND"
            report_pending.append(shortname)
            
    except Exception as e:
        status = "ERROR PARSING"
        
    print(f"[{idx+1}/{len(courses)}] {shortname} >> {status}")

driver.quit()

print("\n=======================================================")
print(f" SCAN COMPLETED. RESULTS SUMMARY:")
print(f"   ✅ READY FOR EXAM : {len(report_ready)} Courses")
print(f"   ❌ PENDING UPLOAD : {len(report_pending)} Courses")
print("=======================================================\n")

if len(report_pending) > 0:
    print("ACTION REQUIRED ON THE FOLLOWING COURSES:")
    for p in report_pending:
        print(f" - {p}")
