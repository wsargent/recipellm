import logging
from typing import Any, Dict

logger = logging.getLogger("mealie-mcp")


class UserMixin:
    """Mixin class for user-related API endpoints"""

    def get_current_user(self) -> Dict[str, Any]:
        """Get information about the currently logged in user.

        Returns:
            Dictionary containing user details such as id, username, email, and other profile information.
        """
        logger.info({"message": "Retrieving current user information"})
        return self._handle_request("GET", "/api/users/self")
