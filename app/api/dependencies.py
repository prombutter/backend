import uuid

# Dummy dependency until Auth is ready
async def get_current_workspace() -> uuid.UUID:
    return uuid.UUID("123e4567-e89b-12d3-a456-426614174000")
