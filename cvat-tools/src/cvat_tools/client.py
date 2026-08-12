import os

from cvat_sdk import make_client
from dotenv import load_dotenv


def get_client():
    load_dotenv()

    url = os.getenv("CVAT_URL", "http://localhost:8080").rstrip("/")
    token = os.getenv("CVAT_ACCESS_TOKEN", "").strip()
    username = os.getenv("CVAT_USERNAME", "").strip()
    password = os.getenv("CVAT_PASSWORD", "")
    org = os.getenv("CVAT_ORG", "").strip()

    if token:
        client = make_client(host=url)
        client.api_client.set_default_header(
            "Authorization",
            f"Token {token}",
        )
    elif username and password:
        client = make_client(
            host=url,
            credentials=(username, password),
        )
    else:
        raise RuntimeError(
            "CVAT authentication missing. Set CVAT_ACCESS_TOKEN or "
            "CVAT_USERNAME + CVAT_PASSWORD in .env."
        )

    if org:
        client.organization_slug = org

    return client
