"""SQLite storage for verified users."""

from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS verified_users (
    user_id     INTEGER PRIMARY KEY,
    phone       TEXT    NOT NULL,
    username    TEXT,
    full_name   TEXT,
    verified_at TEXT    NOT NULL
);
"""


class UserStorage:
    def __init__(self, path: str) -> None:
        self._path = path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self._path)
        await self._db.execute(_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("UserStorage is not connected")
        return self._db

    async def save_verified(
        self, user_id: int, phone: str, username: str | None, full_name: str | None
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO verified_users (user_id, phone, username, full_name, verified_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                phone = excluded.phone,
                username = excluded.username,
                full_name = excluded.full_name,
                verified_at = excluded.verified_at
            """,
            (user_id, phone, username, full_name, datetime.now(timezone.utc).isoformat()),
        )
        await self.db.commit()

    async def get_phone(self, user_id: int) -> str | None:
        async with self.db.execute(
            "SELECT phone FROM verified_users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else None
