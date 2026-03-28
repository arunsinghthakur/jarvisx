import logging
import uvicorn
from jarvisx.config.configs import ADMIN_API_PORT
from services.api.admin.src.main import app

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=ADMIN_API_PORT)
