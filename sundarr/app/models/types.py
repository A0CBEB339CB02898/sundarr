from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

JsonObject = JSON().with_variant(JSONB, "postgresql")
