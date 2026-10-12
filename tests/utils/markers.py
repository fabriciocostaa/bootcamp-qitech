import pytest


def known_bug(bug_id: str, reason: str):
    return pytest.mark.xfail(strict=True, reason=f"[{bug_id}] {reason}")
