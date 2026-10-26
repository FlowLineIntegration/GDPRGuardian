"""Clés d'API, jetons et capacités de résultat / API keys, tokens and result capabilities."""

from __future__ import annotations

import base64
import hashlib
import math
from collections import Counter

import pytest
from server_testkit import KEY_A, KEY_A_SHA256, KEY_B

from gdprguardian.server.security import (
    DEV_PRINCIPAL,
    ApiKeyAuthenticator,
    DevAuthenticator,
    bearer_token,
    issue_upload_token,
    result_digest,
    result_id,
    token_digest,
    valid_upload_id,
)


def test_each_key_maps_to_a_stable_distinct_principal() -> None:
    auth = ApiKeyAuthenticator([KEY_A, KEY_B])
    a = auth.authenticate(f"Bearer {KEY_A}")
    b = auth.authenticate(f"bearer {KEY_B}")
    assert a and b and a != b
    assert a == ApiKeyAuthenticator([KEY_A]).authenticate(f"Bearer {KEY_A}")
    # Le principal ne révèle pas la clé / the principal does not reveal the key.
    assert KEY_A not in a and KEY_A[:8] not in a


def test_keys_given_as_digests_authenticate_the_same_principal() -> None:
    # Production : seules les empreintes sont dans l'environnement / production: only digests in the environment.
    by_digest = ApiKeyAuthenticator(digests=[KEY_A_SHA256])
    assert by_digest.authenticate(f"Bearer {KEY_A}") == ApiKeyAuthenticator([KEY_A]).authenticate(f"Bearer {KEY_A}")
    assert by_digest.authenticate(f"Bearer {KEY_A_SHA256}") is None  # l'empreinte n'est pas une clé / not a key
    assert by_digest.authenticate(f"Bearer {KEY_B}") is None


@pytest.mark.parametrize("header", [
    None, "", "Bearer", "Bearer ", f"Basic {KEY_A}", f"Bearer {KEY_A}x", f"Bearer {KEY_A[:-1]}",
    f"Bearer {KEY_A}\x00", "Bearer " + "x" * 5000, f"Token {KEY_A}",
])
def test_invalid_credentials_are_rejected(header: str | None) -> None:
    assert ApiKeyAuthenticator([KEY_A]).authenticate(header) is None


def test_bearer_parsing() -> None:
    assert bearer_token(f"Bearer   {KEY_A}  ") == KEY_A
    assert bearer_token("Bearer clé") is None


def test_authenticator_needs_keys() -> None:
    with pytest.raises(ValueError, match="key"):
        ApiKeyAuthenticator([])


def test_dev_authenticator_accepts_anything() -> None:
    assert DevAuthenticator().authenticate(None) == DEV_PRINCIPAL


def test_upload_tokens_are_256_bits_and_digested() -> None:
    token, digest = issue_upload_token()
    assert len(token) == 43 and token_digest(token) == digest
    assert issue_upload_token()[0] != token
    assert token_digest("short") is None
    assert token_digest(token + "=") is None
    assert token_digest("../" + token[3:]) is None


def test_result_ids_are_256_bit_capabilities_derived_one_way() -> None:
    token, _ = issue_upload_token()
    upload_id = result_id(token)
    assert valid_upload_id(upload_id) and len(upload_id) == 3 + 43
    assert len(base64.urlsafe_b64decode(upload_id[3:] + "=")) == 32  # 256 bits
    assert upload_id == result_id(token) and token not in upload_id
    assert result_digest(upload_id) is not None and result_digest(upload_id) != token_digest(token)
    assert not valid_upload_id(upload_id + "x")
    assert not valid_upload_id("up_" + "a" * 22)  # ancien format de 128 bits / former 128-bit format
    assert not valid_upload_id("up_../../etc/passwd" + "." * 24)
    assert result_digest("up_" + "a" * 22) is None


def test_the_result_id_cannot_be_derived_from_a_seen_upload_url() -> None:
    # Qui voit l'URL d'envoi (historique du shell, ligne de commande de curl) ne calcule pas l'identifiant du résultat :
    # HMAC sous une clé tirée au démarrage, jamais écrite. Whoever sees the upload URL cannot compute the result id:
    # HMAC under a key drawn at start-up, never written.
    token, _ = issue_upload_token()
    public_derivation = hashlib.sha256(b"gdprguardian/result-capability\0" + token.encode()).digest()
    guessed = "up_" + base64.urlsafe_b64encode(public_derivation).rstrip(b"=").decode()
    assert result_id(token) != guessed and valid_upload_id(guessed)


def test_capabilities_are_unpredictable() -> None:
    # 2 000 identifiants : tous distincts, caractères répartis (pas de préfixe fixe ni de compteur).
    # 2,000 ids: all distinct, characters spread out (no fixed prefix, no counter).
    ids = [result_id(issue_upload_token()[0]) for _ in range(2000)]
    assert len(set(ids)) == len(ids)
    for position in (3, 20, 44):
        counts = Counter(upload_id[position] for upload_id in ids)
        assert len(counts) > 50  # sur 64 symboles possibles / out of 64 possible symbols
    # Entropie empirique par caractère proche de 6 bits / empirical entropy per character close to 6 bits.
    counts = Counter("".join(upload_id[3:45] for upload_id in ids))
    total = sum(counts.values())
    entropy = -sum(n / total * math.log2(n / total) for n in counts.values())
    assert entropy > 5.9
