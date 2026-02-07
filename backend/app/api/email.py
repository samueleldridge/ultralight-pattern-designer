"""
Email API Endpoints

Endpoints:
- POST /api/email/send-test - Send test email
- POST /api/email/settings - Update email settings
- GET /api/email/status - Check email configuration
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from app.services.email_service import EmailService, EmailMessage, get_email_service
from app.services.email_templates import EmailTemplates
from app.middleware import get_current_user

router = APIRouter(prefix="/api/email", tags=["email"])


# Request Models
class TestEmailRequest(BaseModel):
    to: EmailStr
    template: str = "welcome"  # welcome, alert, weekly


class SendCustomEmailRequest(BaseModel):
    to: EmailStr
    subject: str
    html_body: str
    text_body: Optional[str] = None


class EmailSettings(BaseModel):
    provider: str  # sendgrid, aws_ses, smtp, console
    from_email: EmailStr
    from_name: str


@router.post("/send-test")
async def send_test_email(
    request: TestEmailRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a test email to verify configuration"""
    email_service = get_email_service()
    
    # Generate test content based on template
    if request.template == "welcome":
        html_body = EmailTemplates.welcome_email(
            user_name=request.to.split('@')[0],
            login_url="https://app.example.com/login"
        )
        subject = "Welcome to AI Analytics Platform"
    elif request.template == "alert":
        html_body = EmailTemplates.subscription_alert(
            user_name=request.to.split('@')[0],
            subscription_name="Test Alert",
            condition_met=True,
            rows_found=5,
            summary="Found 5 items matching your criteria",
            query_results={},
            action_url="https://app.example.com/alerts/123"
        )
        subject = "Test Alert: Subscription Notification"
    elif request.template == "weekly":
        html_body = EmailTemplates.weekly_report(
            user_name=request.to.split('@')[0],
            week_start="2024-01-01",
            week_end="2024-01-07",
            metrics={"revenue": "$125,000", "new_customers": 42},
            insights=["Revenue up 15% from last week", "Customer acquisition accelerating"],
            dashboard_url="https://app.example.com/dashboard"
        )
        subject = "Your Weekly Analytics Report"
    else:
        raise HTTPException(status_code=400, detail="Unknown template")
    
    message = EmailMessage(
        to=request.to,
        subject=subject,
        html_body=html_body
    )
    
    success = await email_service.send_email(message)
    
    if success:
        return {
            "status": "sent",
            "to": request.to,
            "template": request.template,
            "provider": email_service.provider.value
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to send email")


@router.post("/send-custom")
async def send_custom_email(
    request: SendCustomEmailRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a custom email (admin only)"""
    # TODO: Add admin check
    email_service = get_email_service()
    
    message = EmailMessage(
        to=request.to,
        subject=request.subject,
        html_body=request.html_body,
        text_body=request.text_body
    )
    
    success = await email_service.send_email(message)
    
    if success:
        return {"status": "sent", "to": request.to}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email")


@router.get("/status")
async def get_email_status(
    current_user: dict = Depends(get_current_user)
):
    """Get current email configuration status"""
    import os
    
    email_service = get_email_service()
    provider = email_service.provider
    
    config = {
        "provider": provider.value,
        "configured": False,
        "details": {}
    }
    
    if provider.value == "sendgrid":
        config["configured"] = bool(os.getenv("SENDGRID_API_KEY"))
        config["details"] = {
            "api_key_set": bool(os.getenv("SENDGRID_API_KEY")),
            "api_key_preview": os.getenv("SENDGRID_API_KEY", "")[:10] + "..." if os.getenv("SENDGRID_API_KEY") else None
        }
    elif provider.value == "aws_ses":
        config["configured"] = all([
            os.getenv("AWS_ACCESS_KEY_ID"),
            os.getenv("AWS_SECRET_ACCESS_KEY"),
            os.getenv("AWS_SES_REGION")
        ])
        config["details"] = {
            "access_key_set": bool(os.getenv("AWS_ACCESS_KEY_ID")),
            "secret_key_set": bool(os.getenv("AWS_SECRET_ACCESS_KEY")),
            "region": os.getenv("AWS_SES_REGION")
        }
    elif provider.value == "smtp":
        config["configured"] = bool(os.getenv("SMTP_HOST"))
        config["details"] = {
            "host": os.getenv("SMTP_HOST"),
            "port": os.getenv("SMTP_PORT", "587"),
            "tls": os.getenv("SMTP_USE_TLS", "true"),
            "user_set": bool(os.getenv("SMTP_USER"))
        }
    elif provider.value == "console":
        config["configured"] = True
        config["details"] = {"mode": "development - emails printed to console"}
    
    return config


@router.get("/templates")
async def list_email_templates(
    current_user: dict = Depends(get_current_user)
):
    """List available email templates"""
    return {
        "templates": [
            {
                "id": "welcome",
                "name": "Welcome Email",
                "description": "Sent to new users on signup"
            },
            {
                "id": "alert",
                "name": "Subscription Alert",
                "description": "Sent when subscription condition is met"
            },
            {
                "id": "weekly",
                "name": "Weekly Report",
                "description": "Weekly summary of analytics"
            },
            {
                "id": "insight",
                "name": "Proactive Insight",
                "description": "AI-generated insight notification"
            }
        ]
    }
