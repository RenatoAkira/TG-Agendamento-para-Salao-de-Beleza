from backend.models import Administrador, Profissional, Cliente

class UserProxy:
    def __init__(self, user_id, user_type):
        self.id = f"{user_type}:{user_id}"
        self.user_type = user_type
        self.user_id = user_id

    def get_real_user(self):
        if self.user_type == 'administrador':
            return Administrador.query.get(self.user_id)
        elif self.user_type == 'profissional':
            return Profissional.query.get(self.user_id)
        elif self.user_type == 'cliente':
            return Cliente.query.get(self.user_id)
        return None

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id
