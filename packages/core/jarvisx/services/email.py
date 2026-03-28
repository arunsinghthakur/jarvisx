import logging
import smtplib
import secrets
import hashlib
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from jarvisx.config.configs import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_FROM_EMAIL,
    SMTP_FROM_NAME,
    SMTP_USE_TLS,
    OTP_EXPIRY_MINUTES,
    OTP_MAX_ATTEMPTS,
)
from jarvisx.database.models import EmailVerification, User

logger = logging.getLogger(__name__)


def generate_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token: str, token_hash: str) -> bool:
    return hash_token(token) == token_hash


class EmailService:
    def __init__(self, db: Session):
        self.db = db
    
    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        if not SMTP_HOST:
            logger.info("[EmailService] SMTP not configured. Would send to %s: %s", to_email, subject)
            return True
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
            msg["To"] = to_email
            
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)
            
            if SMTP_USE_TLS:
                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10)
            
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            
            server.sendmail(SMTP_FROM_EMAIL, to_email, msg.as_string())
            server.quit()
            logger.info("[EmailService] Email sent successfully to %s", to_email)
            return True
        except Exception as e:
            logger.error("[EmailService] Failed to send email to %s: %s", to_email, e)
            return False
    
    def create_verification_token(self, user_id: str, organization_id: str) -> Tuple[str, EmailVerification]:
        self.db.query(EmailVerification).filter(
            EmailVerification.user_id == user_id,
            EmailVerification.organization_id == organization_id,
            EmailVerification.is_used == False
        ).update({"is_used": True})
        
        token = generate_token()
        
        verification = EmailVerification(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            user_id=user_id,
            otp_hash=hash_token(token),
            expires_at=datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES),
            is_used=False,
            attempts=0,
        )
        self.db.add(verification)
        self.db.commit()
        self.db.refresh(verification)
        
        return token, verification
    
    def send_verification_email(self, user: User, token: str, base_url: str = "http://localhost:5003") -> bool:
        subject = "Verify your email - JarvisX"
        
        from urllib.parse import urlencode
        verification_params = urlencode({"token": token})
        verification_link = f"{base_url}/verify-email?{verification_params}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .verify-btn {{ display: inline-block; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
                .verify-btn:hover {{ opacity: 0.9; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
                .link-text {{ word-break: break-all; font-size: 12px; color: #666; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Welcome to JarvisX!</h2>
                <p>Hi{' ' + user.first_name if user.first_name else ''},</p>
                <p>Please click the button below to verify your email and activate your account:</p>
                
                <div style="text-align: center;">
                    <a href="{verification_link}" class="verify-btn">Verify Email</a>
                </div>
                
                <p>This link will expire in {OTP_EXPIRY_MINUTES} minutes.</p>
                
                <p class="link-text">If the button doesn't work, copy and paste this link in your browser:<br/>
                <a href="{verification_link}">{verification_link}</a></p>
                
                <p>If you didn't request this, please ignore this email.</p>
                <div class="footer">
                    <p>This is an automated message from JarvisX. Please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(user.email, subject, html_content)
    
    def verify_email_token(self, token: str, mark_used: bool = False) -> Tuple[bool, str, Optional[User]]:
        token_hash = hash_token(token)
        
        verification = self.db.query(EmailVerification).filter(
            EmailVerification.otp_hash == token_hash,
            EmailVerification.is_used == False,
            EmailVerification.expires_at > datetime.utcnow()
        ).first()
        
        if not verification:
            return False, "Invalid or expired verification link. Please request a new one.", None
        
        user = self.db.query(User).filter(User.id == verification.user_id).first()
        
        if mark_used:
            verification.is_used = True
            if user:
                user.is_verified = True
                user.is_active = True
            self.db.commit()
        
        return True, "Token is valid.", user
    
    def activate_user_with_password(self, token: str, password_hash: str) -> Tuple[bool, str, Optional[User]]:
        token_hash = hash_token(token)
        
        verification = self.db.query(EmailVerification).filter(
            EmailVerification.otp_hash == token_hash,
            EmailVerification.is_used == False,
            EmailVerification.expires_at > datetime.utcnow()
        ).first()
        
        if not verification:
            return False, "Invalid or expired verification link. Please request a new one.", None
        
        user = self.db.query(User).filter(User.id == verification.user_id).first()
        if not user:
            return False, "User not found.", None
        
        verification.is_used = True
        user.password_hash = password_hash
        user.is_verified = True
        user.is_active = True
        self.db.commit()
        
        return True, "Account activated successfully.", user
    
    def resend_verification_email(self, user_id: str, base_url: str = "http://localhost:5003") -> Tuple[bool, str]:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False, "User not found."
        
        if user.is_verified:
            return False, "Email is already verified."
        
        token, _ = self.create_verification_token(user_id, user.organization_id)
        
        if self.send_verification_email(user, token, base_url):
            return True, "Verification email sent successfully."
        
        return False, "Failed to send verification email."
    
    def send_password_reset_email(self, user: User, token: str, base_url: str = "http://localhost:5003") -> bool:
        subject = "Reset your password - JarvisX"
        
        from urllib.parse import urlencode
        reset_params = urlencode({"token": token})
        reset_link = f"{base_url}/reset-password?{reset_params}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .reset-btn {{ display: inline-block; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
                .reset-btn:hover {{ opacity: 0.9; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
                .link-text {{ word-break: break-all; font-size: 12px; color: #666; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Password Reset Request</h2>
                <p>Hi{' ' + user.first_name if user.first_name else ''},</p>
                <p>We received a request to reset your password. Click the button below to set a new password:</p>
                
                <div style="text-align: center;">
                    <a href="{reset_link}" class="reset-btn">Reset Password</a>
                </div>
                
                <p>This link will expire in {OTP_EXPIRY_MINUTES} minutes.</p>
                
                <p class="link-text">If the button doesn't work, copy and paste this link in your browser:<br/>
                <a href="{reset_link}">{reset_link}</a></p>
                
                <p>If you didn't request this password reset, please ignore this email. Your password will remain unchanged.</p>
                <div class="footer">
                    <p>This is an automated message from JarvisX. Please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(user.email, subject, html_content)
    
    def create_password_reset_token(self, email: str, base_url: str) -> Tuple[bool, str]:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return True, "If an account exists with this email, a password reset link has been sent."
        
        if not user.is_active:
            return True, "If an account exists with this email, a password reset link has been sent."
        
        token, _ = self.create_verification_token(user.id, user.organization_id)
        
        if self.send_password_reset_email(user, token, base_url):
            return True, "If an account exists with this email, a password reset link has been sent."
        
        return False, "Failed to send password reset email."
    
    def reset_password(self, token: str, password_hash: str) -> Tuple[bool, str, Optional[User]]:
        token_hash = hash_token(token)
        
        verification = self.db.query(EmailVerification).filter(
            EmailVerification.otp_hash == token_hash,
            EmailVerification.is_used == False,
            EmailVerification.expires_at > datetime.utcnow()
        ).first()
        
        if not verification:
            return False, "Invalid or expired reset link. Please request a new one.", None
        
        user = self.db.query(User).filter(User.id == verification.user_id).first()
        if not user:
            return False, "User not found.", None
        
        verification.is_used = True
        user.password_hash = password_hash
        self.db.commit()
        
        return True, "Password reset successfully.", user
