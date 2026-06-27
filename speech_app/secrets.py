from __future__ import annotations


class SecretStore:
    SERVICE = "Speech"
    API_KEY_ACCOUNT = "ai-api-key"

    def _keyring(self):
        try:
            import keyring
        except ImportError as exc:
            raise RuntimeError(
                "Secure key storage is unavailable. Run 'speech install' first."
            ) from exc
        return keyring

    def get_api_key(self) -> str | None:
        value = self._keyring().get_password(self.SERVICE, self.API_KEY_ACCOUNT)
        return value.strip() if value and value.strip() else None

    def set_api_key(self, value: str) -> None:
        value = value.strip()
        if not value:
            raise ValueError("API key cannot be empty")
        self._keyring().set_password(self.SERVICE, self.API_KEY_ACCOUNT, value)

    def delete_api_key(self) -> None:
        keyring = self._keyring()
        try:
            keyring.delete_password(self.SERVICE, self.API_KEY_ACCOUNT)
        except keyring.errors.PasswordDeleteError:
            pass
