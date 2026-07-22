import os
import smtplib
from email.message import EmailMessage
from app.logger import logger  # Imports your centralized logger

def send_otp_email(receiver_email: str, otp: str):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    sender_email = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")

    msg = EmailMessage()
    msg.set_content(f"Your password reset code is: {otp}\n\nThis code will expire in 10 minutes.")
    msg["Subject"] = "Your Password Reset OTP"
    msg["From"] = sender_email
    msg["To"] = receiver_email
    
    # Fallback plain-text for older email clients
    plain_content = f"Your verification code is: {otp}\nThis code will expire in 10 minutes."
    msg.set_content(plain_content)

    # HTML Body (Significantly improves inbox placement)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f6f8; padding: 20px;">
        <div style="max-width: 500px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h2 style="color: #1a365d; margin-bottom: 10px;">Security Verification</h2>
            <p style="color: #4a5568; font-size: 15px;">Use the verification code below to reset your password. This code is valid for <strong>10 minutes</strong>.</p>
            <div style="text-align: center; margin: 25px 0;">
                <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #2b6cb0; background: #ebf8ff; padding: 10px 20px; border-radius: 6px; display: inline-block;">
                    {otp}
                </span>
            </div>
            <p style="color: #718096; font-size: 12px; margin-top: 30px;">If you did not request this code, please ignore this email or contact hospital IT support.</p>
        </div>
    </body>
    </html>
    """
    msg.add_alternative(html_content, subtype="html")

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
        
        # Secure audit logging
        logger.info(f"OTP email successfully dispatched to {receiver_email}")
        
    except smtplib.SMTPAuthenticationError:
        logger.critical("SMTP Authentication failed. Verify your email credentials in .env")
    except Exception as e:
        logger.error(f"SMTP execution failed for {receiver_email}. Error: {str(e)}")