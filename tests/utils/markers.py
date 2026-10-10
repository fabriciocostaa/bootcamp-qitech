import pytest


def known_bug(bug_id: str, reason: str):
    """Marca um teste que descreve o comportamento CORRETO, mas que a API de hoje viola.

    O teste continua escrito do jeito certo: ele diz o que a API DEVERIA
    fazer. O `xfail(strict=True)` so impede que a suite fique vermelha por
    um defeito ja conhecido, e faz o contrario do que parece:

      - enquanto o defeito existe, o teste "falha como esperado" (xfail);
      - no dia em que alguem corrigir a API, o teste PASSA e, por ser
        strict, o pytest acusa XPASS como ERRO — a lembranca de apagar
        esta marca e de comemorar.

    Para ver todos os defeitos de uma vez, como falhas de verdade:

        pytest --runxfail
    """
    return pytest.mark.xfail(strict=True, reason=f"[{bug_id}] {reason}")
