import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from config.settings import get_settings

_security = HTTPBasic()


def require_dashboard_login(credentials: HTTPBasicCredentials = Depends(_security)) -> str:
    settings = get_settings()
    correct_username = secrets.compare_digest(credentials.username, settings.dashboard_username)
    correct_password = secrets.compare_digest(credentials.password, settings.dashboard_password)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid dashboard credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
