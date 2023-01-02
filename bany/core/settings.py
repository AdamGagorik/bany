from pydantic import AnyUrl
from pydantic import BaseSettings
from pydantic import SecretStr


class Settings(BaseSettings):
    YNAB_API_URL: AnyUrl = "https://api.youneedabudget.com/v1"
    YNAB_API_KEY: SecretStr

    class Config:
        env_file = ".env"
        env_prefix = ""
        env_file_encoding = "utf-8"
