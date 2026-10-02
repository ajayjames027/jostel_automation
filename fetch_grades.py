import urllib.request
import urllib.parse
import json

def fetch_grades_from_quiz(cmid, token):
    # Base endpoint for Moodle Web Services API
    url = "https://service.sjctni.edu/jostel/moodle/webservice/rest/server.php"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    print(f"Step 1: Looking up exact Quiz ID for URL tag '?id={cmid}'...")
    params = urllib.parse.urlencode({
        'wstoken': token,
        'wsfunction': 'core_course_get_course_module',
        'moodlewsrestformat': 'json',
        'cmid': cmid
    })
    
    try:
        req = urllib.request.Request(f"{url}?{params}", headers=headers)
        response_bytes = urllib.request.urlopen(req).read()
        res = json.loads(response_bytes.decode('utf-8'))
        
        if 'exception' in res:
            print("Error connecting to Moodle:", res.get('message'))
            return
            
        # Moodle URLs use the 'course module' ID. We must trace it to the 'instance' ID for quizzes.
        quiz_id = res['cm']['instance']
        print(f"-> Success! Actual Quiz ID in database is: {quiz_id}\n")
        
        print(f"Step 2: Pulling grades directly into Python...")
        grade_params = urllib.parse.urlencode({
            'wstoken': token,
            'wsfunction': 'mod_quiz_get_user_grades',
            'moodlewsrestformat': 'json',
            'quizid': quiz_id
        })
        
        grade_req = urllib.request.Request(f"{url}?{grade_params}", headers=headers)
        grade_res = json.loads(urllib.request.urlopen(grade_req).read().decode('utf-8'))
        
        if 'exception' in grade_res:
            print("Error fetching grades:", grade_res.get('message'))
            return
            
        print("\n------- REPORT -------")
        grades = grade_res.get('grades', [])
        
        if not grades:
            print("No grades available yet. The quiz might not be graded completely.")
        else:
            print(f"Total students graded: {len(grades)}")
            for g in grades:
                # You can map userid to reg number via a separate API call later
                print(f"User ID: {g['userid']}  |  Grade: {g['grade']}")
                
    except urllib.error.HTTPError as e:
        print(f"\n[HTTP Error] {e.code}: {e.reason}")
        print("Note: The Moodle server might be temporarily down or blocking automated API calls.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    TOKEN = "20346d2c25c71285ffc0f147a3f9eab8"
    
    # Change URL_ID to match whatever is at the end of your browser URL: .../report.php?id=XXXXX
    URL_ID = 13199 
    
    fetch_grades_from_quiz(URL_ID, TOKEN)
