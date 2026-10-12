import random
import re


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
        while True:
            cpf = _with_check_digits([random.randrange(10) for _ in range(9)])
            digits = re.sub(r"\D", "", cpf)
            if len(set(digits)) == 1:
                continue
            if any(fragment in cpf for fragment in _MAGIC_FRAGMENTS):
                continue
            return cpf

    @staticmethod
    def generate_cpf_containing(fragment: str) -> str:
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
