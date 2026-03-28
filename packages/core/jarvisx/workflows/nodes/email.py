import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import json

from jarvisx.workflows.nodes.base import BaseNodeExecutor
from jarvisx.services.integration_service import get_email_config, IntegrationNotFoundError

logger = logging.getLogger(__name__)


class EmailNodeExecutor(BaseNodeExecutor):
    async def execute(
        self,
        config: dict,
        input_data: dict,
        node_data: dict
    ) -> dict:
        organization_id = node_data.get("organization_id")
        email_config_id = config.get("email_config_id")
        
        to_emails = config.get("to", "")
        subject_template = config.get("subject", "Workflow Output")
        body_template = config.get("body", "{{input.response}}")
        include_attachment = config.get("include_attachment", False)
        attachment_format = config.get("attachment_format", "json")
        
        context = {"input": input_data}
        to_emails = self.interpolate_variables(to_emails, context)
        subject = self.interpolate_variables(subject_template, context)
        body = self.interpolate_variables(body_template, context)
        
        recipients = [email.strip() for email in to_emails.split(",") if email.strip()]
        
        if not recipients:
            raise ValueError("No recipient email addresses provided")
        
        try:
            email_config = get_email_config(organization_id, email_config_id)
        except IntegrationNotFoundError as e:
            logger.error(f"[EmailNode] {e}")
            return {
                "success": False,
                "error": str(e),
                "recipients": recipients,
                "subject": subject
            }
        
        try:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = subject
            msg["From"] = f"{email_config.from_name} <{email_config.from_email}>"
            msg["To"] = ", ".join(recipients)
            
            html_body = self._format_html_body(body)
            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)
            
            if include_attachment:
                attachment_data = self._create_attachment(input_data, attachment_format)
                attachment = MIMEBase("application", "octet-stream")
                attachment.set_payload(attachment_data["content"])
                encoders.encode_base64(attachment)
                attachment.add_header(
                    "Content-Disposition",
                    f"attachment; filename={attachment_data['filename']}"
                )
                msg.attach(attachment)
            
            if not email_config.smtp_host:
                logger.info(f"[EmailNode] SMTP not configured. Would send to {recipients}: {subject}")
                return {
                    "success": True,
                    "message": "Email simulated (SMTP not configured)",
                    "recipients": recipients,
                    "subject": subject
                }
            
            if email_config.use_tls:
                server = smtplib.SMTP(email_config.smtp_host, email_config.smtp_port, timeout=30)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(email_config.smtp_host, email_config.smtp_port, timeout=30)
            
            if email_config.smtp_user and email_config.smtp_password:
                server.login(email_config.smtp_user, email_config.smtp_password)
            
            server.sendmail(email_config.from_email, recipients, msg.as_string())
            server.quit()
            
            logger.info(f"[EmailNode] Email sent successfully to {recipients}")
            return {
                "success": True,
                "message": "Email sent successfully",
                "recipients": recipients,
                "subject": subject
            }
            
        except Exception as e:
            logger.error(f"[EmailNode] Failed to send email: {e}")
            return {
                "success": False,
                "error": str(e),
                "recipients": recipients,
                "subject": subject
            }
    
    def _format_html_body(self, body: str) -> str:
        if body.strip().startswith("<"):
            return body
        
        paragraphs = body.split("\n\n")
        html_paragraphs = [f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs if p.strip()]
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                pre {{ background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; }}
                code {{ background: #f5f5f5; padding: 2px 4px; border-radius: 2px; }}
            </style>
        </head>
        <body>
            <div class="container">
                {''.join(html_paragraphs)}
            </div>
        </body>
        </html>
        """
    
    def _create_attachment(self, data: dict, format: str) -> dict:
        if format == "json":
            content = json.dumps(data, indent=2).encode("utf-8")
            filename = "workflow_output.json"
        elif format == "txt":
            if "response" in data:
                content = str(data["response"]).encode("utf-8")
            else:
                content = json.dumps(data, indent=2).encode("utf-8")
            filename = "workflow_output.txt"
        else:
            content = json.dumps(data, indent=2).encode("utf-8")
            filename = "workflow_output.json"
        
        return {"content": content, "filename": filename}
