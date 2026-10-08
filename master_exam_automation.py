import os
import sys
import csv
import time
import re
from datetime import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

# =================================================================
# MASTER MOODLE EXAM AUTOMATION SUITE (FOR FUTURE EXAMS)
# =================================================================
# Standard Moodle Configuration
BASE_URL = "https://service.sjctni.edu/jostel/moodle"
DEFAULT_CATEGORY_ID = "962"
DEFAULT_TEMPLATE_COURSE = "Template_SL_End"
DEFAULT_SUBNET_IPS = "172.16.123.,172.16.139.,172.16.109.,172.16.140."

def print_banner():
    print("=" * 65)
    print("      JOSTEL MOODLE MASTER EXAM AUTOMATION SUITE      ")
    print("=" * 65)

def print_menu():
    print("\nSelect an Automation Module to Execute:")
    print(" 1. Generate Course & User Upload CSVs from Roster CSV/Excel")
    print(" 2. Extract Exam Timetable PDF -> CSV Schedule")
    print(" 3. Configure Quiz Timings & IP Restrictions (Selenium)")
    print(" 4. Rename All Quizzes to Course Shortnames (Selenium)")
    print(" 5. Audit & Generate Defaulter Faculty Report (Empty Quizzes)")
    print(" 6. Run Complete End-to-End Bot Suite (Steps 3, 4 & 5)")
    print(" 0. Exit Suite")
    print("-" * 65)

def slugify(text):
    return ''.join(e for e in str(text or 'Unknown') if e.isalnum())[:10]

# --- MODULE 1: ROSTER PROCESSING ---
def module_process_roster():
    print("\n--- MODULE 1: ROSTER PROCESSING ---")
    roster_file = input("Enter path to Roster file (default: end_spl.csv): ").strip() or "end_spl.csv"
    if not os.path.exists(roster_file):
        print(f"[!] File '{roster_file}' not found.")
        return
    
    cat_id = input(f"Enter Moodle Category ID (default: {DEFAULT_CATEGORY_ID}): ").strip() or DEFAULT_CATEGORY_ID
    template_shortname = input(f"Enter Template Course Shortname (default: {DEFAULT_TEMPLATE_COURSE}): ").strip() or DEFAULT_TEMPLATE_COURSE
    date_suffix = input("Enter Exam Date Suffix (e.g., 15102026 or leave blank): ").strip() or "15102026"
    
    print(f"\nProcessing {roster_file}...")
    if roster_file.endswith('.csv'):
        df = pd.read_csv(roster_file)
    else:
        df = pd.read_excel(roster_file)
        
    unique_courses = {}
    user_enrols = []
    teacher_map = {}
    
    for _, row in df.iterrows():
        course_code = str(row.get('coursecode', '') or row.get('Course Code', '')).strip()
        course_title = str(row.get('coursetitle', '') or row.get('Course Title', '')).strip()
        staff_id = str(row.get('staffid', '') or row.get('Staff Incharge', '') or row.get('Staff', '')).strip()
        staff_name = str(row.get('staffname', '') or row.get('Staff Incharge', '') or row.get('Staff', '')).strip()
        
        if not course_code: continue
        
        shortname = f"{course_code}_{date_suffix}" if date_suffix else course_code
        fullname = f"{course_code} - {course_title}"
        
        if shortname not in unique_courses:
            unique_courses[shortname] = {
                'shortname': shortname,
                'fullname': fullname,
                'category': cat_id,
                'templatecourse': template_shortname
            }
            
        # Student enrollment
        reg_no = str(row.get('regdno', '') or row.get('Reg. Nol', '') or row.get('RegNo', '') or row.get('Username', '')).strip()
        name = str(row.get('name', '') or row.get('Name', '') or '.').strip()
        if reg_no:
            user_enrols.append({
                'username': reg_no.lower(),
                'firstname': name,
                'lastname': '.',
                'course1': shortname,
                'role1': 'student'
            })
            
        # Teacher enrollment
        if staff_id and staff_id.lower() != 'nan':
            teacher_username = staff_id.lower()
            key = f"{shortname}_{teacher_username}"
            if key not in teacher_map:
                teacher_map[key] = True
                user_enrols.append({
                    'username': teacher_username,
                    'firstname': staff_name or '.',
                    'lastname': '.',
                    'course1': shortname,
                    'role1': 'editingteacher'
                })

    courses_df = pd.DataFrame(list(unique_courses.values()))
    users_df = pd.DataFrame(user_enrols)
    
    out_courses = "automated_courses_upload.csv"
    out_users = "automated_users_upload.csv"
    
    courses_df.to_csv(out_courses, index=False)
    users_df.to_csv(out_users, index=False)
    
    print(f"[✅] Created '{out_courses}' with {len(courses_df)} courses.")
    print(f"[✅] Created '{out_users}' with {len(users_df)} user records (students & teachers).")

# --- MODULE 2: PDF TIMETABLE PARSER ---
def module_parse_pdf():
    print("\n--- MODULE 2: TIMETABLE PDF PARSER ---")
    pdf_file = input("Enter PDF Timetable filename (default: JosTEL_End Semester Examinations - Self Learning Courses.pdf): ").strip()
    if not pdf_file:
        pdf_file = "JosTEL_End Semester Examinations - Self Learning Courses.pdf"
        
    roster_file = input("Enter Roster CSV filename (default: end_spl.csv): ").strip() or "end_spl.csv"
    
    if not os.path.exists(pdf_file) or not os.path.exists(roster_file):
        print("[!] Required PDF or Roster file not found.")
        return
        
    date_suffix = input("Enter Exam Date Suffix (e.g. 15102026): ").strip() or "15102026"
    
    import fitz # PyMuPDF
    doc = fitz.open(pdf_file)
    end_spl = pd.read_csv(roster_file)
    student_course = end_spl.set_index('regdno')['coursecode'].to_dict()
    
    pdf_rows = []
    for pno, page in enumerate(doc):
        text = page.get_text()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        for i, line in enumerate(lines):
            m = re.match(r'^([0-9]{2}[A-Z]{2,4}[0-9]{3,4})$', line)
            if m:
                regno = m.group(1)
                ctx = ' '.join(lines[max(0, i-8):min(len(lines), i+4)])
                date_m = re.search(r'(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})', ctx)
                time_m = re.search(r'(\d{1,2}:\d{2}\s*[AP]M\s*to\s*\d{1,2}:\d{2}\s*[AP]M)', ctx, re.IGNORECASE)
                pdf_rows.append({
                    'regno': regno,
                    'coursecode': student_course.get(regno, 'UNKNOWN'),
                    'date': date_m.group(1) if date_m else None,
                    'time': time_m.group(1) if time_m else None
                })

    df_pdf = pd.DataFrame(pdf_rows)
    df_clean = df_pdf[df_pdf['coursecode'] != 'UNKNOWN'].dropna(subset=['date', 'time'])
    
    timing_list = []
    for coursecode, group in df_clean.groupby('coursecode'):
        mode_row = group.groupby(['date', 'time']).size().idxmax()
        date_str, time_str = mode_row
        
        dt_obj = datetime.strptime(date_str, '%d %b %Y')
        formatted_date = dt_obj.strftime('%Y-%m-%d')
        
        t_start_str, t_end_str = time_str.split(' to ')
        t_start = datetime.strptime(t_start_str.strip(), '%I:%M %p').strftime('%H:%M:%S')
        t_end = datetime.strptime(t_end_str.strip(), '%I:%M %p').strftime('%H:%M:%S')
        
        shortname = f"{coursecode}_{date_suffix}" if date_suffix else coursecode
        timing_list.append({
            'Course_Shortname': shortname,
            'Course_Code': coursecode,
            'Exam_Date': date_str,
            'Exam_Time_Slot': time_str,
            'Quiz_Start': f"{formatted_date} {t_start}",
            'Quiz_End': f"{formatted_date} {t_end}"
        })

    out_df = pd.DataFrame(timing_list)
    out_file = "moodle_quiz_timing_schedule.csv"
    out_df.to_csv(out_file, index=False)
    print(f"[✅] Created '{out_file}' with {len(out_df)} exam timing schedules.")

# --- SELENIUM BOT ENGINE ---
def start_moodle_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)
    
    driver.get(f"{BASE_URL}/login/index.php")
    print("\n>>> MANUAL ACTION REQUIRED <<<")
    print("Please log into Moodle inside the opened Chrome browser window.")
    input("Press ENTER in this terminal ONLY AFTER you have successfully logged in... ")
    return driver, wait

def select_dropdown(driver, name, val):
    try:
        elem = driver.find_element(By.NAME, name)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
        sel = Select(elem)
        sel.select_by_value(str(val))
    except:
        driver.execute_script(f"var el = document.querySelector('[name=\"{name}\"]'); if(el){{el.value=\"{val}\"; el.dispatchEvent(new Event('change'));}}")

def set_moodle_datetime(driver, prefix, dt_str):
    if not dt_str: return
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        checkbox_name = f"{prefix}[enabled]"
        try:
            chk = driver.find_element(By.NAME, checkbox_name)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", chk)
            if not chk.is_selected():
                chk.click()
                time.sleep(0.2)
        except:
            driver.execute_script(f"var btn = document.querySelector('[name=\"{checkbox_name}\"]') || document.getElementById('id_{prefix}_enabled'); if (btn && !btn.checked) btn.click();")
            time.sleep(0.2)

        select_dropdown(driver, f"{prefix}[day]", dt.day)
        select_dropdown(driver, f"{prefix}[month]", dt.month)
        select_dropdown(driver, f"{prefix}[year]", dt.year)
        select_dropdown(driver, f"{prefix}[hour]", dt.hour)
        select_dropdown(driver, f"{prefix}[minute]", dt.minute)
    except Exception as e:
        print(f"      - [!] Datetime error for {prefix}: {e}")

# --- MODULE 3: TIMING & IP CONFIGURATOR ---
def module_configure_timings(driver=None, wait=None):
    print("\n--- MODULE 3: QUIZ TIMING & IP LOCKDOWN BOT ---")
    schedule_file = "moodle_quiz_timing_schedule.csv"
    if not os.path.exists(schedule_file):
        print(f"[!] Schedule file '{schedule_file}' not found. Please run Module 2 first.")
        return
        
    subnet_ips = input(f"Enter IP Restrictions (default: {DEFAULT_SUBNET_IPS}): ").strip() or DEFAULT_SUBNET_IPS
    
    tasks = []
    with open(schedule_file, 'r', encoding='utf-8') as f:
        tasks = list(csv.DictReader(f))
        
    close_at_end = False
    if driver is None:
        driver, wait = start_moodle_browser()
        close_at_end = True
        
    for idx, task in enumerate(tasks):
        shortname = task['Course_Shortname']
        print(f"[{idx+1}/{len(tasks)}] Setting Timing & IP for {shortname} ({task['Exam_Date']} {task['Exam_Time_Slot']})")
        try:
            driver.get(f"{BASE_URL}/course/search.php?search={shortname}")
            time.sleep(1)
            course_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'course/view.php?id=')]")))
            course_link.click()
            time.sleep(1)
            
            quiz_link = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'mod/quiz/view.php')]")))
            cmid = quiz_link.get_attribute("href").split("id=")[1].split("&")[0]
            
            driver.get(f"{BASE_URL}/course/modedit.php?update={cmid}&return=0")
            time.sleep(1.5)
            
            driver.execute_script("""
            document.querySelectorAll('fieldset.collapsed').forEach(f => f.classList.remove('collapsed'));
            document.querySelectorAll('a.fheader').forEach(a => { if (a.getAttribute('aria-expanded') === 'false') a.click(); });
            """)
            time.sleep(0.3)
            
            # Click Show More
            try:
                for btn in driver.find_elements(By.XPATH, "//a[contains(@class, 'moreless-toggler') or contains(text(), 'Show more')]"):
                    driver.execute_script("arguments[0].click();", btn)
            except: pass
            
            set_moodle_datetime(driver, "timeopen", task['Quiz_Start'])
            set_moodle_datetime(driver, "timeclose", task['Quiz_End'])
            
            # Subnet IP
            driver.execute_script("var el = document.getElementById('id_subnet'); if(el){ var c = el.closest('.form-group')||el.closest('.fitem'); if(c) c.style.display='flex'; el.style.display='block'; }")
            ip_field = wait.until(EC.presence_of_element_located((By.ID, "id_subnet")))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", ip_field)
            ip_field.clear()
            ip_field.send_keys(subnet_ips)
            if not ip_field.get_attribute("value"):
                driver.execute_script(f"document.getElementById('id_subnet').value = '{subnet_ips}';")
                
            save_btn = driver.find_element(By.ID, "id_submitbutton2")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_btn)
            save_btn.click()
            time.sleep(1.5)
            print(f"   [✅] SUCCESS: Configured {shortname}")
        except Exception as e:
            print(f"   [❌] FAILED: {shortname}: {e}")
            
    if close_at_end:
        driver.quit()

# --- MODULE 4: QUIZ RENAMER ---
def module_rename_quizzes(driver=None, wait=None):
    print("\n--- MODULE 4: QUIZ RENAMER BOT ---")
    schedule_file = "moodle_quiz_timing_schedule.csv"
    if not os.path.exists(schedule_file):
        print(f"[!] File '{schedule_file}' not found.")
        return
        
    tasks = []
    with open(schedule_file, 'r', encoding='utf-8') as f:
        tasks = list(csv.DictReader(f))
        
    close_at_end = False
    if driver is None:
        driver, wait = start_moodle_browser()
        close_at_end = True
        
    for idx, task in enumerate(tasks):
        shortname = task['Course_Shortname']
        print(f"[{idx+1}/{len(tasks)}] Renaming Quiz for {shortname}")
        try:
            driver.get(f"{BASE_URL}/course/search.php?search={shortname}")
            time.sleep(1)
            course_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'course/view.php?id=')]")))
            course_link.click()
            time.sleep(1)
            
            quiz_link = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'mod/quiz/view.php')]")))
            cmid = quiz_link.get_attribute("href").split("id=")[1].split("&")[0]
            
            driver.get(f"{BASE_URL}/course/modedit.php?update={cmid}&return=0")
            time.sleep(1)
            
            name_input = wait.until(EC.presence_of_element_located((By.ID, "id_name")))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", name_input)
            name_input.clear()
            name_input.send_keys(shortname)
            
            save_btn = driver.find_element(By.ID, "id_submitbutton2")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_btn)
            save_btn.click()
            time.sleep(1.5)
            print(f"   [✅] SUCCESS: Renamed quiz to {shortname}")
        except Exception as e:
            print(f"   [❌] FAILED: {shortname}: {e}")
            
    if close_at_end:
        driver.quit()

# --- MODULE 5: DEFAULTER AUDITOR ---
def module_audit_defaulters(driver=None, wait=None):
    print("\n--- MODULE 5: DEFAULTER FACULTY & EMPTY QUIZ AUDITOR ---")
    schedule_file = "moodle_quiz_timing_schedule.csv"
    roster_file = "end_spl.csv"
    
    staff_map = {}
    if os.path.exists(roster_file):
        df_roster = pd.read_csv(roster_file)
        for _, row in df_roster.iterrows():
            code = str(row.get('coursecode', '')).strip()
            if code and code not in staff_map:
                staff_map[code] = {
                    'staffname': str(row.get('staffname', '')).strip(),
                    'staffid': str(row.get('staffid', '')).strip()
                }
                
    tasks = []
    with open(schedule_file, 'r', encoding='utf-8') as f:
        tasks = list(csv.DictReader(f))
        
    close_at_end = False
    if driver is None:
        driver, wait = start_moodle_browser()
        close_at_end = True
        
    defaulters = []
    for idx, task in enumerate(tasks):
        shortname = task['Course_Shortname']
        code = task.get('Course_Code', shortname.split('_')[0])
        staff_info = staff_map.get(code, {'staffname': 'Unknown', 'staffid': 'Unknown'})
        
        print(f"[{idx+1}/{len(tasks)}] Auditing Quiz Status for {shortname}")
        try:
            driver.get(f"{BASE_URL}/course/search.php?search={shortname}")
            time.sleep(1)
            course_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'course/view.php?id=')]")))
            course_link.click()
            time.sleep(1)
            
            quiz_link = wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'mod/quiz/view.php')]")))
            quiz_url = quiz_link.get_attribute("href")
            cmid = quiz_url.split("id=")[1].split("&")[0]
            
            driver.get(quiz_url)
            time.sleep(1)
            page_src = driver.page_source.lower()
            
            is_empty = False
            if "no questions have been added" in page_src or "questions: 0" in page_src:
                is_empty = True
                
            driver.get(f"{BASE_URL}/mod/quiz/edit.php?cmid={cmid}")
            time.sleep(1)
            edit_src = driver.page_source.lower()
            if "total of marks: 0" in edit_src or "questions: 0" in edit_src:
                is_empty = True

            if is_empty:
                print(f"   [🚨 DEFAULTER] No questions! Faculty: {staff_info['staffname']} ({staff_info['staffid']})")
                defaulters.append({
                    'Course_Shortname': shortname,
                    'Course_Code': code,
                    'Faculty_Name': staff_info['staffname'],
                    'Faculty_ID': staff_info['staffid'],
                    'Status': 'EMPTY (No Questions Uploaded)',
                    'Quiz_URL': quiz_url
                })
            else:
                print(f"   [✅ OK] Questions present.")
        except Exception as e:
            print(f"   [!] Audit error on {shortname}: {e}")
            
    out_file = "defaulter_teachers_report.csv"
    if defaulters:
        pd.DataFrame(defaulters).to_csv(out_file, index=False)
        print(f"\n[🚨] AUDIT COMPLETE: Exported {len(defaulters)} defaulter faculty to '{out_file}'")
    else:
        print("\n[🎉] CONGRATULATIONS: All faculty members have uploaded questions!")
        
    if close_at_end:
        driver.quit()

# --- MODULE 6: FULL BOT SUITE RUNNER ---
def module_full_suite():
    print("\n--- MODULE 6: FULL END-TO-END AUTOMATION SUITE ---")
    driver, wait = start_moodle_browser()
    try:
        print("\n=== STEP 1: CONFIGURING QUIZ TIMINGS & SUBNET IPS ===")
        module_configure_timings(driver, wait)
        
        print("\n=== STEP 2: RENAMING QUIZZES ===")
        module_rename_quizzes(driver, wait)
        
        print("\n=== STEP 3: AUDITING DEFAULTER FACULTY ===")
        module_audit_defaulters(driver, wait)
        
        print("\n[🎉] FULL SUITE AUTOMATION SUCCESSFULLY COMPLETED!")
    finally:
        driver.quit()

# --- MAIN CONTROLLER LOOP ---
def main():
    while True:
        print_banner()
        print_menu()
        choice = input("Enter choice (0-6): ").strip()
        if choice == '1':
            module_process_roster()
        elif choice == '2':
            module_parse_pdf()
        elif choice == '3':
            module_configure_timings()
        elif choice == '4':
            module_rename_quizzes()
        elif choice == '5':
            module_audit_defaulters()
        elif choice == '6':
            module_full_suite()
        elif choice == '0':
            print("\nExiting Master Suite. Goodbye!\n")
            sys.exit(0)
        else:
            print("\n[!] Invalid choice. Please select 0 to 6.")
        input("\nPress ENTER to return to the main menu...")

if __name__ == "__main__":
    main()
