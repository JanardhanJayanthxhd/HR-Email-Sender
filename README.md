# Auto Email Sender

A Python application with a dark minimal UI for sending automated job application emails to HR departments.

## Features

- **Dark Minimal UI** using Tkinter
- **Multiple Email Providers**: Supports Gmail and Outlook (extensible architecture)
- **3 Email Template Variants**: Formal, Friendly Professional, and Concise
- **Resume Attachment**: Automatically attach your PDF resume
- **Dynamic Configuration**: Uses .env for credentials
- **Clean Code**: Follows SOLID principles with Google-style docstrings

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   - Copy `.env.example` to `.env`
   - Fill in your details:
     ```
     SENDER_EMAIL_PROVIDER=gmail
     SENDER_EMAIL=your_email@gmail.com
     SENDER_PASSWORD=your_app_password
     SENDER_NAME=Your Full Name
     ```

3. **For Gmail users:**
   - Enable 2-factor authentication
   - Generate an App Password: https://myaccount.google.com/apppasswords
   - Use the App Password in `SENDER_PASSWORD`

4. **Add your resume:**
   - Place your resume PDF in the `resume/` directory

## Usage

Run the application:
```bash
python app.py
```

Fill in the form:
- **HR Email**: Recipient's email address
- **Company**: Company name
- **Position**: Job position you're applying for
- **Skills**: Your key skills (comma-separated)
- **Experience**: Brief experience summary (e.g., "3 years in Python development")
- **Email Style**: Choose between Formal, Friendly, or Concise
- **Resume**: Browse and select your PDF resume

Click **Preview Email** to see the email before sending, or **Send Email** to send directly.

## Project Structure

```
auto_email_sender/
├── app.py                  # Main application with UI
├── email_sender.py         # Email sending logic
├── email_config.py         # Provider configurations (extensible)
├── email_templates.py      # Email template variants
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variable template
├── .env                   # Your credentials (not tracked)
├── resume/                # Place your PDF resume here
│   └── README.md
└── README.md
```

## Extending Email Providers

To add a new email provider:

```python
# In email_config.py
class NewProvider(EmailProvider):
    def get_smtp_config(self):
        return {
            'smtp_server': 'smtp.newprovider.com',
            'smtp_port': 587
        }

# Register it
EmailProviderFactory.register_provider('newprovider', NewProvider)
```

## Notes

- Subject line format: `Application {Your Name} - {Position}`
- All templates are professional and customizable
- Resume attachment is optional but recommended
# HR-Email-Sender
