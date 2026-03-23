from dataclasses import dataclass
from datetime import datetime


@dataclass
class Workspace:
    id: int | None
    owner_id: int
    name: str
    description: str | None = None
    created_at: datetime | None = None
