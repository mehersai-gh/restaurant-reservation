import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Load environment variables
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "mehersai133@gmail.com"#os.getenv("SMTP_EMAIL")
EMAIL_PASSWORD = "btcu durb flrk rhcl"#os.getenv("SMTP_PASSWORD")

# Base directory for email templates
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "email_templates")

def load_email_template(template_name, **kwargs):
    """Loads an email template and replaces placeholders with provided values."""
    template_path = os.path.join(TEMPLATES_DIR, f"{template_name}.html")
    
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Email template '{template_name}' not found.")

    with open(template_path, "r", encoding="utf-8") as file:
        template_content = file.read()

    # Replace placeholders with actual values
    for key, value in kwargs.items():
        template_content = template_content.replace(f"{{{{ {key} }}}}", str(value))

    return template_content

def send_email(to_email, usage, **kwargs):
    """Send an email using the configured SMTP server, loading templates dynamically."""
    try:
        # Load email content based on usage type
        body = load_email_template(usage, **kwargs)
        subject = "Registration Successful!" if usage == "register" else "Notification from Our Service"

        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))

        # Connect to SMTP server
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())

        print(f"✅ Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False
