"""
Email Service for Notifications

Sends emails for:
- Subscription alerts (when conditions are met)
- Weekly/monthly reports
- Proactive insights
- System notifications

Supports multiple providers:
- SendGrid (recommended)
- AWS SES
- SMTP (generic)
"""

from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum
import os


class EmailProvider(str, Enum):
    SENDGRID = "sendgrid"
    AWS_SES = "aws_ses"
    SMTP = "smtp"
    CONSOLE = "console"  # For development - prints to console


@dataclass
class EmailAttachment:
    filename: str
    content: bytes
    content_type: str


@dataclass
class EmailMessage:
    to: str
    subject: str
    html_body: str
    text_body: Optional[str] = None
    from_name: str = "AI Analytics Platform"
    from_email: str = "noreply@aianalytics.com"
    attachments: Optional[List[EmailAttachment]] = None


class EmailService:
    """Service for sending emails"""
    
    def __init__(self, provider: Optional[EmailProvider] = None):
        self.provider = provider or self._detect_provider()
        self._client = None
    
    def _detect_provider(self) -> EmailProvider:
        """Auto-detect email provider from environment"""
        if os.getenv("SENDGRID_API_KEY"):
            return EmailProvider.SENDGRID
        elif os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SES_REGION"):
            return EmailProvider.AWS_SES
        elif os.getenv("SMTP_HOST"):
            return EmailProvider.SMTP
        else:
            return EmailProvider.CONSOLE
    
    def _get_client(self):
        """Lazy initialization of email client"""
        if self._client is not None:
            return self._client
        
        if self.provider == EmailProvider.SENDGRID:
            try:
                from sendgrid import SendGridAPIClient
                self._client = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
            except ImportError:
                raise ImportError("SendGrid not installed. Run: pip install sendgrid")
        
        elif self.provider == EmailProvider.AWS_SES:
            try:
                import boto3
                self._client = boto3.client(
                    'ses',
                    region_name=os.getenv("AWS_SES_REGION", "us-east-1"),
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
                )
            except ImportError:
                raise ImportError("Boto3 not installed. Run: pip install boto3")
        
        elif self.provider == EmailProvider.SMTP:
            import smtplib
            self._client = smtplib.SMTP(
                os.getenv("SMTP_HOST"),
                int(os.getenv("SMTP_PORT", "587"))
            )
        
        return self._client
    
    async def send_email(self, message: EmailMessage) -> bool:
        """Send an email"""
        try:
            if self.provider == EmailProvider.SENDGRID:
                return await self._send_sendgrid(message)
            elif self.provider == EmailProvider.AWS_SES:
                return await self._send_ses(message)
            elif self.provider == EmailProvider.SMTP:
                return await self._send_smtp(message)
            else:
                return await self._send_console(message)
        except Exception as e:
            print(f"Email send failed: {e}")
            return False
    
    async def _send_sendgrid(self, message: EmailMessage) -> bool:
        """Send via SendGrid"""
        from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition
        import base64
        
        mail = Mail(
            from_email=Email(message.from_email, message.from_name),
            to_emails=To(message.to),
            subject=message.subject,
            html_content=message.html_body
        )
        
        if message.text_body:
            mail.add_content(Content("text/plain", message.text_body))
        
        # Add attachments
        if message.attachments:
            for att in message.attachments:
                encoded = base64.b64encode(att.content).decode()
                attachment = Attachment()
                attachment.file_content = FileContent(encoded)
                attachment.file_name = FileName(att.filename)
                attachment.file_type = FileType(att.content_type)
                attachment.disposition = Disposition('attachment')
                mail.add_attachment(attachment)
        
        client = self._get_client()
        response = client.send(mail)
        
        return response.status_code == 202
    
    async def _send_ses(self, message: EmailMessage) -> bool:
        """Send via AWS SES"""
        client = self._get_client()
        
        msg = {
            'Source': f"{message.from_name} <{message.from_email}>",
            'Destination': {'ToAddresses': [message.to]},
            'Message': {
                'Subject': {'Data': message.subject},
                'Body': {
                    'Html': {'Data': message.html_body}
                }
            }
        }
        
        if message.text_body:
            msg['Message']['Body']['Text'] = {'Data': message.text_body}
        
        response = client.send_email(**msg)
        return 'MessageId' in response
    
    async def _send_smtp(self, message: EmailMessage) -> bool:
        """Send via SMTP"""
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = message.subject
        msg['From'] = f"{message.from_name} <{message.from_email}>"
        msg['To'] = message.to
        
        # Add body
        msg.attach(MIMEText(message.html_body, 'html'))
        if message.text_body:
            msg.attach(MIMEText(message.text_body, 'plain'))
        
        # Add attachments
        if message.attachments:
            for att in message.attachments:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(att.content)
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {att.filename}'
                )
                msg.attach(part)
        
        # Send
        with smtplib.SMTP(
            os.getenv("SMTP_HOST"),
            int(os.getenv("SMTP_PORT", "587"))
        ) as server:
            if os.getenv("SMTP_USE_TLS", "true").lower() == "true":
                server.starttls()
            if os.getenv("SMTP_USER"):
                server.login(
                    os.getenv("SMTP_USER"),
                    os.getenv("SMTP_PASSWORD")
                )
            server.sendmail(message.from_email, message.to, msg.as_string())
        
        return True
    
    async def _send_console(self, message: EmailMessage) -> bool:
        """Print email to console (for development)"""
        print("\n" + "="*70)
        print("📧 EMAIL (Console Mode)")
        print("="*70)
        print(f"To: {message.to}")
        print(f"From: {message.from_name} <{message.from_email}>")
        print(f"Subject: {message.subject}")
        print("-"*70)
        print(message.html_body[:500] + "..." if len(message.html_body) > 500 else message.html_body)
        print("="*70 + "\n")
        return True


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
