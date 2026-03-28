import logging
import json
import httpx

from jarvisx.workflows.nodes.base import BaseNodeExecutor
from jarvisx.services.integration_service import get_slack_config, get_teams_config, IntegrationNotFoundError

logger = logging.getLogger(__name__)


class NotificationNodeExecutor(BaseNodeExecutor):
    async def execute(
        self,
        config: dict,
        input_data: dict,
        node_data: dict
    ) -> dict:
        organization_id = node_data.get("organization_id")
        slack_config_id = config.get("slack_config_id")
        teams_config_id = config.get("teams_config_id")
        
        platform = config.get("platform", "slack")
        webhook_url = config.get("webhook_url", "")
        message_template = config.get("message", "{{input.response}}")
        include_data = config.get("include_data", False)
        channel = config.get("channel", "")
        
        context = {"input": input_data}
        message = self.interpolate_variables(message_template, context)
        
        if not webhook_url:
            try:
                if platform == "slack":
                    slack_config = get_slack_config(organization_id, slack_config_id)
                    if slack_config:
                        webhook_url = slack_config.webhook_url
                        if not channel and slack_config.default_channel:
                            channel = slack_config.default_channel
                elif platform == "teams":
                    teams_config = get_teams_config(organization_id, teams_config_id)
                    if teams_config:
                        webhook_url = teams_config.webhook_url
            except IntegrationNotFoundError as e:
                logger.error(f"[NotificationNode] {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "platform": platform
                }
        
        if not webhook_url:
            return {
                "success": False,
                "error": f"Webhook URL is required for {platform} notification. Please configure it in Settings.",
                "platform": platform
            }
        
        try:
            if platform == "slack":
                payload = self._build_slack_payload(message, channel, include_data, input_data)
            elif platform == "teams":
                teams_config = None
                if organization_id:
                    try:
                        teams_config = get_teams_config(organization_id, teams_config_id)
                    except IntegrationNotFoundError:
                        pass
                card_theme_color = teams_config.card_theme_color if teams_config else "6366f1"
                payload = self._build_teams_payload(message, include_data, input_data, card_theme_color)
            elif platform == "discord":
                payload = self._build_discord_payload(message, include_data, input_data)
            else:
                payload = {"text": message}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
            
            logger.info(f"[NotificationNode] Notification sent to {platform}")
            
            return {
                "success": True,
                "message": f"Notification sent to {platform}",
                "platform": platform,
                "status_code": response.status_code
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[NotificationNode] HTTP error: {e}")
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "platform": platform
            }
        except Exception as e:
            logger.error(f"[NotificationNode] Failed to send notification: {e}")
            return {
                "success": False,
                "error": str(e),
                "platform": platform
            }
    
    def _build_slack_payload(self, message: str, channel: str, include_data: bool, data: dict) -> dict:
        payload = {
            "text": message,
            "mrkdwn": True
        }
        
        if channel:
            payload["channel"] = channel
        
        if include_data:
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"```{json.dumps(data, indent=2)[:2900]}```"
                    }
                }
            ]
            payload["blocks"] = blocks
        
        return payload
    
    def _build_teams_payload(self, message: str, include_data: bool, data: dict, theme_color: str = "6366f1") -> dict:
        sections = [
            {
                "activityTitle": "Workflow Notification",
                "facts": [],
                "markdown": True,
                "text": message
            }
        ]
        
        if include_data:
            data_text = json.dumps(data, indent=2)[:2900]
            sections.append({
                "activityTitle": "Data",
                "text": f"```\n{data_text}\n```",
                "markdown": True
            })
        
        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": theme_color,
            "summary": "Workflow Notification",
            "sections": sections
        }
    
    def _build_discord_payload(self, message: str, include_data: bool, data: dict) -> dict:
        embeds = []
        
        if include_data:
            data_text = json.dumps(data, indent=2)[:4000]
            embeds.append({
                "title": "Workflow Output Data",
                "description": f"```json\n{data_text}\n```",
                "color": 6373617
            })
        
        payload = {
            "content": message,
        }
        
        if embeds:
            payload["embeds"] = embeds
        
        return payload
