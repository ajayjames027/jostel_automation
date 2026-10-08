import urllib.request
import urllib.parse
import json

def test_api():
    url = "https://service.sjctni.edu/jostel/moodle/webservice/rest/server.php"
    token = "20346d2c25c71285ffc0f147a3f9eab8"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # We will try to call a non-existent function to sometimes trigger an error that reveals something,
    # but the best way is to see if we can call "core_webservice_get_site_info"
    # Actually, we can check if "mod_quiz" functions exist if there's an API for it, wait, Moodle WS 
    # doesn't natively allow listing functions easily without a specific call if enabled.
    
    # Let's try to see if "core_course_edit_module" exists
    params = urllib.parse.urlencode({
        'wstoken': token,
        'wsfunction': 'core_course_edit_module',
        'moodlewsrestformat': 'json',
        'action': 'update',
        'id': 1
    })
    
    req = urllib.request.Request(f"{url}?{params}", headers=headers)
    try:
        response_bytes = urllib.request.urlopen(req).read()
        res = json.loads(response_bytes.decode('utf-8'))
        print("core_course_edit_module response:", res)
    except Exception as e:
        print("HTTP Error:", e)

if __name__ == "__main__":
    test_api()
