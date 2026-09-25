# seed.py
import sys
import os

# Define a raiz de busca
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# Tenta importar com o padrão do Docker primeiro; se falhar, tenta com 'src' (Local)
try:
    from repositories.operator_repository import OperatorRepository
    from database import get_context
except ModuleNotFoundError:
    try:
        from src.repositories.operator_repository import OperatorRepository
        from src.database import get_context
    except ModuleNotFoundError as e:
        print("❌ Erro crítico: Não foi possível localizar os módulos do projeto.")
        raise e

def create_initial_admin():
    context = get_context()
    repository = OperatorRepository(context)
    
    email_admin = "admin@seu-sistema.com"
    
    if repository.get_by_email(email_admin):
        print(f"❌ Erro: O operador '{email_admin}' já existe no banco de dados!")
        return
        
    repository.create_operator(
        email="admin@banco-UFABC.com",
        name="Fabricio da Costa",
        document_number = "509.246.798-32",
        password="adminadmin"
    )

    print(f"🚀 Sucesso: Único Admin ({email_admin}) criado com sucesso!")

if __name__ == "__main__":
    create_initial_admin()