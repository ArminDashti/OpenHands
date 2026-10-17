import binascii
import hashlib
from base64 import b64decode, b64encode

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, SecretStr
from server.config import get_config

_jwt_service = None
_fernet = None
_settings_cipher = None
_FERNET_TOKEN_PREFIX = 'gAAAA'


class _SettingsReadCipher:
    def __init__(self, cipher):
        self._cipher = cipher

    def encrypt(self, secret: SecretStr | None) -> str | None:
        return self._cipher.encrypt(secret)

    def decrypt(self, secret: str | None) -> SecretStr | None:
        if secret is None:
            return None
        if not secret.startswith(_FERNET_TOKEN_PREFIX):
            return SecretStr(secret)
        decrypted = self._cipher.try_decrypt_str(secret)
        return SecretStr(decrypted if decrypted is not None else secret)

    def try_decrypt_str(self, secret: str) -> str | None:
        return self._cipher.try_decrypt_str(secret)


def encrypt_model(encrypt_keys: list, model_instance) -> dict:
    return encrypt_kwargs(encrypt_keys, model_to_kwargs(model_instance))


def decrypt_model(decrypt_keys: list, model_instance) -> dict:
    return decrypt_kwargs(decrypt_keys, model_to_kwargs(model_instance))


def encrypt_kwargs(encrypt_keys: list, kwargs: dict) -> dict:
    for key, value in kwargs.items():
        if value is None:
            continue

        if isinstance(value, dict):
            encrypt_kwargs(encrypt_keys, value)
            continue

        if key in encrypt_keys:
            value = encrypt_value(value)
            kwargs[key] = value
    return kwargs


def decrypt_kwargs(encrypt_keys: list, kwargs: dict) -> dict:
    for key, value in kwargs.items():
        try:
            if value is None:
                continue
            if key in encrypt_keys:
                value = decrypt_value(value)
                kwargs[key] = value
        except binascii.Error:
            pass  # Key is in legacy format...
    return kwargs


def encrypt_value(value: str | SecretStr) -> str:
    return get_jwt_service().create_jwe_token(
        {'v': value.get_secret_value() if isinstance(value, SecretStr) else value}
    )


def decrypt_value(value: str | SecretStr) -> str:
    token = get_jwt_service().decrypt_jwe_token(
        value.get_secret_value() if isinstance(value, SecretStr) else value
    )
    return token['v']


def get_jwt_service():
    from openhands.app_server.config import get_global_config

    global _jwt_service
    if _jwt_service is None:
        jwt_service_injector = get_global_config().jwt
        assert jwt_service_injector is not None
        _jwt_service = jwt_service_injector.get_jwt_service()
    return _jwt_service


def get_settings_cipher():
    """Return the SDK cipher used for field-level settings encryption."""
    from openhands.sdk.utils.cipher import Cipher

    global _settings_cipher
    if _settings_cipher is None:
        jwt_svc = get_jwt_service()
        default_key = jwt_svc.get_key(jwt_svc._default_key_id)
        _settings_cipher = Cipher(default_key.key.get_secret_value())
    return _settings_cipher


def get_settings_cipher_context() -> dict[str, Any]:
    return {'cipher': _SettingsReadCipher(get_settings_cipher())}


def get_settings_storage_context() -> dict[str, Any]:
    return {'expose_secrets': 'encrypted', 'cipher': get_settings_cipher()}


def decrypt_legacy_model(decrypt_keys: list, model_instance) -> dict:
    return decrypt_legacy_kwargs(decrypt_keys, model_to_kwargs(model_instance))


def decrypt_legacy_kwargs(encrypt_keys: list, kwargs: dict) -> dict:
    for key, value in kwargs.items():
        try:
            if value is None:
                continue
            if key in encrypt_keys:
                value = decrypt_legacy_value(value)
                kwargs[key] = value
        except binascii.Error:
            pass  # Key is in legacy format...
        except InvalidToken:
            pass  # Key not encrypted...
    return kwargs


def decrypt_legacy_value(value: str | SecretStr) -> str:
    if isinstance(value, SecretStr):
        return (
            get_fernet().decrypt(b64decode(value.get_secret_value().encode())).decode()
        )
    else:
        return get_fernet().decrypt(b64decode(value.encode())).decode()


def encrypt_legacy_model(encrypt_keys: list, model_instance) -> dict:
    return encrypt_legacy_kwargs(encrypt_keys, model_to_kwargs(model_instance))


def encrypt_legacy_kwargs(encrypt_keys: list, kwargs: dict) -> dict:
    for key, value in kwargs.items():
        if value is None:
            continue
        if key in encrypt_keys:
            value = encrypt_legacy_value(value)
            kwargs[key] = value
    return kwargs


def encrypt_legacy_value(value: str | SecretStr) -> str:
    if isinstance(value, SecretStr):
        return b64encode(
            get_fernet().encrypt(value.get_secret_value().encode())
        ).decode()
    else:
        return b64encode(get_fernet().encrypt(value.encode())).decode()


def get_fernet():
    global _fernet
    if _fernet is None:
        jwt_secret = get_config().jwt_secret.get_secret_value()
        fernet_key = b64encode(hashlib.sha256(jwt_secret.encode()).digest())
        _fernet = Fernet(fernet_key)
    return _fernet


def model_to_kwargs(model_instance):
    return {
        column.name: getattr(model_instance, column.name)
        for column in model_instance.__table__.columns
    }
