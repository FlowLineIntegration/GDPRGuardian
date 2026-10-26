"""Identité des clients : pseudonyme en mémoire, niveaux d'adresse, en-tête de confiance, principal LOCAL.

Client identity: in-memory pseudonym, address tiers, trusted header, LOCAL principal.
"""

from __future__ import annotations

import hashlib
import ipaddress

import pytest
from server_testkit import FakeClock

from gdprguardian.server.clients import (
    LOCAL,
    PSEUDONYM_BYTES,
    ClientIdentifier,
    Pseudonymizer,
    address_tiers,
)


def identifier(clock: FakeClock | None = None, header: str | None = "X-GG-Client") -> ClientIdentifier:
    return ClientIdentifier(header, Pseudonymizer(clock=clock or FakeClock()))


@pytest.mark.parametrize(("address", "client", "prefix"), [
    ("203.0.113.7", "203.0.113.7/32", "203.0.113.0/24"),
    ("::ffff:203.0.113.7", "203.0.113.7/32", "203.0.113.0/24"),       # IPv4 mappée / IPv4-mapped
    ("2001:db8:1:2:3:4:5:6", "2001:db8:1:2::/64", "2001:db8:1::/48"),
    ("2001:DB8:1:2::9", "2001:db8:1:2::/64", "2001:db8:1::/48"),
    ("fe80::1%eth0", "fe80::/64", "fe80::/48"),
])
def test_tiers_are_the_client_and_prefix_networks(address: str, client: str, prefix: str) -> None:
    tiers = address_tiers(address)
    assert tiers is not None
    for material, network in zip(tiers, (client, prefix), strict=True):
        expected = ipaddress.ip_network(network)
        packed = expected.network_address.packed[:expected.prefixlen // 8]
        assert material.endswith(packed) and material[:5] in (b"4/32:", b"4/24:", b"6/64:", b"6/48:")


@pytest.mark.parametrize("value", ["", "jean.dupont@exemple.fr", "1.2.3", "203.0.113.7, 10.0.0.1", "x" * 100,
                                   "2001:db8::g", " "])
def test_unreadable_addresses_give_nothing(value: str) -> None:
    assert address_tiers(value) is None


def test_pseudonyms_are_truncated_keyed_hashes_never_the_address() -> None:
    ident = identifier()
    client, _ = ident.network([(b"x-gg-client", b"203.0.113.7")], None)
    assert client.key is not None and client.key < 2 ** (8 * PSEUDONYM_BYTES)
    assert client.principal == f"c_{client.key:016x}"
    shown = repr(client) + client.principal
    assert "203.0.113" not in shown and "cb007107" not in shown.lower()  # ni texte ni octets / neither text nor bytes
    # Autre secret (redémarrage) : autre pseudonyme, aucun lien possible / another secret: no possible link.
    assert identifier().network([(b"x-gg-client", b"203.0.113.7")], None)[0].key != client.key


def test_same_network_same_client_neighbours_share_the_prefix() -> None:
    ident = identifier()

    def network(address: str) -> tuple[int | None, int | None]:
        client, _ = ident.network([(b"x-gg-client", address.encode())], None)
        return client.key, client.prefix

    assert network("2001:db8:1:2::1") == network("2001:db8:1:2:ffff::1")
    assert network("2001:db8:1:2::1")[1] == network("2001:db8:1:3::1")[1]
    assert network("2001:db8:1:2::1")[0] != network("2001:db8:1:3::1")[0]
    assert network("203.0.113.7")[1] == network("203.0.113.200")[1]
    assert network("203.0.113.7") == network("::ffff:203.0.113.7")


def test_the_trusted_header_is_removed_once_read() -> None:
    headers = [(b"host", b"api.example.eu"), (b"x-gg-client", b"203.0.113.7"), (b"accept", b"*/*")]
    client, kept = identifier().network(headers, ("10.0.0.1", 4242))
    assert kept == [(b"host", b"api.example.eu"), (b"accept", b"*/*")]
    assert not client.local and client.principal.startswith("c_")


def test_without_the_header_the_request_comes_from_the_server_itself() -> None:
    client, kept = identifier().network([(b"host", b"localhost")], None)
    assert client.principal == LOCAL and client.local and client.key is None and client.src == "protocol"
    assert kept == [(b"host", b"localhost")]


TOKEN = "f" * 64
TOKEN_SHA256 = hashlib.sha256(TOKEN.encode()).hexdigest()


def test_with_a_local_token_only_its_holder_is_the_server_itself() -> None:
    # Un travailleur compromis joint le même socket sans en-tête d'adresse : sans le jeton (fichier réservé à root sur
    # l'hôte), il tombe dans le seau commun, jamais LOCAL (ni exempté ni compté « protocol »). A compromised worker
    # reaches the same socket without the address header: without the token, it lands in the shared bucket.
    ident = ClientIdentifier("X-GG-Client", Pseudonymizer(clock=FakeClock()), local_token_sha256=TOKEN_SHA256)
    server, kept = ident.network([(b"host", b"localhost"), (b"x-gg-local", TOKEN.encode())], None)
    assert server.local and server.src == "protocol" and kept == [(b"host", b"localhost")]
    for headers in ([], [(b"x-gg-local", b"wrong")], [(b"x-gg-local", TOKEN.encode())] * 2):
        worker, kept = ident.network(headers, None)
        assert not worker.local and worker.src == "public" and worker.key is not None and kept == []
    garbled, _ = ident.network([(b"x-gg-client", b"not an address")], None)
    assert worker.key == garbled.key  # le seau commun des adresses illisibles / the shared unreadable bucket
    # Le jeton n'élève jamais une requête venue de Nginx / the token never lifts a request coming through Nginx.
    proxied, kept = ident.network([(b"x-gg-client", b"203.0.113.7"), (b"x-gg-local", TOKEN.encode())], None)
    assert not proxied.local and kept == []


def test_prefix_and_budget_keys_are_pseudonyms() -> None:
    client, _ = identifier().network([(b"x-gg-client", b"2001:db8:1:2::1")], None)
    assert client.prefix_key == f"p_{client.prefix:016x}" and client.budget_key == client.prefix_key
    keyed = identifier().principal("k_abc", owner="k_abc")
    assert keyed.prefix_key is None and keyed.budget_key == "k_abc"


def test_a_repeated_or_garbled_header_lands_in_one_shared_bucket() -> None:
    ident = identifier()
    twice, _ = ident.network([(b"x-gg-client", b"203.0.113.7"), (b"x-gg-client", b"198.51.100.1")], None)
    garbled, _ = ident.network([(b"x-gg-client", b"not an address")], None)
    assert twice.key == garbled.key and not twice.local and twice.src == "public"


def test_without_a_configured_header_only_the_tcp_peer_counts() -> None:
    # Un client ne peut pas choisir son identité en écrivant l'en-tête / a client cannot pick its identity.
    ident = identifier(header=None)
    spoofed, kept = ident.network([(b"x-gg-client", b"198.51.100.1")], ("203.0.113.7", 50000))
    real, _ = ident.network([], ("203.0.113.7", 50001))
    assert spoofed.key == real.key and not spoofed.local
    assert kept == [(b"x-gg-client", b"198.51.100.1")]  # sans valeur : jamais lu / meaningless: never read
    unix, _ = ident.network([], None)  # socket Unix sans en-tête configuré : seau commun / shared bucket
    assert not unix.local and unix.key is not None


def test_keyed_principals_get_one_tier_and_their_binding() -> None:
    client = identifier().principal("k_abc", owner="k_abc")
    assert client.prefix is None and client.owner == "k_abc" and client.key is not None


def test_secret_rotation_and_grace_period() -> None:
    clock = FakeClock()
    pseudonymizer = Pseudonymizer(rotate_s=86_400, grace_s=600, clock=clock)
    [(first, previous)] = pseudonymizer.derive(b"m")
    assert previous is None
    clock.advance(86_399)
    assert pseudonymizer.derive(b"m") == [(first, None)]
    clock.advance(1)
    [(second, previous)] = pseudonymizer.derive(b"m")
    assert second != first and previous == first  # 10 min de grâce / 10-minute grace
    clock.advance(600)
    assert pseudonymizer.derive(b"m") == [(second, None)]  # l'ancien secret est oublié / old secret forgotten
