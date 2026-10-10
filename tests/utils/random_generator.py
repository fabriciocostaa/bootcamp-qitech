import random
import re


# Os mocks (mocks/mappings/*.json) decidem o desfecho pelo CONTEUDO do CPF:
#   "99" em qualquer ponto -> o KYC recusa a identidade
#   "88" em qualquer ponto -> o bureau de risco devolve score baixo
#   "77" em qualquer ponto -> o bureau de risco fica indisponivel (503)
# Por isso um CPF aleatorio qualquer NAO serve para teste: ~10% deles
# conteriam "99" e o teste ficaria vermelho sem motivo (flaky). O gerador
# padrao evita todos esses trechos; os cenarios de recusa pedem o trecho
# de proposito, com generate_cpf_containing().
KYC_REJECTED_FRAGMENT = "99"
RISK_LOW_SCORE_FRAGMENT = "88"
RISK_UNAVAILABLE_FRAGMENT = "77"

_MAGIC_FRAGMENTS = (KYC_REJECTED_FRAGMENT, RISK_LOW_SCORE_FRAGMENT, RISK_UNAVAILABLE_FRAGMENT)


def _with_check_digits(nine_digits: list) -> str:
    cpf = list(nine_digits)
    for _ in range(2):
        value = sum([(len(cpf) + 1 - i) * v for i, v in enumerate(cpf)]) % 11
        cpf.append(11 - value if value > 1 else 0)
    number = "".join(str(x) for x in cpf)
    return f"{number[0:3]}.{number[3:6]}.{number[6:9]}-{number[9:11]}"


class RandomGenerator:
    @staticmethod
    def generate_cpf() -> str:
        """Um CPF valido que NAO dispara nenhum comportamento especial dos mocks."""
        while True:
            cpf = _with_check_digits([random.randrange(10) for _ in range(9)])
            digits = re.sub(r"\D", "", cpf)
            if len(set(digits)) == 1:
                continue  # 111.111.111-11 passa na conta mas a API recusa
            if any(fragment in cpf for fragment in _MAGIC_FRAGMENTS):
                continue
            return cpf

    @staticmethod
    def generate_cpf_containing(fragment: str) -> str:
        """Um CPF valido que contem `fragment` (ex.: "99") logo no comeco.

        Os outros trechos magicos ficam de fora, pra que so UM mock reaja.
        """
        assert len(fragment) == 2 and fragment.isdigit()
        others = [f for f in _MAGIC_FRAGMENTS if f != fragment]
        while True:
            nine = [int(fragment[0]), int(fragment[1])] + [random.randrange(10) for _ in range(7)]
            cpf = _with_check_digits(nine)
            digits = re.sub(r"\D", "", cpf)
            if len(set(digits)) == 1:
                continue
            if any(other in cpf for other in others):
                continue
            return cpf

    @staticmethod
    def generate_cnpj():
        cnpj = [random.randrange(10) for _ in range(8)] + [0, 0, 0, 1]

        for _ in range(2):
            value = sum(v * (i % 8 + 2) for i, v in enumerate(reversed(cnpj)))
            digit = 11 - value % 11
            cnpj.append(digit if digit < 10 else 0)

        cnpj_number = "".join(str(x) for x in cnpj)

        cnpj_number = (
            f"{cnpj_number[0:2]}.{cnpj_number[2:5]}.{cnpj_number[5:8]}/{cnpj_number[8:12]}-{cnpj_number[12:14]}"
        )

        return cnpj_number
