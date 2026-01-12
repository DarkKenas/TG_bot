from .user import UserRepository
from .wish import WishRepository
from .transfer import TransferRepository
from .admin import AdminRepository
from .collector import CollectorRepository
from .service_user import ServiceUserRepository

__all__ = [
    "UserRepository",
    "WishRepository",
    "TransferRepository",
    "AdminRepository",
    "CollectorRepository",
    "ServiceUserRepository",
]

