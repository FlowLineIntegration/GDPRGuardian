"""Dépôt en mémoire : capacités, usage unique, isolement, expiration, effacement / in-memory store behaviour."""

from __future__ import annotations

import pytest
from server_testkit import FakeClock

from gdprguardian.documents import DocumentResult
from gdprguardian.server.errors import InvalidRequest, NotFound, QuotaExceeded, ResultsQuotaExceeded, ServiceBusy
from gdprguardian.server.options import AnonymizeOptions
from gdprguardian.server.security import issue_upload_token, result_id
from gdprguardian.server.store import JobState, JobStore, Quota

OPTIONS = AnonymizeOptions()


def make_store(clock: FakeClock, **overrides: int) -> JobStore:
    # 100 000 caractères : 12 500 par client du PUT, 25 000 par préfixe / 12,500 per PUT client, 25,000 per prefix.
    settings = {"upload_ttl_s": 300, "result_ttl_s": 600, "processing_ttl_s": 660, "max_active_per_principal": 4,
                "max_jobs": 100, "max_chars": 100_000, **overrides}
    return JobStore(clock=clock, **settings)


def result(markdown: str) -> DocumentResult:
    return DocumentResult(markdown, "txt", {"entities": {}}, ["w"], {"comments": 2})


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def test_full_lifecycle_and_deletion_after_full_read(clock: FakeClock) -> None:
    store = make_store(clock)
    job, token = store.create("p", "cv.txt", OPTIONS)
    upload_id = result_id(token)
    assert store.read(upload_id, "p", 1, 1000).status == "pending"
    claimed = store.claim(token, "p")
    assert claimed is job and job.state is JobState.PROCESSING
    store.complete(job, result("a" * 2500))
    assert job.filename == ""
    last = store.read(upload_id, "p", 3, 1000)
    # Rapport, avertissements et éléments écartés à chaque page / report, warnings and dropped on every page.
    assert last.next_page is None and not last.deleted and last.report == {"entities": {}}
    first = store.read(upload_id, "p", 1, 1000)
    assert first.report == {"entities": {}} and first.warnings == ["w"] and first.dropped == {"comments": 2}
    middle = store.read(upload_id, "p", 2, 1000)
    assert middle.deleted and middle.upload_id == upload_id and middle.expires_in == 120
    # Délai de grâce : une réponse perdue se relit / grace period: a lost answer can be read again.
    clock.advance(119)
    assert store.read(upload_id, "p", 2, 1000).markdown == "a" * 1000
    clock.advance(2)
    with pytest.raises(NotFound) as gone:
        store.read(upload_id, "p", 1, 1000)
    assert gone.value.status == 404 and gone.value.code == "already_read"
    assert store.stats() == {"jobs": 0, "stored_chars": 0}


def test_distinct_errors_for_expired_deleted_and_unknown_results(clock: FakeClock) -> None:
    store = make_store(clock)
    _expired, expired_token = store.create("p", "a.txt", OPTIONS)
    deleted, deleted_token = store.create("p", "b.txt", OPTIONS)
    store.claim(deleted_token, "p")
    store.complete(deleted, result("abc"))
    store.delete(result_id(deleted_token), "p")
    clock.advance(301)
    codes = {}
    for name, upload_id in (("expired", result_id(expired_token)), ("deleted", result_id(deleted_token)),
                            ("unknown", result_id(issue_upload_token()[0]))):
        with pytest.raises(NotFound) as caught:
            store.read(upload_id, "p", 1, 1000)
        codes[name] = (caught.value.status, caught.value.code)
    assert codes == {"expired": (404, "expired"), "deleted": (404, "deleted"), "unknown": (404, "not_found")}
    # Une autre clé n'apprend rien / another key learns nothing.
    with pytest.raises(NotFound) as foreign:
        store.read(result_id(deleted_token), "intruder", 1, 1000)
    assert foreign.value.code == "not_found"
    # Traces oubliées après une heure / traces forgotten after an hour.
    clock.advance(3601)
    with pytest.raises(NotFound) as old:
        store.read(result_id(deleted_token), "p", 1, 1000)
    assert old.value.code == "not_found"


def test_each_read_extends_an_unfinished_result(clock: FakeClock) -> None:
    store = make_store(clock)
    job, token = store.create("p", "cv.txt", OPTIONS)
    store.claim(token, "p")
    store.complete(job, result("a" * 2500))
    for page in (1, 2):
        clock.advance(500)
        assert store.read(result_id(token), "p", page, 1000).expires_in == 600
    clock.advance(500)
    assert store.read(result_id(token), "p", 3, 1000).deleted


def test_partial_reads_never_keep_a_result_beyond_three_lifetimes(clock: FakeClock) -> None:
    # Lire la page 1 toutes les 9 minutes ne garde pas le résultat indéfiniment : 30 minutes au plus depuis sa
    # publication. Reading page 1 every 9 minutes does not keep the result forever: 30 minutes at most.
    store = make_store(clock)
    job, token = store.create("p", "cv.txt", OPTIONS)
    store.claim(token, "p")
    store.complete(job, result("a" * 2500))
    expires = [store.read(result_id(token), "p", 1, 1000).expires_in]
    for _ in range(3):
        clock.advance(540)
        expires.append(store.read(result_id(token), "p", 1, 1000).expires_in)
    assert expires == [600, 600, 600, 180]  # borne : 1 800 s après la publication / bound: 1,800 s after publication
    clock.advance(181)
    with pytest.raises(NotFound) as gone:
        store.read(result_id(token), "p", 1, 1000)
    assert gone.value.code == "expired"


def test_wrong_used_or_foreign_tokens_get_the_same_answer(clock: FakeClock) -> None:
    store = make_store(clock)
    _job, token = store.create("p", "cv.txt", OPTIONS)
    with pytest.raises(NotFound) as foreign:
        store.claim(token, "intruder")
    store.claim(token, "p")
    with pytest.raises(NotFound) as used:
        store.claim(token, "p")  # usage unique : même réponse qu'un faux jeton / single use: same as a wrong token
    with pytest.raises(NotFound) as wrong:
        store.claim("x" * 43, "p")
    assert {(e.value.status, e.value.code, e.value.message) for e in (foreign, used, wrong)} == {
        (404, "not_found", NotFound.message)}
    with pytest.raises(NotFound):
        store.read(result_id(token), "intruder", 1, 1000)


def test_unbound_uploads_are_reachable_through_their_capability_only(clock: FakeClock) -> None:
    # Service public : aucune clé ; la capacité seule donne accès, d'où qu'on vienne (l'IP d'un agent change).
    # Public service: no key; the capability alone grants access, wherever the caller is (an agent's IP changes).
    store = make_store(clock)
    job, token = store.create("c_creator", "a.txt", OPTIONS, bound=False, quota=Quota("c_creator", "p_net"))
    _other, other_token = store.create("c_creator", "b.txt", OPTIONS, bound=False)
    assert job.owner is None and job.pending_key == "p_net"  # en attente : le préfixe du créateur / creator's prefix
    store.claim(token, "c_someone_else")  # l'envoi part d'une autre adresse / the PUT comes from elsewhere
    assert job.pending_key is None and job.holders == ("c_someone_else",)  # puis le client du PUT / then the PUT's
    store.complete(job, result("abc"))
    # Le résultat d'un autre envoi n'est pas joignable avec cette capacité / another upload is not reachable.
    assert store.read(result_id(other_token), "c_creator", 1, 1000).status == "pending"
    view = store.read(result_id(token), "c_third", 1, 1000)
    assert view.markdown == "abc" and view.deleted
    clock.advance(121)
    with pytest.raises(NotFound):  # lu, donc consommé après le délai de grâce / read, consumed after the grace
        store.read(result_id(token), "c_creator", 1, 1000)


def test_the_store_keeps_digests_never_the_capabilities(clock: FakeClock) -> None:
    store = make_store(clock)
    job, token = store.create("p", "cv.txt", OPTIONS)
    upload_id = result_id(token)
    kept = repr(vars(store)) + repr([(j.result_digest, j.token_digest) for j in store._jobs.values()])
    assert token not in kept and upload_id not in kept
    assert token.encode() not in job.result_digest + (job.token_digest or b"")
    assert set(store._jobs) == {job.result_digest} and len(job.result_digest) == 32


def test_a_valid_looking_capability_reaches_nothing(clock: FakeClock) -> None:
    store = make_store(clock)
    store.create("p", "cv.txt", OPTIONS)
    forged = result_id(issue_upload_token()[0])  # bien formé, jamais émis / well formed, never issued
    with pytest.raises(NotFound):
        store.read(forged, "p", 1, 1000)
    with pytest.raises(NotFound):
        store.delete(forged, "p")


def test_upload_token_expires(clock: FakeClock) -> None:
    store = make_store(clock)
    _job, token = store.create("p", "cv.txt", OPTIONS)
    clock.advance(301)
    with pytest.raises(NotFound):
        store.claim(token, "p")
    with pytest.raises(NotFound):
        store.get(result_id(token), "p")


def test_result_expires_even_if_unread(clock: FakeClock) -> None:
    store = make_store(clock)
    job, token = store.create("p", "cv.txt", OPTIONS)
    store.claim(token, "p")
    clock.advance(500)
    store.complete(job, result("abc"))
    clock.advance(599)
    assert store.read(result_id(token), "p", 1, 1000).expires_in == 1
    job2, token2 = store.create("p", "b.txt", OPTIONS)
    store.claim(token2, "p")
    store.complete(job2, result("abc"))
    clock.advance(601)
    with pytest.raises(NotFound):
        store.read(result_id(token2), "p", 1, 1000)
    assert store.stats()["stored_chars"] == 0


def test_job_expired_during_processing_is_dropped(clock: FakeClock) -> None:
    store = make_store(clock)
    job, token = store.create("p", "cv.txt", OPTIONS)
    store.claim(token, "p")
    store.start(job)
    clock.advance(661)
    with pytest.raises(NotFound):
        store.complete(job, result("abc"))


def test_time_queued_never_counts_against_an_upload(clock: FakeClock) -> None:
    # File profonde : bien au-delà du délai de traitement avant d'obtenir un travailleur / deep queue.
    store = make_store(clock)
    job, token = store.create("p", "cv.txt", OPTIONS)
    store.claim(token, "p")
    for _ in range(20):
        clock.advance(500)
        assert store.read(result_id(token), "p", 1, 1000).status == "processing"  # purge, réarmé / re-armed
    store.start(job)  # le délai de traitement part d'ici / the processing delay starts here
    clock.advance(659)
    store.complete(job, result("abc"))
    assert store.read(result_id(token), "p", 1, 1000).markdown == "abc"


def test_an_upload_deleted_while_queued_never_gets_a_worker(clock: FakeClock) -> None:
    store = make_store(clock)
    job, token = store.create("p", "cv.txt", OPTIONS)
    store.claim(token, "p")
    store.delete(result_id(token), "p")  # le client renonce pendant l'attente / the client gives up while queued
    with pytest.raises(NotFound):
        store.start(job)
    assert store.stats() == {"jobs": 0, "stored_chars": 0}


def test_a_failed_upload_still_expires(clock: FakeClock) -> None:
    store = make_store(clock)
    job, token = store.create("p", "cv.txt", OPTIONS)
    store.claim(token, "p")
    store.fail(job, InvalidRequest("Envoi interrompu", code="upload_interrupted"))
    clock.advance(601)
    store.purge()
    assert len(store) == 0


def test_failure_is_reported_once(clock: FakeClock) -> None:
    store = make_store(clock)
    job, token = store.create("p", "cv.txt", OPTIONS)
    store.claim(token, "p")
    store.fail(job, InvalidRequest("Envoi interrompu", code="upload_interrupted"))
    with pytest.raises(InvalidRequest) as caught:
        store.read(result_id(token), "p", 1, 1000)
    assert caught.value.code == "upload_interrupted"
    # Redit pendant le délai de grâce, puis oublié / told again during the grace period, then forgotten.
    with pytest.raises(InvalidRequest):
        store.read(result_id(token), "p", 1, 1000)
    clock.advance(121)
    with pytest.raises(NotFound):
        store.read(result_id(token), "p", 1, 1000)


def test_quotas(clock: FakeClock) -> None:
    store = make_store(clock, max_active_per_principal=2, max_pending=3)
    store.create("p", "a.txt", OPTIONS)
    store.create("p", "b.txt", OPTIONS, bound=False)  # compté pour son créateur, lié ou non / counted either way
    with pytest.raises(QuotaExceeded):
        store.create("p", "c.txt", OPTIONS)
    store.create("q", "a.txt", OPTIONS)
    with pytest.raises(ServiceBusy):
        store.create("r", "a.txt", OPTIONS)  # 3 en attente en tout / 3 pending in all
    clock.advance(301)
    store.create("p", "c.txt", OPTIONS)


def test_pending_uploads_count_per_creator_prefix_not_per_address(clock: FakeClock) -> None:
    # Un /48 qui tourne ses /64 ne remplit pas le service : 40 en attente par préfixe ; un autre réseau passe.
    # A /48 rotating its /64s cannot fill the service: 40 pending per prefix; another network goes through.
    store = make_store(clock, max_active_per_principal=10, max_per_prefix=3)
    for client in ("c_a", "c_b", "c_c"):
        store.create(client, "a.txt", OPTIONS, bound=False, quota=Quota(client, "p_attacker"))
    with pytest.raises(QuotaExceeded):
        store.create("c_d", "a.txt", OPTIONS, bound=False, quota=Quota("c_d", "p_attacker"))
    store.create("c_bob", "a.txt", OPTIONS, bound=False, quota=Quota("c_bob", "p_bob"))


def test_received_uploads_and_results_count_against_the_put_client(clock: FakeClock) -> None:
    # Connecteur MCP partagé : il crée les envois, chaque utilisateur les envoie de sa machine ; le quota des
    # résultats suit le PUT. Shared MCP connector: it creates the uploads, each user sends from their machine; the
    # result quota follows the PUT.
    store = make_store(clock, max_active_per_principal=2, max_per_prefix=40)
    connector = Quota("c_connector", "p_connector")
    tokens = [store.create("c_connector", "a.txt", OPTIONS, bound=False, quota=connector)[1] for _ in range(5)]
    for token in tokens[:2]:
        store.claim(token, "c_alice", quota=Quota("c_alice", "p_alice"))
    with pytest.raises(QuotaExceeded):  # deux reçus non lus pour Alice / two unread for Alice
        store.claim(tokens[2], "c_alice", quota=Quota("c_alice", "p_alice"))
    job = store.claim(tokens[2], "c_bob", quota=Quota("c_bob", "p_bob"))  # jeton intact / token kept
    assert job.holders == ("c_bob", "p_bob")


def test_result_characters_are_shared_per_client_and_prefix(clock: FakeClock) -> None:
    # Dépôt de 1 000 caractères : 125 par client du PUT, 250 par préfixe ; un client ne bloque pas les autres.
    # 1,000-character store: 125 per PUT client, 250 per prefix; one client does not block the others.
    store = make_store(clock, max_chars=1_000)
    mallory = Quota("c_mallory", "p_evil")
    job, token = store.create("c_mallory", "a.txt", OPTIONS, bound=False, quota=mallory)
    store.claim(token, "c_mallory", quota=mallory)
    store.complete(job, result("x" * 125))
    job2, token2 = store.create("c_mallory", "b.txt", OPTIONS, bound=False, quota=mallory)
    with pytest.raises(ResultsQuotaExceeded):  # part pleine : refusé avant tout travail / share full: refused upfront
        store.claim(token2, "c_mallory", quota=mallory)
    store.claim(token2, "c_neighbour", quota=Quota("c_neighbour", "p_evil"))
    store.complete(job2, result("y" * 100))
    job3, token3 = store.create("c_mallory", "c.txt", OPTIONS, bound=False, quota=mallory)
    store.claim(token3, "c_third", quota=Quota("c_third", "p_evil"))
    with pytest.raises(ResultsQuotaExceeded):  # le préfixe tiendrait 255 / the prefix would hold 255
        store.complete(job3, result("z" * 30))
    with pytest.raises(ResultsQuotaExceeded):  # échec signalé au lecteur / failure reported to the reader
        store.read(result_id(token3), "c_third", 1, 1000)
    victim = Quota("c_victim", "p_victim")
    job4, token4 = store.create("c_victim", "d.txt", OPTIONS, bound=False, quota=victim)
    store.claim(token4, "c_victim", quota=victim)
    store.complete(job4, result("Jean Dupont"))
    assert store.stats()["stored_chars"] == 125 + 100 + 11


def test_character_budget(clock: FakeClock) -> None:
    store = make_store(clock, max_chars=100)
    job, token = store.create("p", "a.txt", OPTIONS)
    store.claim(token, "p")
    with pytest.raises(ServiceBusy):
        store.complete(job, result("x" * 101))
    with pytest.raises(ServiceBusy):
        store.read(result_id(token), "p", 1, 1000)


def test_page_out_of_range(clock: FakeClock) -> None:
    store = make_store(clock)
    job, token = store.create("p", "a.txt", OPTIONS)
    store.claim(token, "p")
    store.complete(job, result("abc"))
    with pytest.raises(NotFound) as caught:
        store.read(result_id(token), "p", 2, 1000)
    assert caught.value.code == "page_not_found"


def test_distinct_page_sizes_are_bounded(clock: FakeClock) -> None:
    # Sinon chaque lecture pourrait forcer un recalcul complet des bornes / else every read could force a recompute.
    store = make_store(clock)
    job, token = store.create("p", "a.txt", OPTIONS)
    store.claim(token, "p")
    store.complete(job, result("z" * 10_000))
    for size in (1000, 2000, 3000, 4000, 1000):
        store.read(result_id(token), "p", 2, size)
    with pytest.raises(InvalidRequest) as caught:
        store.read(result_id(token), "p", 1, 5000)
    assert caught.value.code == "too_many_page_sizes"


def test_different_page_sizes_share_coverage(clock: FakeClock) -> None:
    store = make_store(clock)
    job, token = store.create("p", "a.txt", OPTIONS)
    store.claim(token, "p")
    store.complete(job, result("z" * 3000))
    assert not store.read(result_id(token), "p", 1, 2000).deleted  # [0, 2000)
    assert store.read(result_id(token), "p", 3, 1000).deleted       # [2000, 3000)
