import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings


def send_otp_email(to_email: str, otp: str, purpose: str):
    # Define content for each OTP type
    purposes = {
        "account_verification": {
            "subject": "Verify Your Email - SaveMarga",
            "title": "Email Verification",
            "intro": "Thank you for signing up with <b>SaveMarga</b>.",
            "instruction": "Please use the following OTP to verify your account:",
            "icon": """
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="#2B74F5" viewBox="0 0 24 24">
                  <path d="M12 1a11 11 0 1 0 11 11A11.013 11.013 0 0 0 12 1Zm0 19.933A8.933 8.933 0 1 1 20.933 12 8.944 8.944 0 0 1 12 20.933ZM10.293 13.707l-2-2a1 1 0 0 1 1.414-1.414L11 11.586l3.293-3.293a1 1 0 1 1 1.414 1.414l-4 4a1 1 0 0 1-1.414 0Z"/>
                </svg>
            """,
        },
        "two_factor_auth": {
            "subject": "Login Verification - SaveMarga",
            "title": "Two-Factor Authentication",
            "intro": "We detected a login attempt to your <b>SaveMarga</b> account.",
            "instruction": "Use the OTP below to complete your login:",
            "icon": """
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="#2B74F5" viewBox="0 0 24 24">
                  <path d="M12 2a5 5 0 0 1 5 5v3h1a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h1V7a5 5 0 0 1 5-5Zm0 2a3 3 0 0 0-3 3v3h6V7a3 3 0 0 0-3-3Z"/>
                </svg>
            """,
        },
        "password_reset": {
            "subject": "Reset Your Password - SaveMarga",
            "title": "Password Reset Request",
            "intro": "We received a request to reset your <b>SaveMarga</b> account password.",
            "instruction": "Use the OTP below to reset your password:",
            "icon": """
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="#2B74F5" viewBox="0 0 24 24">
                  <path d="M13 3a9 9 0 1 0 9 9h-2a7 7 0 1 1-7-7V3Zm0 4v5l4.28 2.54 1-1.74L14 11V7h-1Z"/>
                </svg>
            """,
        },
    }

    # Default to registration if purpose not recognized
    content = purposes.get(purpose, purposes["account_verification"])

    # HTML Email Template
    html_body = f"""
    <html>
      <body style="margin:0; padding:0; font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color:transparent; color:#FFFFFF;">
        <table align="center" width="100%" style="max-width:600px; background-color:#0C0C0C; border-radius:12px; overflow:hidden;">
          <tr>
            <td style="background-color:#FFAA2D; text-align:center; padding:25px 0;">
              <h1 style="margin:0; color:#0C0C0C; font-weight:800; font-size:26px;">SaveMarga</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:35px;">
              <div style="text-align:center; margin-bottom:20px;">
                {content["icon"]}
              </div>
              <h2 style="text-align:center; color:#FFAA2D; margin-bottom:15px;">{content["title"]}</h2>
              <p style="text-align:center; color:#CCCCCC; font-size:15px;">
                {content["intro"]}<br><br>{content["instruction"]}
              </p>

              <div style="text-align:center; margin:30px 0;">
                <div style="display:inline-block; background-color:transparent; border:2px solid #2B74F5; border-radius:10px; padding:20px 50px; font-size:28px; font-weight:bold; color:#FFAA2D; letter-spacing:4px;">
                  {otp}
                </div>
              </div>

              <p style="color:#9CA3AF; font-size:13px; text-align:center; margin-top:10px;">
                This OTP will expire in <b>10 minutes</b>. Do not share it with anyone.
              </p>
            </td>
          </tr>
          <tr>
            <td style="background-color:transparent; text-align:center; padding:15px;">
              <p style="color:#6B7280; font-size:12px;">&copy; 2025 SaveMarga. All rights reserved.</p>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    # Plaintext Fallback
    text_body = f"""
{content['title']}
-----------------------
{content['intro']}
{content['instruction']}

Your OTP is: {otp}

This OTP will expire in 10 minutes. Do not share it with anyone.
"""

    # Build Email
    message = MIMEMultipart("alternative")
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message["Subject"] = content["subject"]

    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    # Send Email
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
        print(f"✅ [{purpose}] OTP email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send OTP email to {to_email}: {e}")


def send_budget_warning_email(
    to_email: str,
    category: str,
    remaining_budget: float,
    predicted_amount: float,
    risk_probability: float
):
    """
    Send a beautifully styled alert email when the AI predicts overspending on a budget.
    """
    subject = f"⚠️ Budget Overspending Alert: {category} - SaveMarga"
    overrun = predicted_amount - remaining_budget
    risk_pct = int(risk_probability * 100)

    html_body = f"""
    <html>
      <body style="margin:0; padding:0; font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color:transparent; color:#FFFFFF;">
        <table align="center" width="100%" style="max-width:600px; background-color:#0C0C0C; border-radius:12px; overflow:hidden;">
          <tr>
            <td style="background-color:#EF4444; text-align:center; padding:25px 0;">
              <h1 style="margin:0; color:#0C0C0C; font-weight:800; font-size:26px;">SaveMarga Smart Alert</h1>
            </td>
          </tr>
          <tr>
            <td style="padding:35px;">
              <div style="text-align:center; margin-bottom:20px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" fill="#EF4444" viewBox="0 0 24 24">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                </svg>
              </div>
              <h2 style="text-align:center; color:#FFAA2D; margin-bottom:15px;">Overspending Risk Detected!</h2>
              <p style="color:#CCCCCC; font-size:15px; line-height: 1.6; text-align: left;">
                Hello,<br><br>
                Our AI-powered Budget Awareness engine has analyzed your recent spending patterns. 
                Based on your current trajectory, you are at <b>high risk</b> of overspending on your <b>{category}</b> budget this month.
              </p>
              
              <table width="100%" style="margin: 25px 0; border-collapse: collapse; background-color: #1A1A1A; border-radius: 8px; overflow: hidden;">
                <tr style="border-bottom: 1px solid #333;">
                  <td style="padding: 12px 15px; color: #9CA3AF; font-size: 14px;">Remaining Budget</td>
                  <td style="padding: 12px 15px; text-align: right; color: #FFAA2D; font-weight: bold; font-size: 16px;">Rs. {remaining_budget:.2f}</td>
                </tr>
                <tr style="border-bottom: 1px solid #333;">
                  <td style="padding: 12px 15px; color: #9CA3AF; font-size: 14px;">AI Projected Spend</td>
                  <td style="padding: 12px 15px; text-align: right; color: #EF4444; font-weight: bold; font-size: 16px;">Rs. {predicted_amount:.2f}</td>
                </tr>
                <tr style="border-bottom: 1px solid #333;">
                  <td style="padding: 12px 15px; color: #9CA3AF; font-size: 14px;">Predicted Overrun</td>
                  <td style="padding: 12px 15px; text-align: right; color: #EF4444; font-weight: bold; font-size: 16px;">Rs. {overrun:.2f}</td>
                </tr>
                <tr>
                  <td style="padding: 12px 15px; color: #9CA3AF; font-size: 14px;">Risk Probability</td>
                  <td style="padding: 12px 15px; text-align: right; color: #EF4444; font-weight: bold; font-size: 16px;">{risk_pct}%</td>
                </tr>
              </table>

              <p style="color:#CCCCCC; font-size:15px; line-height: 1.6; text-align: center;">
                We recommend checking your <b>What-If Simulator</b> on the website to see how adjusting your daily limits can get you back on track!
              </p>

              <div style="text-align:center; margin:30px 0;">
                <a href="http://localhost:3000/budgetgoals" style="display:inline-block; background-color:#2B74F5; color:#FFFFFF; text-decoration:none; border-radius:8px; padding:12px 30px; font-weight:bold; font-size:16px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                  Go to Budget Dashboard
                </a>
              </div>
            </td>
          </tr>
          <tr>
            <td style="background-color:transparent; text-align:center; padding:15px;">
              <p style="color:#6B7280; font-size:12px;">&copy; 2025 SaveMarga. All rights reserved.</p>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    text_body = f"""
SaveMarga Budget Alert
-----------------------
You are at high risk ({risk_pct}%) of overspending on your {category} budget.
Remaining Budget: Rs. {remaining_budget:.2f}
AI Projected Spend: Rs. {predicted_amount:.2f}
Expected Overrun: Rs. {overrun:.2f}

Please visit your SaveMarga dashboard to review your budget plan.
"""

    message = MIMEMultipart("alternative")
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message["Subject"] = subject

    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
        print(f"✅ Budget warning email sent to {to_email} for {category}")
    except Exception as e:
        print(f"❌ Failed to send budget warning email: {e}")

