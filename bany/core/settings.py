from pydantic import AnyUrl
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    YNAB_API_URL: AnyUrl = "https://api.youneedabudget.com/v1"
    YNAB_API_KEY: SecretStr = ""
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", env_file_encoding="utf-8")
