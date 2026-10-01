from tests.utils import ObjectGenerator, RequestGenerator, PayloadGenerator


class TestClientUpdate:
    def test_update(self):
        client, jwt_token = ObjectGenerator.create_authenticated_client()
        _key = client["client_key"]
 
        new_status = "approved"
        payload = PayloadGenerator.create_new_status_payload(new_status)
 
        status, response = RequestGenerator.PUT_client(_key, jwt_token, payload)
        assert status == 202
        assert response["client_key"] == _key
 
        status, response = RequestGenerator.GET_client(_key, jwt_token)
        assert status == 200
        assert response["client_key"] == _key
        assert response["name"] == client["name"]
        assert response["email"] == client["email"]
        assert response["document_number"] == client["document_number"]
        assert response["birthdate"] == client["birthdate"]
        assert response["status"] == new_status
 
        # Cada mudanca de status deixa um evento: pending (criacao) + approved.
        trail = [event["status"] for event in response["status_events"]]
        assert trail == ["pending", "approved"]
 
        # Aprovar o cadastro cria uma conta com saldo zero.
        assert len(response["accounts"]) == 1
        account = response["accounts"][0]
        assert account["account_key"] is not None
        assert account["balance"] == "0.00"
        assert account["status"] == "active"


    def test_status_events_keep_the_trail_in_order(self):
        """O GET por chave conta a HISTORIA, nao so o estado de agora.
 
        Cada mudanca de status deixa uma linha em client_status_event.
        A trilha comeca em `pending` porque o controller chama o
        update_status logo apos criar o cliente.
        """
        client, token = ObjectGenerator.create_authenticated_client()
        _key = client["client_key"]
 
        status, response = RequestGenerator.GET_client(_key, token)
        assert status == 200
        assert len(response["status_events"]) == 1
 
        ObjectGenerator.update_client(_key, "approved", token)
 
        status, response = RequestGenerator.GET_client(_key, token)
        assert status == 200
 
        trail = [status_event["status"] for status_event in response["status_events"]]
 
        assert trail == ["pending", "approved"]
        assert response["status_events"][0]["event_datetime"] is not None

    def test_schema_refuses_status_outside_the_enum(self):
        """So os status que o schema lista (approved/rejected) sao aceitos.
 
        O "enum" do put_client.json e o contrato de entrada: um status
        inventado nem chega na regra de negocio.
        """
        client, token = ObjectGenerator.create_authenticated_client()
        _key = client["client_key"]
 
        payload = PayloadGenerator.create_new_status_payload("status_que_nao_existe")
 
        status, response = RequestGenerator.PUT_client(_key, token, payload)
        assert status == 400
        assert response["code"] == "QIT000001"


    def test_update_finished(self):
        """Quem ja saiu de `pending` nao muda mais de status."""
        client, token = ObjectGenerator.create_authenticated_client()
        _key = client["client_key"]
 
        ObjectGenerator.update_client(_key, "approved", token)
 
        status, response = RequestGenerator.GET_client(_key, token)
        assert status == 200
        assert response["client_key"] == _key
        assert response["status"] == "approved"
 
        # Repetir a aprovacao do mesmo status
        payload = PayloadGenerator.create_new_status_payload("approved")
        status, response = RequestGenerator.PUT_client(_key, token, payload)
        assert status == 409
        assert response["code"] == "QIT001002"
