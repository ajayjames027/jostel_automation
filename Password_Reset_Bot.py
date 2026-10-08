import urllib.request
import urllib.parse
import json
import sys

URL = "https://service.sjctni.edu/jostel/moodle/webservice/rest/server.php"
# Please ensure this token has admin/manager privileges to update users!
TOKEN = "20346d2c25c71285ffc0f147a3f9eab8" 

def print_hdr(text):
    print("\n" + "="*50)
    print(f" {text}")
    print("="*50)

def call_moodle(function, params):
    params['wstoken'] = TOKEN
    params['wsfunction'] = function
    params['moodlewsrestformat'] = 'json'
    
    encoded = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{URL}?{encoded}", headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        res = urllib.request.urlopen(req).read()
        return json.loads(res.decode('utf-8'))
    except Exception as e:
        print(f"[!] Network Error: {e}")
        return None

def reset_student_password():
    print_hdr("JOS-TEL HELP DESK: PASSWORD RESET MODULE")
    print("This module will forcibly reset a student's password to '12345' ")
    print("and flag their account to mandate a password change on next login.\n")
    
    while True:
        reg_no = input("Enter Student Register Number (or 'exit' to quit): ").strip()
        if reg_no.lower() == 'exit':
            break
        if not reg_no:
            continue
            
        print(f"[*] Looking up account for '{reg_no}'...")
        
        # 1. Fetch User ID by Registration Number (Username)
        fetch_params = {
            'field': 'username',
            'values[0]': reg_no.lower() # usernames in moodle are typically lowercase
        }
        
        users = call_moodle('core_user_get_users_by_field', fetch_params)
        
        if not users or len(users) == 0:
            print(f"[!] Error: Could not find any student with Registration Number '{reg_no}'.")
            continue
            
        user_id = users[0].get('id')
        user_name = users[0].get('fullname')
        
        print(f"[+] Found Student: {user_name} (Moodle ID: {user_id})")
        
        # 2. Update User Payload
        update_params = {
            'users[0][id]': user_id,
            'users[0][password]': '12345',
            # Moodle preference to force password change is typically 'auth_forcepasswordchange'
            'users[0][preferences][0][type]': 'auth_forcepasswordchange',
            'users[0][preferences][0][value]': '1'
        }
        
        print(f"[*] Dispatching reset command to Moodle core...")
        result = call_moodle('core_user_update_users', update_params)
        
        # 'core_user_update_users' returns None/null if successful, or an exception object if failed
        if result is None or (isinstance(result, list) and len(result) == 0):
            print(f"✅ SUCCESS! '{reg_no}' password is now '12345'.")
            print("=> The system will FORCE them to change this password when they next log in!\n")
        elif isinstance(result, dict) and 'exception' in result:
            print(f"❌ FAILED. Moodle returned an error: {result.get('message')}\n")
        else:
            # Sometimes empty list means success depending on moodle version
            print(f"✅ SUCCESS (Processed)! '{reg_no}' password is now '12345'.\n")

if __name__ == "__main__":
    reset_student_password()
