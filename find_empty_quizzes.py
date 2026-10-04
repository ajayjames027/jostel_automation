import urllib.request
import urllib.parse
import json

def test_api():
    url = "https://service.sjctni.edu/jostel/moodle/webservice/rest/server.php"
    token = "20346d2c25c71285ffc0f147a3f9eab8"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # Let's get quizzes from all courses
    params = urllib.parse.urlencode({
        'wstoken': token,
        'wsfunction': 'mod_quiz_get_quizzes_by_courses',
        'moodlewsrestformat': 'json',
    })
    
    req = urllib.request.Request(f"{url}?{params}", headers=headers)
    response_bytes = urllib.request.urlopen(req).read()
    res = json.loads(response_bytes.decode('utf-8'))
    
    if 'exception' in res:
        print("Error:", res.get('message'))
        return
        
    quizzes = res.get('quizzes', [])
    print(f"Total quizzes found: {len(quizzes)}")
    if len(quizzes) > 0:
        print("Sample quiz structure:")
        print(json.dumps(quizzes[0], indent=2))

if __name__ == "__main__":
    test_api()
