"""
Exposed API functions that can be used by other microservices.

This module re-exports specific functions from api.py that are safe to use
without database access, making them suitable for other services to import
and use independently.
"""

from api.api import (
    verify_jwt_token_with_public_key,
    get_uid_from_token,
    get_public_key,
)

__all__ = [
    'verify_jwt_token_with_public_key',
    'get_uid_from_token',
]
