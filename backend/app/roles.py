from . import config


def role_for_email(email, admins=None):
    """Role comes only from server config; nothing the client sends can change it."""
    admins = config.ADMIN_EMAILS if admins is None else admins
    return "admin" if (email or "").strip().lower() in admins else "customer"
