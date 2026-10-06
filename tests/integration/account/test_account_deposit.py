from tests.utils.object_generator import ObjectGenerator
from tests.utils.request_generator import RequestGenerator
import datetime
from src.models.transaction_type import TransactionType
import uuid

class TestBankOperations:
    def test_deposit_success(self):
        # Create a client and an account
        client, jwt_token = ObjectGenerator.create_authenticated_client()
        response_status, response_json = RequestGenerator.GET_client(client["client_key"], jwt_token)
        
        assert response_status == 200
        
        account = response_json["account"]
        amount = 2000
        idempotency_key = str(uuid.uuid4())

        # Perform a deposit
        response_status, response_json = RequestGenerator.POST_account_deposit(
            account_key=account.account_key,
            jwt_token=client.jwt_token,
            idempotency_key=idempotency_key,
            deposit_payload=amount
        )

        # Check the response status code
        assert response_status == 200

        # Check the updated account balance
        #assert response_json["operation_key"] == 
        assert response_json["kind"] == TransactionType.DEPOSIT
        assert response_json["amount"] == amount
        assert response_json["fee"] == 0
        assert response_json["created_at"] == datetime.datetime.now()

    def test_withdraw_success(self):
        # 1. Preparação: Para o saque funcionar na caixa preta, precisamos criar a conta E depositar antes
        client, jwt_token = ObjectGenerator.create_authenticated_client()
        _, client_data = RequestGenerator.GET_client(client["client_key"], jwt_token)
        account = client_data["account"]
        
        # Garante saldo inicial via API
        RequestGenerator.POST_account_deposit(account.account_key, jwt_token, str(uuid.uuid4()), amount=2000)

        # 2. Execução do Saque
        withdraw_amount = 500
        idempotency_key = str(uuid.uuid4())
        
        response_status, response_json = RequestGenerator.POST_account_withdraw(
            account_key=account.account_key,
            jwt_token=jwt_token,
            idempotency_key=idempotency_key,
            withdraw_payload=withdraw_amount
        )

        # 3. Validações
        assert response_status == 200
        assert response_json["kind"] == TransactionType.WITHDRAW
        assert response_json["amount"] == withdraw_amount
        # Se sua API atualizar o saldo no retorno, valide também (ex: balance == 1500)


    def test_transfer_success(self):
        # 1. Preparação: Precisamos de DUAS contas (Origem com saldo e Destino)
        client_origin, jwt_token_origin = ObjectGenerator.create_authenticated_client()
        _, data_origin = RequestGenerator.GET_client(client_origin["client_key"], jwt_token_origin)
        account_origin = data_origin["account"]
        
        # Deposita na conta de origem
        RequestGenerator.POST_account_deposit(account_origin.account_key, jwt_token_origin, str(uuid.uuid4()), amount=1000)

        # Cria conta de destino
        client_dest, jwt_token_dest = ObjectGenerator.create_authenticated_client()
        _, data_dest = RequestGenerator.GET_client(client_dest["client_key"], jwt_token_dest)
        account_dest = data_dest["account"]

        # 2. Execução da Transferência
        transfer_amount = 400
        idempotency_key = str(uuid.uuid4())

        response_status, response_json = RequestGenerator.POST_account_transfer(
            account_key_origin=account_origin.account_key,
            account_key_destination=account_dest.account_key,
            jwt_token=jwt_token_origin, # Quem transfere é a origem
            idempotency_key=idempotency_key,
            transfer_payload=transfer_amount
        )

        # 3. Validações
        assert response_status == 200
        assert response_json["kind"] == TransactionType.TRANSFER
        assert response_json["amount"] == transfer_amount