from fastapi import Header, HTTPException, status

from .config import API_KEY


def verify_api_key(x_api_key: str | None = Header(None)) -> None:
    """Validate optional API key when configured."""
    if not API_KEY:
        return

    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API inválida.",
        )
