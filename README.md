# Email Summarizer AI Agent 📩🤖

This is an AI-powered Python script that:
- Connects to your Gmail inbox
- Reads all emails received today
- Summarizes them using HuggingFace's free DistilBART model
- Sends a structured summary email to you daily at 8 PM

## Features
✅ Free and local  
✅ Uses IMAP, SMTP, HuggingFace Transformers  
✅ Auto-scheduled with APScheduler  
✅ Clean, structured output

## Run it
```bash
pip install -r requirements.txt
python email_summarizer.py
