from tests.utils import ObjectGenerator, RequestGenerator, PayloadGenerator


class TestClientUpdate:
    def test_update(self):
        client = ObjectGenerator.create_client()
        _key = client["client_key"]

        new_status = "success"
        payload = {"status": new_status}

        status, response = RequestGenerator.PUT_client(_key, payload)
        assert status == 202

        status, response = RequestGenerator.GET_client(_key)
        assert status == 200
        assert response["client_key"] == _key
        assert response["status"] == "success"

    def test_status_events_keep_the_trail_in_order(self):
        """O GET por chave conta a HISTORIA, nao so o estado de agora.

        Cada mudanca de status deixa uma linha em
        client_status_event, e ate agora nenhuma rota devolvia
        essas linhas: o banco guardava uma historia que ninguem podia
        ler. Saber que a entidade esta em `success` e diferente de
        saber POR ONDE ela passou pra chegar la.

        Repare que a trilha comeca em `pending`, e nao em `created`: o
        repositorio grava o status inicial direto na entidade, sem
        passar pelo update_status que e quem cria o evento. E uma
        lacuna conhecida do projeto, e o teste a descreve como ela e em
        vez de fingir que nao existe.
        """
        client = ObjectGenerator.create_client()
        _key = client["client_key"]

        status, response = RequestGenerator.GET_client(_key)
        assert status == 200
        assert len(response["status_events"]) == 1

        ObjectGenerator.update_client(_key, "success")

        status, response = RequestGenerator.GET_client(_key)
        assert status == 200

        trail = []
        for status_event in response["status_events"]:
            trail.append(status_event["status"])

        assert trail == ["pending", "success"]
        assert response["status_events"][0]["event_datetime"] is not None

    def test_schema_refuses_status_outside_the_enum(self):
        """So os status que o schema lista sao aceitos.

        O "enum": ["success", "failed"] do put_client.json e a
        maquina de estados escrita no contrato de entrada: um status
        inventado nem chega na regra de negocio.
        """
        client = ObjectGenerator.create_client()
        _key = client["client_key"]

        payload = PayloadGenerator.create_new_status_payload("status_que_nao_existe")

        status, response = RequestGenerator.PUT_client(_key, payload)
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_webhook(self):

        client = ObjectGenerator.create_client()
        _key = client["client_key"]

        status, response = RequestGenerator.PUT_webhook_client(_key)
        assert status == 204

        status, response = RequestGenerator.GET_client(_key)
        assert status == 200
        assert response["client_key"] == _key
        assert response["counter"] == 1

    def test_update_finished(self):

        client = ObjectGenerator.create_client()

        _key = client["client_key"]

        ObjectGenerator.update_client(_key, "success")

        status, response = RequestGenerator.GET_client(_key)
        assert status == 200
        assert response["client_key"] == _key
        assert response["status"] == "success"

        payload = PayloadGenerator.create_new_status_payload("success")
        status, response = RequestGenerator.PUT_client(_key, payload)
        assert status == 409
        assert response["code"] == "QIT001002"
