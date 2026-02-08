"""
Email Templates for Notifications
"""

from typing import Dict, Any
from datetime import datetime


class EmailTemplates:
    """HTML email templates"""
    
    @staticmethod
    def base_template(content: str, title: str = "AI Analytics Platform") -> str:
        """Base email template with styling"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    border-radius: 12px;
                    padding: 32px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 32px;
                    padding-bottom: 24px;
                    border-bottom: 1px solid #eee;
                }}
                .logo {{
                    font-size: 24px;
                    font-weight: 600;
                    color: #6366f1;
                }}
                .content {{
                    margin: 24px 0;
                }}
                .button {{
                    display: inline-block;
                    background: #6366f1;
                    color: white;
                    text-decoration: none;
                    padding: 12px 24px;
                    border-radius: 8px;
                    margin: 16px 0;
                    font-weight: 500;
                }}
                .footer {{
                    margin-top: 32px;
                    padding-top: 24px;
                    border-top: 1px solid #eee;
                    font-size: 12px;
                    color: #666;
                    text-align: center;
                }}
                .highlight {{
                    background: #eef2ff;
                    padding: 16px;
                    border-radius: 8px;
                    margin: 16px 0;
                    border-left: 4px solid #6366f1;
                }}
                .metric {{
                    font-size: 32px;
                    font-weight: 600;
                    color: #6366f1;
                    margin: 8px 0;
                }}
                .alert {{
                    background: #fef3c7;
                    border-left: 4px solid #f59e0b;
                    padding: 16px;
                    border-radius: 8px;
                    margin: 16px 0;
                }}
                .success {{
                    background: #d1fae5;
                    border-left: 4px solid #10b981;
                    padding: 16px;
                    border-radius: 8px;
                    margin: 16px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🤖 AI Analytics</div>
                </div>
                <div class="content">
                    {content}
                </div>
                <div class="footer">
                    <p>You're receiving this because you have an active subscription in AI Analytics Platform.</p>
                    <p><a href="{{unsubscribe_url}}">Manage notification preferences</a></p>
                </div>
            </div>
        </body>
        </html>
        """
    
    @classmethod
    def subscription_alert(
        cls,
        user_name: str,
        subscription_name: str,
        condition_met: bool,
        rows_found: int,
        summary: str,
        query_results: Any,
        action_url: str
    ) -> str:
        """Template for subscription alert emails"""
        
        status_class = "alert" if condition_met else "success"
        status_emoji = "⚠️" if condition_met else "✅"
        status_text = "Condition Met" if condition_met else "Check Complete"
        
        content = f"""
            <h2>Hi {user_name},</h2>
            
            <p>Your subscription <strong>"{subscription_name}"</strong> has been checked.</p>
            
            <div class="{status_class}">
                <strong>{status_emoji} {status_text}</strong>
                <div class="metric">{rows_found}</div>
                <p>{summary}</p>
            </div>
            
            <div class="highlight">
                <p><strong>Would you like to explore this data?</strong></p>
                <p>Click below to dive into the results and see detailed analysis.</p>
            </div>
            
            <center>
                <a href="{action_url}" class="button">View Results</a>
            </center>
            
            <p style="font-size: 12px; color: #666; margin-top: 24px;">
                This alert was triggered at {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
            </p>
        """
        
        return cls.base_template(content, f"Alert: {subscription_name}")
    
    @classmethod
    def weekly_report(
        cls,
        user_name: str,
        week_start: str,
        week_end: str,
        metrics: Dict[str, Any],
        insights: List[str],
        dashboard_url: str
    ) -> str:
        """Template for weekly summary emails"""
        
        insights_html = "\n".join([
            f'<li style="margin: 8px 0;">💡 {insight}</li>' 
            for insight in insights
        ])
        
        content = f"""
            <h2>Hi {user_name},</h2>
            
            <p>Here's your weekly analytics summary for <strong>{week_start} - {week_end}</strong>:</p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 24px 0;">
                <div class="highlight" style="text-align: center;">
                    <div style="font-size: 12px; color: #666;">Revenue</div>
                    <div class="metric">{metrics.get('revenue', 'N/A')}</div>
                </div>
                <div class="highlight" style="text-align: center;">
                    <div style="font-size: 12px; color: #666;">New Customers</div>
                    <div class="metric">{metrics.get('new_customers', 'N/A')}</div>
                </div>
            </div>
            
            <h3>Key Insights</h3>
            <ul style="padding-left: 20px;">
                {insights_html}
            </ul>
            
            <center>
                <a href="{dashboard_url}" class="button">View Full Dashboard</a>
            </center>
        """
        
        return cls.base_template(content, "Your Weekly Analytics Report")
    
    @classmethod
    def proactive_insight(
        cls,
        user_name: str,
        insight_title: str,
        insight_description: str,
        suggested_query: str,
        priority: str,
        explore_url: str
    ) -> str:
        """Template for proactive insight emails"""
        
        priority_colors = {
            "urgent": ("#dc2626", "🔴"),
            "high": ("#f59e0b", "🟠"),
            "medium": ("#6366f1", "🔵"),
            "low": ("#6b7280", "⚪")
        }
        
        color, emoji = priority_colors.get(priority, ("#6366f1", "🔵"))
        
        content = f"""
            <h2>Hi {user_name},</h2>
            
            <p>We noticed something that might interest you:</p>
            
            <div class="highlight" style="border-left-color: {color};">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-size: 24px;">{emoji}</span>
                    <strong style="color: {color}; text-transform: uppercase; font-size: 12px;">
                        {priority} Priority
                    </strong>
                </div>
                <h3 style="margin-top: 8px;">{insight_title}</h3>
                <p>{insight_description}</p>
            </div>
            
            <div class="alert">
                <strong>Suggested query:</strong><br>
                <code style="background: rgba(0,0,0,0.1); padding: 4px 8px; border-radius: 4px;">
                    {suggested_query}
                </code>
            </div>
            
            <center>
                <a href="{explore_url}" class="button">Explore This Insight</a>
            </center>
        """
        
        return cls.base_template(content, f"Insight: {insight_title}")
    
    @classmethod
    def welcome_email(cls, user_name: str, login_url: str) -> str:
        """Welcome email for new users"""
        
        content = f"""
            <h2>Welcome to AI Analytics Platform, {user_name}!</h2>
            
            <p>You're all set to start asking questions about your data in plain English.</p>
            
            <div class="highlight">
                <strong>Here are a few things you can try:</strong>
                <ul style="margin-top: 8px;">
                    <li>"What was my revenue last month?"</li>
                    <li>"Show me top customers by sales"</li>
                    <li>"Compare this quarter vs last quarter"</li>
                </ul>
            </div>
            
            <p>Your AI assistant will automatically learn what you care about and proactively share insights.</p>
            
            <center>
                <a href="{login_url}" class="button">Get Started</a>
            </center>
        """
        
        return cls.base_template(content, "Welcome to AI Analytics")
    
    @classmethod
    def export_complete(
        cls,
        user_name: str,
        query: str,
        row_count: int,
        format: str
    ) -> str:
        """Email template for completed export"""
        
        content = f"""
            <h2>Hi {user_name},</h2>
            
            <p>Your data export is ready!</p>
            
            <div class="success">
                <strong>✅ Export Complete</strong>
                <p style="margin: 8px 0;"><strong>Query:</strong> {query[:100]}{'...' if len(query) > 100 else ''}</p>
                <p style="margin: 8px 0;"><strong>Rows:</strong> {row_count:,}</p>
                <p style="margin: 8px 0;"><strong>Format:</strong> {format}</p>
            </div>
            
            <div class="highlight">
                <p><strong>📎 Your file is attached to this email.</strong></p>
                <p style="font-size: 14px; color: #666;">
                    You can open it in Excel, Google Sheets, or any spreadsheet application.
                    The file will also be available for download in the app for 24 hours.
                </p>
            </div>
            
            <p style="margin-top: 24px;">
                <strong>💡 Pro tip:</strong> You can schedule this export to run automatically 
                and have it emailed to you daily, weekly, or monthly. Just ask me: 
                <em>"Send me this report every week"</em>
            </p>
        """
        
        return cls.base_template(content, "Your Data Export is Ready")
