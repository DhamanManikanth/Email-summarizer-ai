import imaplib
import email
from email.header import decode_header
import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from transformers import pipeline
import torch

# CONFIGURATION
GMAIL_IMAP = 'imap.gmail.com'
EMAIL_ACCOUNT = ''  # <-- Your Gmail address
EMAIL_PASSWORD = ''    # <-- Your Gmail App Password
TIMEZONE = 'Asia/Kolkata'
SUMMARY_TIME = 20  # 8 PM

# Initialize summarizer
summarizer = pipeline('summarization', model='sshleifer/distilbart-cnn-12-6')

def fetch_today_emails():
    # Connect to Gmail
    mail = imaplib.IMAP4_SSL(GMAIL_IMAP)
    mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    mail.select('inbox')

    # Get today's date in required format
    tz = pytz.timezone(TIMEZONE)
    today = datetime.datetime.now(tz).strftime('%d-%b-%Y')
    result, data = mail.search(None, f'(SINCE "{today}")')
    email_ids = data[0].split()
    emails = []
    for eid in email_ids:
        _, msg_data = mail.fetch(eid, '(RFC822)')
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject, encoding = decode_header(msg['Subject'])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or 'utf-8')
                from_ = msg.get('From')
                body = ''
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        cdispo = str(part.get('Content-Disposition'))
                        if ctype == 'text/plain' and 'attachment' not in cdispo:
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                else:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                emails.append({'from': from_, 'subject': subject, 'body': body})
    mail.logout()
    return emails

def summarize_emails(emails):
    summaries = []
    for mail in emails:
        text = mail['body']
        if len(text.strip()) < 30:
            summary = text.strip()
        else:
            summary = summarizer(text[:1000], max_length=60, min_length=15, do_sample=False)[0]['summary_text']
        summaries.append({
            'from': mail['from'],
            'subject': mail['subject'],
            'summary': summary
        })
    return summaries

def send_summary_email(summary_list):
    if not summary_list:
        summary_body = 'No emails received today.'
    else:
        summary_body = ''
        for idx, s in enumerate(summary_list, 1):
            summary_body += f"{idx}. From: {s['from']}\nSubject: {s['subject']}\nSummary: {s['summary']}\n\n"
    # Compose email
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ACCOUNT
    msg['To'] = EMAIL_ACCOUNT
    msg['Subject'] = "Today's Email Summary"
    msg.attach(MIMEText(summary_body, 'plain'))
    # Send email via Gmail SMTP
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ACCOUNT, EMAIL_ACCOUNT, msg.as_string())
        print('Summary email sent successfully!')
    except Exception as e:
        print(f'Failed to send summary email: {e}')

def job():
    emails = fetch_today_emails()
    summaries = summarize_emails(emails)
    send_summary_email(summaries)

def schedule_summary():
    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    scheduler.add_job(job, 'cron', hour=SUMMARY_TIME, minute=0)
    scheduler.start()
    print(f"Scheduled daily email summary at {SUMMARY_TIME}:00.")
    try:
        while True:
            pass  # Keep the script running
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

import sys

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'now':
        # Run the summary and send email instantly
        job()
    else:
        schedule_summary()
