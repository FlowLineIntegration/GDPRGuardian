#!/usr/bin/env bash
# Gardien RGPD · GDPR Guardian : campagne du protocole public sur le serveur de production (docs/PROTOCOLE.md, §9).
# Public protocol campaign on the production server. À lancer par l'utilisateur sudo, depuis le dossier qui contient
# gg-protocol.pyz (python -m tools.protocol bundle) et ce script. Run by the sudo user, from the folder holding
# gg-protocol.pyz and this script:
#
#   bash run-protocol.sh prepare     dossier en mémoire vive pour le paquet des corpus réels (scp ensuite)
#   bash run-protocol.sh start       lance ou reprend la campagne (conteneur jetable, unité systemd gg-protocol) ;
#                                    GG_PROTOCOL_HOURS=3 bash run-protocol.sh start : pause propre après 3 h
#   bash run-protocol.sh status      avancement (compteurs seulement) ; journal : journalctl -u gg-protocol
#   bash run-protocol.sh stop        pause propre (dernier point de reprise vérifié) ; start reprend
#   bash run-protocol.sh finish      campagne terminée : image du service vérifiée, résultats copiés, dossier de
#                                    travail archivé, corpus réels effacés de la mémoire vive ; campagne incomplète :
#                                    rien n'est effacé, start la reprend
#                                    (GG_PROTOCOL_ABANDON=1 : abandon d'une campagne incomplète, rapport partiel gardé)
#
# Essai chronométré avant la campagne (jamais publié) : paquet de la seule moitié dev (pack-real --split dev) et
# GG_PROTOCOL_ARGS="--synthetic-docs 3000 --redteam-bases 30" ; finish range ses résultats dans results/trial-<date>/.
# Timed trial before the campaign (never published): dev-half pack and a scaled plan; results in results/trial-<date>/.
#
# Le conteneur : image du service en cours (même Python), aucun réseau, système en lecture seule, utilisateur 10001,
# aucune capacité, mémoire sans swap, aucun fichier core, priorité processeur basse ; socket du service en lecture
# seule ; le jeton local arrive sur l'entrée standard depuis le fichier root 0600, jamais en argument ni sur disque.
# L'image du service (docker inspect) entre dans l'empreinte du moteur : une campagne = un moteur. Un écart permis
# (GG_PROTOCOL_ALLOW_SWAP=1, GG_PROTOCOL_REDEPLOYED_AFTER=1) est inscrit dans les résultats, à déclarer.
# The container: the running service's image (same Python), no network, read-only root, user 10001, no capability,
# memory without swap, no core file, low CPU priority; service socket read-only; the local token arrives on standard
# input from the root 0600 file, never as an argument nor on disk. The service image (docker inspect) is part of the
# engine fingerprint: one campaign = one engine. An allowed departure is written into the results, to be disclosed.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
BUNDLE=$HERE/gg-protocol.pyz
RAM=/dev/shm/gg-protocol
PACK_NAME="real-corpora.jsonl.gz"
RESULTS=$HERE/results
UNIT=gg-protocol
NAME=gg-protocol
# Chemins du serveur ; les variables qui suivent ne servent qu'aux essais hors production.
# Server paths; the variables below are for tests outside production only.
WORK=${GG_PROTOCOL_WORK:-/var/lib/gg-protocol}
HEADER=${GG_PROTOCOL_HEADER:-/etc/gdprguardian/local-header}
SOCKET_DIR=${GG_PROTOCOL_SOCKET_DIR:-/run/gdprguardian}
SERVICE=${GG_PROTOCOL_SERVICE_CONTAINER:-gdprguardian-gdprguardian-1}
fail() { echo "ÉCHEC / FAILED: $*" >&2; exit 5; }

engine_id() {
  # Image du conteneur du service en cours / image of the running service container.
  if [ -n "${GG_PROTOCOL_ENGINE_ID:-}" ]; then echo "$GG_PROTOCOL_ENGINE_ID"; return; fi
  sudo docker inspect -f '{{.Image}}' "$SERVICE"
}

image() {
  # Le conteneur jetable reprend l'image exacte du service / the throwaway container uses the service's exact image.
  if [ -n "${GG_PROTOCOL_IMAGE:-}" ]; then echo "$GG_PROTOCOL_IMAGE"; return; fi
  engine_id
}

swap_active() {
  [ -n "$(swapon --show --noheadings 2>/dev/null)" ]
}

no_swap() {
  # Un tmpfs peut être écrit dans le swap : refus tant qu'un swap est actif / tmpfs pages can be swapped to disk.
  if swap_active && [ "${GG_PROTOCOL_ALLOW_SWAP:-}" != 1 ]; then
    fail "swap actif : les corpus réels pourraient atteindre le disque ; sudo swapoff -a le temps de la campagne \
(ou GG_PROTOCOL_ALLOW_SWAP=1, inscrit dans les résultats, à déclarer) / swap active: real corpora could reach the \
disk; sudo swapoff -a"
  fi
}

tool() {
  # L'outil dans un conteneur jetable ; $1 = ro ou rw pour le dossier de travail / the tool in a throwaway container.
  local mode=$1
  shift
  sudo docker run --rm --network none --read-only --no-healthcheck --user 10001:10001 --cap-drop ALL --pull never \
    --ulimit core=0 -v "$WORK:/work:$mode" -v "$BUNDLE:/opt/gg-protocol.pyz:ro" "$(image)" \
    python -I /opt/gg-protocol.pyz "$@"
}

plan_id() {
  sudo sed -n 's/^ *"plan_id": *"\([0-9a-f]*\)".*/\1/p' "$WORK/plan.json" | head -1
}

prepare() {
  # Dossier en mémoire vive au compte du conteneur, jamais à l'utilisateur : systemd-logind (RemoveIPC=yes, réglage
  # par défaut) efface ce qu'un utilisateur possède dans /dev/shm à la fin de sa dernière session SSH. Le paquet
  # arrive par sudo sur l'entrée standard. RAM folder owned by the container's account, never by the user: logind
  # (RemoveIPC=yes, the default) wipes what a user owns in /dev/shm when their last SSH session ends. The pack comes
  # in through sudo on standard input.
  [ "$(findmnt -no FSTYPE -T /dev/shm)" = tmpfs ] || fail "/dev/shm n'est pas un tmpfs / is not a tmpfs"
  no_swap
  sudo install -d -m 700 -o 10001 -g 10001 "$RAM"
  echo "copier le paquet / copy the pack: ssh <serveur> \"sudo install -m 0400 -o 10001 -g 10001 /dev/stdin \
$RAM/$PACK_NAME\" < real-corpora.jsonl.gz"
}

start() {
  [ -f "$BUNDLE" ] || fail "paquet absent / bundle missing: $BUNDLE"
  # Lisible par l'utilisateur 10001 du conteneur, quel que soit le masque du scp / readable by the container's user.
  sudo chmod 0644 "$BUNDLE"
  sudo test -f "$HEADER" || fail "jeton local absent : install.sh base / local token missing"
  sudo test -S "$SOCKET_DIR/app.sock" || fail "service arrêté / service not running"
  sudo curl -fsS --max-time 30 --unix-socket "$SOCKET_DIR/app.sock" -H "@$HEADER" -o /dev/null \
    http://localhost/health/deep || fail "sonde profonde du service (jeton local ?) / service deep probe (local token?)"
  if sudo test -d "$WORK/results"; then
    fail "campagne déjà terminée dans $WORK : finish l'archive ; une nouvelle campagne part d'un dossier vide / \
campaign already complete in $WORK: finish archives it"
  fi
  if systemctl is-active -q "$UNIT"; then fail "campagne déjà en cours / campaign already running"; fi
  local real=() extra=() engine image_name
  engine=$(engine_id) || fail "image du service introuvable / service image not found ($SERVICE)"
  [ -n "$engine" ] || fail "image du service introuvable / service image not found ($SERVICE)"
  image_name=$(image)
  # Budget de temps facultatif (pause propre, puis start reprend) / optional time budget (clean pause, start resumes).
  if [ -n "${GG_PROTOCOL_HOURS:-}" ]; then extra=(--hours "$GG_PROTOCOL_HOURS"); fi
  # Essais seulement : plan réduit (jamais publié) / tests only: scaled plan (never published).
  if [ -n "${GG_PROTOCOL_ARGS:-}" ]; then
    local more=()
    read -r -a more <<<"$GG_PROTOCOL_ARGS"
    extra+=("${more[@]}")
  fi
  # sudo : après un premier start, le dossier appartient à 10001 (0700) / after a first start, owned by 10001.
  if sudo test -f "$RAM/$PACK_NAME"; then
    [ "$(findmnt -no FSTYPE -T "$RAM")" = tmpfs ] || fail "$RAM n'est pas en mémoire vive / not in RAM"
    no_swap
    # L'outil efface le paquet dès les unités réelles enregistrées (dossier inscriptible pour lui seul).
    # The tool wipes the pack once the real units are saved (folder writable by it alone).
    sudo chown -R 10001:10001 "$RAM"
    sudo chmod 0700 "$RAM"
    sudo chmod 0400 "$RAM/$PACK_NAME"
    real=(--real "/real/$PACK_NAME" --wipe-real-when-done)
    # Swap permis malgré tout : inscrit dans les résultats / swap allowed anyway: written into the results.
    if swap_active; then extra+=(--disclose allow_swap); fi
  fi
  # Nouvelle campagne sans les corpus réels : refusée (l'outil refuse aussi) / new campaign without the real corpora.
  if [ ${#real[@]} -eq 0 ] && ! sudo test -f "$WORK/plan.json"; then
    fail "paquet des corpus réels absent de $RAM : prepare puis scp / real-corpus pack missing: prepare, then scp"
  fi
  sudo install -d -m 700 -o 10001 -g 10001 "$WORK"
  local real_mount=()
  if sudo test -d "$RAM"; then real_mount=(-v "$RAM:/real"); fi
  # Entrée standard = fichier d'en-tête, ouvert par le shell root de l'unité / stdin = the header file.
  sudo systemd-run --unit="$UNIT" --collect --quiet \
    /bin/sh -c "exec docker run --rm -i --name $NAME --pull never --network none --read-only --no-healthcheck \
      --user 10001:10001 --cap-drop ALL --security-opt no-new-privileges:true --pids-limit 64 --ulimit core=0 \
      --memory 2g --memory-swap 2g --cpus 1 --cpu-shares 256 --log-driver none \
      --tmpfs /tmp:size=16m,mode=1777,noexec,nosuid,nodev \
      -v $SOCKET_DIR:$SOCKET_DIR:ro ${real_mount[*]} -v $BUNDLE:/opt/gg-protocol.pyz:ro -v $WORK:/work \
      $image_name python -I /opt/gg-protocol.pyz run --socket $SOCKET_DIR/app.sock --token-stdin \
      --engine-id $engine --work /work ${real[*]} ${extra[*]} < $HEADER"
  echo "campagne lancée / campaign started (moteur / engine ${engine}): journalctl -u $UNIT -f ; \
bash run-protocol.sh status"
}

status() {
  systemctl is-active "$UNIT" || true
  echo "image du service / service image: $(engine_id 2>/dev/null || echo '?')"
  tool ro status --work /work
}

stop() {
  sudo docker stop -t 60 "$NAME" >/dev/null 2>&1 || true
  echo "pause : start reprend au dernier point de reprise / paused: start resumes from the last checkpoint"
}

wipe_ram() {
  # Corpus réels : effacés de la mémoire vive (exigence DILA, règle du protocole) / real corpora wiped from RAM.
  sudo rm -rf /dev/shm/gg-protocol
  echo "corpus réels effacés de /dev/shm / real corpora wiped from /dev/shm"
}

archive() {
  # Le dossier de travail part en archive : une nouvelle campagne repart d'un dossier vide.
  # The work folder is archived: a new campaign starts from an empty folder.
  local target
  target="$WORK-$(date -u +%Y%m%dT%H%M%SZ)-$(plan_id)$1"
  sudo mv "$WORK" "$target"
  echo "dossier de travail archivé / work folder archived: $target"
}

finish() {
  if systemctl is-active -q "$UNIT"; then fail "campagne en cours / campaign still running"; fi
  sudo test -d "$WORK" || { echo "aucune campagne / no campaign: $WORK"; wipe_ram; return; }
  install -d -m 700 "$RESULTS"
  if sudo test -d "$WORK/results"; then
    # Une campagne = un moteur : l'image du service doit être celle du début / same service image as at start.
    local current dest=$RESULTS
    current=$(engine_id) || fail "image du service introuvable / service image not found ($SERVICE)"
    if ! tool ro verify-engine --work /work --engine-id "$current"; then
      [ "${GG_PROTOCOL_REDEPLOYED_AFTER:-}" = 1 ] || fail "l'image du service n'est plus celle de la campagne : \
redéployé pendant la campagne ? Si c'était après sa fin (comparer docker inspect StartedAt et la fin dans status), \
GG_PROTOCOL_REDEPLOYED_AFTER=1, inscrit dans les résultats, à déclarer / the service image is not the campaign's"
      # L'écart entre dans le point de reprise et dans les résultats réécrits / the departure goes into the results.
      tool rw report --work /work --disclose "redeployed_after:$current" > /dev/null
      echo "ATTENTION : image changée après la campagne, inscrit dans les résultats, à déclarer / WARNING: image \
changed after the campaign, written into the results, to be disclosed"
    fi
    if sudo grep -q '"standard": false' "$WORK/plan.json"; then
      # Essai (plan réduit) : à part, jamais publié / trial (scaled plan): kept apart, never published.
      dest="$RESULTS/trial-$(date -u +%Y%m%dT%H%M%SZ)"
      install -d -m 700 "$dest"
    fi
    # Motif développé par root : le dossier de travail n'est lisible que par 10001 / glob expanded as root.
    sudo sh -c "cp '$WORK'/results/protocol-* '$dest'/ && chown $(id -u):$(id -g) '$dest'/protocol-*"
    ls -l "$dest"
    archive ""
  elif [ "${GG_PROTOCOL_ABANDON:-}" = 1 ]; then
    # Abandon : rapport partiel (jamais publié comme résultat, mais déclaré) / abandon: partial report, disclosed.
    local partial
    partial="$RESULTS/abandoned-$(date -u +%Y%m%dT%H%M%SZ)"
    tool rw report --work /work --allow-partial --out /work/results-abandoned
    install -d -m 700 "$partial"
    sudo sh -c "cp '$WORK'/results-abandoned/protocol-* '$partial'/ && chown -R $(id -u):$(id -g) '$partial'"
    ls -l "$partial"
    archive "-abandoned"
  else
    # Campagne incomplète : rien n'est effacé, pour que start la reprenne. Le paquet des corpus réels reste en mémoire
    # vive tant que leurs unités ne sont pas faites (l'outil l'efface ensuite) ; un redémarrage du serveur le perd.
    # Incomplete campaign: nothing is wiped, so that start can resume it. The real-corpus pack stays in RAM until its
    # units are done (the tool wipes it then); a server reboot loses it.
    local pack="absent"
    if sudo test -f "$RAM/$PACK_NAME"; then pack="gardé en mémoire vive / kept in RAM ($RAM)"; fi
    echo "campagne incomplète : start la reprend ; paquet des corpus réels : $pack (s'il manque alors que des unités \
réelles restent, prepare puis scp avant start) ; GG_PROTOCOL_ABANDON=1 bash run-protocol.sh finish l'abandonne et \
efface la mémoire vive (rapport partiel gardé, à déclarer) / incomplete campaign: start resumes it; real-corpus pack: \
$pack (if it is missing while real units remain, prepare then scp before start); GG_PROTOCOL_ABANDON=1 abandons it \
and wipes the RAM"
    return
  fi
  wipe_ram
}

case "${1:-}" in
  prepare) prepare ;;
  start) start ;;
  status) status ;;
  stop) stop ;;
  finish) finish ;;
  *) sed -n '2,19p' "$0"; exit 2 ;;
esac
