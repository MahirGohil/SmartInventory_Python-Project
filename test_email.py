import smtplib
import ssl

HOST = "smtp.sendgrid.net"
PORT = 587
USER = "apikey"
PASSWORD = "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"

try:
    print("Connecting...")
    server = smtplib.SMTP(HOST, PORT, timeout=15)
    server.set_debuglevel(1)  # prints the full SMTP conversation
    print("Starting TLS...")
    server.starttls(context=ssl.create_default_context())
    print("Logging in...")
    server.login(USER, PASSWORD)
    print("SUCCESS — auth worked")
    server.quit()
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")