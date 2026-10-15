#!/usr/bin/env python3
"""
JosTEL Moodle Master Backup Vault & Date-Wise Archival Engine
St. Joseph's College (Autonomous), Tiruchirappalli

Automated command-line engine to extract, archive, and organize:
1. Question Papers (Aiken .txt and Moodle XML format)
2. Student Grades & Scores (CSV & Summary)
3. Enrolled Student Rosters
4. Course Syllabus Structure (JSON)
5. Consolidated Master Backup Manifest Index

Usage:
  python moodle_master_backup_vault.py --category 962
  python moodle_master_backup_vault.py --all
  python moodle_master_backup_vault.py --date 15102026
  python moodle_master_backup_vault.py --course 4599
"""

import sys
import os
import re
import json
import ssl
import time
import argparse
import datetime
import urllib.request
import urllib.parse
import zipfile

# Ensure UTF-8 stdout on Windows terminals
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Moodle API Configuration
MOODLE_URL = 'https://service.sjctni.edu/jostel/moodle'
API_TOKEN = '20346d2c25c71285ffc0f147a3f9eab8'

# SSL Context
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def api_request(wsfunction, params=None):
    """Execute a REST Web Service call to Moodle."""
    url = f"{MOODLE_URL.rstrip('/')}/webservice/rest/server.php"
    payload = {
        'wstoken': API_TOKEN,
        'wsfunction': wsfunction,
        'moodlewsrestformat': 'json'
    }
    if params:
        payload.update(params)
    
    data = urllib.parse.urlencode(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=30) as resp:
            raw = resp.read().decode('utf-8')
            res = json.loads(raw)
            if isinstance(res, dict) and res.get('exception'):
                raise RuntimeError(f"{res.get('exception')}: {res.get('message')}")
            return res
    except Exception as e:
        # print(f"API Error [{wsfunction}]: {e}")
        return None

def clean_filename(name):
    """Sanitize strings for filesystem safety."""
    return re.sub(r'[\/\\:*?"<>|]', '_', str(name or 'item')).strip()[:60]

def extract_date_code(shortname, startdate=None):
    """Extract a standard YYYY-MM-DD date tag from course shortname or timestamp."""
    sn = str(shortname or '')
    # Check for _15102026 pattern
    m = re.search(r'_(\d{8})', sn)
    if m:
        raw = m.group(1)
        return f"{raw[4:8]}-{raw[2:4]}-{raw[0:2]}"
    
    # Check for _16.10.2026 pattern
    m2 = re.search(r'_(\d{2})\.(\d{2})\.(\d{4})', sn)
    if m2:
        return f"{m2.group(3)}-{m2.group(2)}-{m2.group(1)}"
    
    if startdate and int(startdate) > 10000000:
        return datetime.datetime.fromtimestamp(int(startdate)).strftime('%Y-%m-%d')
    
    return 'Undated_Schedule'

def parse_question_html(html, slot=1, maxmark=1):
    """Parse HTML of a question into structured stem, options, and answer."""
    # Question text
    m_q = re.search(r'<div class="qtext">([\s\S]*?)</div>\s*<fieldset', html)
    raw_q = m_q.group(1) if m_q else ''
    clean_q = re.sub(r'<[^>]+>', '', raw_q).strip() if raw_q else f"Question {slot}"

    # Right answer text
    m_ans = re.search(r'class="rightanswer">([\s\S]*?)</div>', html)
    right_text = ''
    if m_ans:
        right_text = re.sub(r'<[^>]+>', '', m_ans.group(1)).replace('The correct answer is:', '').strip()

    # Options
    options = {}
    opt_matches = re.findall(r'<div class="flex-fill ml-1">([\s\S]*?)</div>', html)
    correct_letter = ''
    
    for i, opt in enumerate(opt_matches):
        if i >= 8: break
        letter = chr(65 + i)
        clean_opt = re.sub(r'<[^>]+>', '', opt).strip()
        # Clean redundant a. or 1.
        clean_opt = re.sub(r'^[a-z]\s*[\.\)]\s+', '', clean_opt, flags=re.I)
        options[letter] = clean_opt
        
        if right_text and clean_opt.lower() == right_text.lower():
            correct_letter = letter

    # Check for .correct class
    if not correct_letter:
        c_m = re.search(r'class="r(\d)\s+correct"', html)
        if c_m:
            c_idx = int(c_m.group(1))
            if c_idx < len(options):
                correct_letter = chr(65 + c_idx)

    return {
        'id': slot,
        'plain_text': clean_q,
        'html_text': raw_q or f"<p>{clean_q}</p>",
        'options': options,
        'answer': correct_letter or 'A',
        'marks': maxmark or 1
    }

def extract_quiz_questions(quiz_id):
    """Retrieve all questions from a quiz using attempt review / on-demand preview attempt."""
    attempt_ids = []
    
    # 1. Admin attempt check
    admin_att = api_request('mod_quiz_get_user_attempts', {'quizid': quiz_id, 'status': 'all', 'userid': 2})
    if admin_att and admin_att.get('attempts'):
        attempt_ids.append(admin_att['attempts'][-1]['id'])
    
    # 2. On-demand attempt via mod_quiz_start_attempt
    if not attempt_ids:
        start_res = api_request('mod_quiz_start_attempt', {'quizid': quiz_id})
        if start_res and start_res.get('attempt'):
            new_id = start_res['attempt']['id']
            api_request('mod_quiz_process_attempt', {'attemptid': new_id, 'finishattempt': 1})
            attempt_ids.append(new_id)

    if not attempt_ids:
        return []

    questions = []
    for att_id in attempt_ids[:2]:
        api_request('mod_quiz_process_attempt', {'attemptid': att_id, 'finishattempt': 1})
        rev = api_request('mod_quiz_get_attempt_review', {'attemptid': att_id, 'page': -1})
        if rev and rev.get('questions'):
            for q_item in rev['questions']:
                parsed = parse_question_html(q_item.get('html', ''), q_item.get('slot', 1), q_item.get('maxmark', 1))
                if parsed['plain_text']:
                    questions.append(parsed)
    return questions

def run_vault_backup(category_id=None, filter_date=None, target_course_id=None, output_dir='./JosTEL_Vault_Backups', make_zip=True):
    """Main backup orchestrator."""
    start_time = time.time()
    now_stamp = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    backup_root = os.path.abspath(output_dir)
    os.makedirs(backup_root, exist_ok=True)

    print("=" * 70)
    print(" 🛡️  JosTEL Moodle Master Backup Vault & Date-Wise Archival Engine")
    print(f" 🕒  Run Timestamp : {now_stamp}")
    print(f" 📂  Output Root   : {backup_root}")
    print("=" * 70)

    # 1. Load courses
    print("📡 Fetching registered course lists from Moodle API...")
    all_courses = api_request('core_course_get_courses')
    if not all_courses:
        print("❌ Error: Could not retrieve courses from Moodle.")
        return

    courses = [c for c in all_courses if c.get('id') != 1]

    # Filter by category
    if category_id:
        courses = [c for c in courses if str(c.get('category')) == str(category_id)]
        print(f"📌 Filtered to Category #{category_id}: {len(courses)} courses found.")

    # Filter by specific course
    if target_course_id:
        courses = [c for c in courses if str(c.get('id')) == str(target_course_id)]
        print(f"📌 Filtered to Single Course #{target_course_id}: {len(courses)} courses found.")

    # Filter by date code
    if filter_date:
        term = filter_date.strip().lower()
        courses = [c for c in courses if term in str(c.get('shortname', '')).lower() or term in extract_date_code(c.get('shortname'), c.get('startdate')).lower()]
        print(f"📌 Filtered by Date Code '{filter_date}': {len(courses)} courses matched.")

    total_courses = len(courses)
    if total_courses == 0:
        print("⚠️ No courses matched the specified criteria.")
        return

    print(f"🚀 Starting archival dump for {total_courses} courses...\n")

    manifest_rows = []
    total_quizzes = 0
    total_questions = 0
    total_grades = 0
    total_files = 0

    for idx, c in enumerate(courses, start=1):
        cid = c.get('id')
        shortname = c.get('shortname', f"Course_{cid}")
        fullname = c.get('fullname', '')
        date_code = extract_date_code(shortname, c.get('startdate'))

        # Date-wise folder hierarchy: Output/YYYY-MM-DD/CourseFolder
        course_dir_name = f"{clean_filename(shortname)}_{cid}"
        dest_folder = os.path.join(backup_root, date_code, course_dir_name)
        os.makedirs(dest_folder, exist_ok=True)

        manifest_item = {
            'S.No': idx,
            'Course ID': cid,
            'Course Code': shortname,
            'Full Name': fullname,
            'Category ID': c.get('category'),
            'Date Code': date_code,
            'Quizzes': 0,
            'Questions Dumped': 0,
            'Students Enrolled': 0,
            'Students Graded': 0,
            'Average Grade': 0,
            'Archived At': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        print(f"[{idx}/{total_courses}] Processing '{shortname}' (ID: {cid})...")

        # A. Course Structure JSON
        try:
            contents = api_request('core_course_get_contents', {'courseid': cid})
            with open(os.path.join(dest_folder, 'Course_Hierarchy_Structure.json'), 'w', encoding='utf-8') as f:
                json.dump({'course': c, 'sections': contents}, f, indent=2)
            total_files += 1
        except Exception:
            pass

        # B. Enrolled Students Roster (CSV)
        enrolled_users = api_request('core_enrol_get_enrolled_users', {'courseid': cid}) or []
        manifest_item['Students Enrolled'] = len(enrolled_users)
        if enrolled_users:
            roster_file = os.path.join(dest_folder, 'Enrolled_Student_Roster.csv')
            with open(roster_file, 'w', encoding='utf-8', newline='') as f:
                f.write("S.No,Moodle User ID,Register Number,Student Full Name,Email,Roles\n")
                for uidx, u in enumerate(enrolled_users, start=1):
                    roles = "; ".join([r.get('shortname', '') for r in u.get('roles', [])])
                    f.write(f'{uidx},{u.get("id")},"{u.get("username")}","{u.get("fullname")}","{u.get("email")}","{roles}"\n')
            total_files += 1

        # C. Quizzes & Question Papers
        q_res = api_request('mod_quiz_get_quizzes_by_courses', {'courseids[0]': cid})
        quizzes = q_res.get('quizzes', []) if q_res else []
        manifest_item['Quizzes'] = len(quizzes)
        total_quizzes += len(quizzes)

        q_count = 0
        for qz in quizzes:
            qid = qz.get('id')
            qname = clean_filename(qz.get('name'))
            qp = extract_quiz_questions(qid)
            if qp:
                q_count += len(qp)
                # 1. Aiken File
                aiken_file = os.path.join(dest_folder, f"QP_Quiz_{qid}_{qname}_Aiken.txt")
                with open(aiken_file, 'w', encoding='utf-8') as f:
                    for item in qp:
                        f.write(f"{item['plain_text']}\n")
                        for ltr, text in item['options'].items():
                            f.write(f"{ltr}. {text}\n")
                        f.write(f"ANSWER: {item['answer']}\n\n")
                
                # 2. Moodle XML File
                xml_file = os.path.join(dest_folder, f"QP_Quiz_{qid}_{qname}_Moodle.xml")
                with open(xml_file, 'w', encoding='utf-8') as f:
                    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<quiz>\n')
                    for item in qp:
                        f.write(f'  <question type="multichoice">\n    <name><text>Q{item["id"]}</text></name>\n')
                        f.write(f'    <questiontext format="html"><text><![CDATA[{item["html_text"]}]]></text></questiontext>\n')
                        f.write(f'    <defaultgrade>{item["marks"]}</defaultgrade>\n    <single>true</single>\n    <shuffleanswers>true</shuffleanswers>\n')
                        for ltr, text in item['options'].items():
                            fraction = '100' if item['answer'] == ltr else '0'
                            f.write(f'    <answer fraction="{fraction}" format="html"><text><![CDATA[<p>{text}</p>]]></text></answer>\n')
                        f.write('  </question>\n')
                    f.write('</quiz>\n')
                total_files += 2

        manifest_item['Questions Dumped'] = q_count
        total_questions += q_count

        # D. Student Grades CSV
        gr_res = api_request('gradereport_user_get_grade_items', {'courseid': cid})
        usergrades = gr_res.get('usergrades', []) if gr_res else []
        if usergrades:
            grades_file = os.path.join(dest_folder, f"Grades_Course_{cid}_{clean_filename(shortname)}.csv")
            scored_count = 0
            total_score = 0.0
            with open(grades_file, 'w', encoding='utf-8', newline='') as f:
                f.write("S.No,Moodle User ID,Register Number,Student Full Name,Email,Score,Max Grade,Submission Date,Feedback\n")
                for gidx, ug in enumerate(usergrades, start=1):
                    uid = ug.get('userid')
                    u_match = next((u for u in enrolled_users if u.get('id') == uid), {})
                    score_val = None
                    max_grade = 100.0
                    sub_date = ''
                    feedback = ''
                    for gi in ug.get('gradeitems', []):
                        if gi.get('itemtype') == 'course' or gi.get('itemmodule') == 'quiz':
                            if gi.get('graderaw') is not None:
                                try:
                                    score_val = float(gi.get('graderaw'))
                                    max_grade = float(gi.get('grademax') or 100)
                                    if gi.get('gradedatesubmitted'):
                                        sub_date = datetime.datetime.fromtimestamp(int(gi['gradedatesubmitted'])).strftime('%Y-%m-%d %H:%M:%S')
                                    feedback = str(gi.get('feedback') or '').replace('\n', ' ')
                                except Exception:
                                    pass

                    if score_val is not None:
                        scored_count += 1
                        total_score += score_val
                        score_str = str(score_val)
                    else:
                        score_str = "Absent / Unattempted"

                    f.write(f'{gidx},{uid},"{u_match.get("username", f"User_{uid}")}","{ug.get("userfullname")}","{u_match.get("email", "")}",{score_str},{max_grade},"{sub_date}","{feedback}"\n')

            manifest_item['Students Graded'] = scored_count
            manifest_item['Average Grade'] = round(total_score / scored_count, 2) if scored_count > 0 else 0
            total_grades += scored_count
            total_files += 1

        manifest_rows.append(manifest_item)
        print(f"   -> [OK] Done: {q_count} Qs, {manifest_item.get('Students Graded', 0)} grades, {manifest_item.get('Students Enrolled', 0)} enrolled.\n")

    # 4. Master Backup Manifest CSV
    manifest_csv_path = os.path.join(backup_root, f"Master_Backup_Manifest_Index_{now_stamp}.csv")
    with open(manifest_csv_path, 'w', encoding='utf-8', newline='') as f:
        headers = list(manifest_rows[0].keys())
        f.write(",".join(headers) + "\n")
        for row in manifest_rows:
            vals = [f'"{v}"' if isinstance(v, str) and ',' in v else str(v) for v in row.values()]
            f.write(",".join(vals) + "\n")

    total_files += 1

    # 5. Optional Zip Compilation
    zip_path = None
    if make_zip:
        zip_path = os.path.join(backup_root, f"JosTEL_Moodle_Master_Backup_{now_stamp}.zip")
        print(f"📦 Compressing into master archive: {zip_path}...")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
            for root, dirs, files in os.walk(backup_root):
                for file in files:
                    full_p = os.path.join(root, file)
                    if full_p == zip_path: continue
                    rel_p = os.path.relpath(full_p, backup_root)
                    z.write(full_p, rel_p)
        print(f"📦 Zip compression completed. Size: {round(os.path.getsize(zip_path) / (1024*1024), 2)} MB")

    elapsed = round(time.time() - start_time, 2)
    print("=" * 70)
    print(" 🎉 MASTER VAULT BACKUP COMPLETED SUCCESSFULLY")
    print(f" ⏱️  Elapsed Time       : {elapsed} seconds")
    print(f" 📁  Courses Backed Up  : {total_courses}")
    print(f" 📝  Quizzes Processed  : {total_quizzes}")
    print(f" ❓  Questions Archived : {total_questions}")
    print(f" 🎓  Grades Dumped      : {total_grades}")
    print(f" 📄  Total Files Saved  : {total_files}")
    print(f" 📊  Master Manifest    : {manifest_csv_path}")
    if zip_path:
        print(f" 📦  Master Zip Archive : {zip_path}")
    print("=" * 70)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="JosTEL Moodle Date-Wise Backup Vault Engine")
    parser.add_argument('--category', type=str, default=None, help="Filter by Moodle Category ID (e.g. 962)")
    parser.add_argument('--date', type=str, default=None, help="Filter by Exam Date Code (e.g. 15102026, 16102026)")
    parser.add_argument('--course', type=int, default=None, help="Back up single Course ID (e.g. 4599)")
    parser.add_argument('--all', action='store_true', help="Back up all courses across entire Moodle")
    parser.add_argument('--output', type=str, default='./JosTEL_Vault_Backups', help="Target output directory")
    parser.add_argument('--no-zip', action='store_true', help="Skip zip file generation")

    args = parser.parse_args()

    # Default to category 962 if no specific filter provided
    target_cat = args.category
    if not args.all and not args.date and not args.course and not target_cat:
        target_cat = '962'

    run_vault_backup(
        category_id=target_cat if not args.all else None,
        filter_date=args.date,
        target_course_id=args.course,
        output_dir=args.output,
        make_zip=not args.no_zip
    )
