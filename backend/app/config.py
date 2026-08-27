"""
Configurações da aplicação, lidas de variáveis de ambiente.
Nunca coloque chaves/API keys direto no código.
"""
from pydantic_settings import BaseSettings
import dotenv
import os


dotenv.load_dotenv()

class Settings(BaseSettings):
    # Banco de dados (preenchido com o output do OpenTofu -> db_endpoint)
    database_url: str = os.environ.get("BESTPRICE_DATABASE_URL")

    # Infosimples - https://api.infosimples.com/api/v2/consultas/sefaz/sp/cfe-completa
    infosimples_token: str = os.environ.get("BESTPRICE_INFOSIMPLES_TOKEN")
    infosimples_base_url: str = "https://api.infosimples.com/api/v2/consultas/sefaz/sp/cfe-completa"

    # Cosmos / Bluesoft - https://cosmos.bluesoft.com.br/api
    cosmos_token: str = os.environ.get("BESTPRICE_COSMOS_TOKEN")
    cosmos_base_url: str = "https://api.cosmos.bluesoft.com.br"

    # Regras de negócio
    historico_precos_limite: int = 5  # últimas N compras exibidas na tela 2

    # class Config:
    #     env_file = ".env"
    #     # env_prefix = "BESTPRICE_"


settings = Settings()
