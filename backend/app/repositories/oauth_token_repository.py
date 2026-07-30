"""Persistencia de tokens OAuth Atlassian."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import OAuthToken


class OAuthTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(self, user_id: int) -> OAuthToken | None:
        return (
            self.db.query(OAuthToken)
            .filter(OAuthToken.id_user == user_id)
            .first()
        )

    def upsert(
        self,
        user_id: int,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
    ) -> OAuthToken:
        token = self.get_by_user_id(user_id)
        if token:
            token.access_token = access_token
            if refresh_token:
                token.refresh_token = refresh_token
            token.expires_at = expires_at
        else:
            token = OAuthToken(
                id_user=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
            )
            self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def delete_by_user_id(self, user_id: int) -> None:
        token = self.get_by_user_id(user_id)
        if token:
            self.db.delete(token)
            self.db.commit()
