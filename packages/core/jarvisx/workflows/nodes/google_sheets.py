import logging
from jarvisx.workflows.nodes.base import BaseNodeExecutor

logger = logging.getLogger(__name__)


class GoogleSheetsNodeExecutor(BaseNodeExecutor):
    async def execute(self, config: dict, input_data: dict, node_data: dict) -> dict:
        operation = config.get("operation", "read")
        spreadsheet_id = config.get("spreadsheet_id", "")
        sheet_range = config.get("range", "Sheet1!A1:Z1000")
        credentials_json = config.get("credentials_json", "")

        if not spreadsheet_id:
            return {"error": "spreadsheet_id is required", "data": input_data}

        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build
            import json

            creds_data = json.loads(credentials_json) if isinstance(credentials_json, str) else credentials_json
            creds = Credentials.from_service_account_info(creds_data, scopes=["https://www.googleapis.com/auth/spreadsheets"])
            service = build("sheets", "v4", credentials=creds)
            sheets = service.spreadsheets()

            if operation == "read":
                result = sheets.values().get(spreadsheetId=spreadsheet_id, range=sheet_range).execute()
                values = result.get("values", [])
                if values:
                    headers = values[0]
                    rows = [dict(zip(headers, row)) for row in values[1:]]
                    return {"rows": rows, "headers": headers, "count": len(rows), "data": input_data}
                return {"rows": [], "headers": [], "count": 0, "data": input_data}

            elif operation == "append":
                rows = input_data.get("rows", [])
                if rows:
                    body = {"values": rows if isinstance(rows[0], list) else [list(r.values()) for r in rows]}
                    sheets.values().append(
                        spreadsheetId=spreadsheet_id, range=sheet_range,
                        valueInputOption="USER_ENTERED", body=body,
                    ).execute()
                return {"appended": len(rows), "data": input_data}

            return {"error": f"Unknown operation: {operation}", "data": input_data}
        except Exception as e:
            logger.error(f"Google Sheets operation failed: {e}")
            return {"error": str(e), "data": input_data}
