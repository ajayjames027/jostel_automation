import pandas as pd
import re
from datetime import datetime

def slugify(text):
    if not text:
        return ''
    text = str(text)
    return re.sub(r'[^a-zA-Z0-9]', '', text)[:10]

def parse_time_part(t_str):
    # cleans up things like " 9:45am " or " 9 am"
    t_str = t_str.strip().lower().replace(" ", "")
    # extract hours, minutes and am/pm
    m = re.match(r'(\d+)(?::(\d+))?(am|pm)', t_str)
    if not m:
        return None
    h = int(m.group(1))
    mn = int(m.group(2)) if m.group(2) else 0
    ampm = m.group(3)
    
    if ampm == 'pm' and h != 12:
        h += 12
    if ampm == 'am' and h == 12:
        h = 0
    return f"{h:02d}:{mn:02d}:00"

def parse_datetime(date_str, time_str):
    try:
        parts = time_str.split('-')
        if len(parts) != 2:
            return None
            
        start_t = parse_time_part(parts[0])
        end_t = parse_time_part(parts[1])
        
        d = datetime.strptime(date_str, "%d.%m.%Y").strftime("%Y-%m-%d")
        
        if start_t and end_t:
            return f"{d} {start_t}", f"{d} {end_t}"
        return None
    except Exception as e:
        print(f"Error parsing: {date_str} {time_str} - {e}")
        return None

try:
    # Preload actual shortnames from the initial upload CSV
    existing_courses = {}
    csv_df = pd.read_csv('moodle_course_upload_ready_v2.csv')
    for idx, r in csv_df.iterrows():
        sn = str(r['shortname'])
        cc = sn.split('_')[0]
        st = sn.split('_')[-1]
        existing_courses[f"{cc}_{st}"] = sn
        
    df = pd.read_excel('NPTEL Alternate Final Exam Schedule- course code, name, dno, staff.xlsx', header=None)
    data = df.fillna("").values.tolist()
    
    courses = {}
    current_start = None
    current_end = None
    
    for row in data:
        col1 = str(row[1]).strip()
        col2 = str(row[2]).strip()
        
        if re.match(r'\d{2}\.\d{2}\.\d{4}', col1):
            if '-' in col2 and ('am' in col2.lower() or 'pm' in col2.lower()):
                parsed = parse_datetime(col1, col2)
                if parsed:
                    current_start, current_end = parsed
        
        course_code = str(row[1]).strip()
        staff = str(row[4]).strip()
        
        if course_code != '' and course_code != 'Course Code' and not re.match(r'\d{2}\.\d{2}\.\d{4}', course_code):
            staff_slug = slugify(staff)
            key = f"{course_code}_{staff_slug}"
            
            # Map to the REAL shortname (with Shift) if possible
            real_shortname = existing_courses.get(key, f"{course_code}__{staff_slug}")
            
            if real_shortname not in courses:
                courses[real_shortname] = {
                    'shortname': real_shortname,
                    'startdate': current_start or '',
                    'enddate': current_end or ''
                }
                
    out_df = pd.DataFrame(courses.values())
    out_df.to_csv('moodle_course_timing_update.csv', index=False)
    print(f"Successfully generated moodle_course_timing_update.csv with {len(out_df)} unique courses mapped to their timings.")
    
except Exception as e:
    print(f"Error: {e}")
