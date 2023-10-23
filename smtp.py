import smtplib
import sqlite3
import threading
import random
from email.mime.text import MIMEText

class EmailSender:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_smtp(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT smtp FROM smtps WHERE user_id=?", (user_id,))
            smtps = cursor.fetchall()
            if smtps:
                return random.choice(smtps)[0]
            return None

    def remove_smtp(self, user_id, smtp):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM smtps WHERE user_id=? AND smtp=?", (user_id, smtp))
            conn.commit()

    def send_email(self, user_id, smtp, to_addr, subject, html_content):
        try:
            msg = MIMEText(html_content, 'html')
            msg['Subject'] = subject
            msg['From'] = smtp['sender']
            msg['To'] = to_addr

            with smtplib.SMTP(smtp['host'], smtp['port']) as server:
                server.login(smtp['username'], smtp['password'])
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            self.remove_smtp(user_id, smtp)
            return False

    def sender(self, user_id, task_id, subject, template, sender, leads):
        def threaded_send(to_addr):
            while True:
                smtp_info = self.get_smtp(user_id)
                if not smtp_info:
                    print(f"No valid SMTPs left for user {user_id}")
                    return
                if self.send_email(user_id, smtp_info, to_addr, subject, template):
                    break

        threads = [threading.Thread(target=threaded_send, args=(lead,)) for lead in leads]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

# Usage
db_path = 'your_database_path_here.db'
email_sender = EmailSender(db_path)
email_sender.sender(user_id, task_id, subject, template, sender, leads)
