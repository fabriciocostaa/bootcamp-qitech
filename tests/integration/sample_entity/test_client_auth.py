from utils import RequestGenerator

class TestClientAuth:
    def test_auth_client(self):
        payload = {}
        status, response = RequestGenerator.POST_client(payload)
        
        assert status == 200
        assert response["code"] == ""     

        #TO DO 
        # TESTE DE AUTENTICAÇÃO DE CLIENTE