from flask_login import UserMixin
from nfdi_search_engine.common.models.user import User


class SessionUser(UserMixin, User):
    def get_id(self) -> str:
        return self.id
