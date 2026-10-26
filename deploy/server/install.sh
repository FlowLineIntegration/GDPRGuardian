#!/usr/bin/env bash
# Gardien RGPD · GDPR Guardian : installation du service public en ligne sur un serveur Ubuntu (Docker, ufw et
# fail2ban déjà en place). Idempotent ; à lancer par un utilisateur sudo, phase par phase, depuis le dossier de ce
# script. Online public service install on an Ubuntu server (Docker, ufw, fail2ban in place). Idempotent; run
# phase by phase, from this script's folder:
#
#   bash install.sh base              Nginx (configuration principale dédiée, HTTP seul tant qu'il n'y a pas de
#                                     certificat), tmpfs du socket, réglages, compose
#   bash install.sh image <archive>   charge l'image Docker (archive de « docker save ») et vérifie sa version
#   bash install.sh cert              certificat Let's Encrypt pour les noms qui pointent ici (les deux noms api.*
#                                     sont requis ; relancer quand d'autres noms arrivent : le certificat s'étend,
#                                     il ne perd jamais un nom)
#   bash install.sh https             configuration HTTPS finale de Nginx
#   bash install.sh site <binaire> [<vidéos>]
#                                     démon du site (gdprguardian-site, construit dans site/) : service systemd ;
#                                     vidéo de lancement (fichiers de video/out du dépôt ; par défaut le dossier
#                                     ../../video/out de ce script) copiée là où Nginx la sert, sous /media/
#   bash install.sh start             (re)crée le conteneur, attend /health et la bonne version, sonde de santé
#   bash install.sh verify            contrôles de bout en bout ; échoue au premier défaut
#   bash install.sh updates           mises à jour automatiques (heure de Paris) : sécurité chaque nuit à 2 h, le
#                                     reste le samedi à 2 h, redémarrage aussitôt s'il le faut, et chaque lundi à 2 h
#
# Service public : aucune clé d'API. Mise à jour d'un serveur en place / upgrade in place: site <binaire> <vidéos>,
# base, image <archive>, start, verify (le démon du site d'abord : Nginx ne pointe vers lui qu'ensuite).
# Chaque fichier de Nginx est sauvegardé, testé (nginx -t) et rétabli si le test échoue : la configuration en
# service n'est jamais remplacée par une configuration cassée. Every Nginx file is backed up, tested and restored on
# failure: the running configuration is never replaced by a broken one.
set -euo pipefail
# Service (API REST et MCP) et site (démon Rust : page en français sur gardienrgpd.fr, en anglais sur
# gdprguardian.com, statistiques en direct ; ni cookie ni journal d'accès).
API_NAMES=(api.gdprguardian.com api.gardienrgpd.fr)
SITE_NAMES=(gdprguardian.com www.gdprguardian.com gardienrgpd.fr www.gardienrgpd.fr)
CERT_NAME=gdprguardian
APP_DIR=/opt/gdprguardian
ENV_DIR=/etc/gdprguardian
ENV_FILE=$ENV_DIR/gdprguardian.env
# Jeton des requêtes du serveur lui-même (sonde, vérification, protocole de mesure) : l'en-tête prêt pour curl
# (-H @fichier, jamais en argument), et son empreinte pour le conteneur. Token of the server's own requests: the
# header ready for curl (-H @file, never as an argument), and its digest for the container.
LOCAL_HEADER=$ENV_DIR/local-header
LOCAL_ENV=$ENV_DIR/local.env
HERE=$(cd "$(dirname "$0")" && pwd)
CONTAINER=gdprguardian-gdprguardian-1
SOCKET=/run/gdprguardian/app.sock
# Configuration principale dédiée (nginx -c) : le nginx.conf du paquet reste intact / dedicated main configuration.
NGINX_MAIN=/etc/nginx/nginx-gdprguardian.conf
NGINX_STOCK=/etc/nginx/nginx.conf
BACKUP_DIR=/var/backups/gdprguardian
STATIC_PAGE=/var/www/gdprguardian-site
# Vidéo de lancement des sites, servie par Nginx sous /media/ : même liste que $gdprguardian_media (nginx-http.conf),
# et que les pages citent (tests/server/test_deploy_config.py). Launch video of the sites, served by Nginx under
# /media/: same list as $gdprguardian_media (nginx-http.conf) and as the pages cite.
MEDIA_DIR=/var/www/gdprguardian-media
MEDIA_FILES=(gardien-rgpd-lancement-fr.mp4 gardien-rgpd-lancement-fr-poster.png
             gardien-rgpd-lancement-fr-transcript.txt gardien-rgpd-lancement-fr-social.mp4
             gdpr-guardian-launch-en.mp4 gdpr-guardian-launch-en-poster.png
             gdpr-guardian-launch-en-transcript.txt gdpr-guardian-launch-en-social.mp4)
step() { echo; echo "=== $*"; }
put() { sudo install -D -m "$2" /dev/stdin "$1"; }
fail() { echo "ÉCHEC / FAILED: $*" >&2; exit 5; }

# Version attendue, lue dans compose.yaml / expected version, read from compose.yaml.
wanted_image() { sed -n 's/^ *image: *//p' "$HERE/compose.yaml" | head -1; }
wanted_version() { local image; image=$(wanted_image); echo "${image##*:}"; }

# Ancienne page statique (avant le démon), retirée dès que Nginx ne la sert plus / old static page (before the
# daemon), removed once Nginx no longer serves it.
drop_static_page() {
  if [ -d "$STATIC_PAGE" ] && ! sudo grep -qs "$STATIC_PAGE" /etc/nginx/sites-available/gdprguardian; then
    sudo rm -r "$STATIC_PAGE"
    echo "ancienne page statique retirée / old static page removed"
  fi
}

# Installe des fichiers de Nginx « source:destination » : sauvegarde, installation, test, et retour à l'état
# précédent si le test échoue. Installs Nginx files "source:destination": backup, install, test, and back to the
# previous state if the test fails.
nginx_apply() {
  local stamp pair src dest saved=()
  stamp=$(date +%Y%m%d-%H%M%S)
  sudo install -d -m 700 "$BACKUP_DIR/nginx-$stamp"
  for pair in "$@"; do
    src=${pair%%:*}
    dest=${pair#*:}
    if sudo test -e "$dest"; then
      sudo cp -a "$dest" "$BACKUP_DIR/nginx-$stamp/$(echo "$dest" | tr / _)"
      saved+=("$dest")
    fi
    sudo install -D -m 644 "$src" "$dest"
  done
  if ! sudo nginx -t -q -c "$NGINX_MAIN"; then
    echo "nginx -t a échoué : retour à la configuration précédente / nginx -t failed: restoring" >&2
    for pair in "$@"; do
      dest=${pair#*:}
      if printf '%s\n' "${saved[@]}" | grep -qx -- "$dest"; then
        sudo cp -a "$BACKUP_DIR/nginx-$stamp/$(echo "$dest" | tr / _)" "$dest"
      else
        sudo rm -f "$dest"
      fi
    done
    exit 3
  fi
}

# nginx.conf du paquet : rétabli s'il a été modifié (une modification bloque les mises à jour automatiques de
# Nginx). Packaged nginx.conf: restored when modified (a modification blocks unattended Nginx upgrades).
restore_stock_nginx_conf() {
  local want have
  want=$(dpkg-query -W -f='${Conffiles}\n' nginx-common 2>/dev/null | awk -v f="$NGINX_STOCK" '$1 == f {print $2}')
  have=$(md5sum "$NGINX_STOCK" 2>/dev/null | cut -d' ' -f1 || true)
  if [ -n "$want" ] && [ "$want" != "$have" ]; then
    sudo install -d -m 700 "$BACKUP_DIR"
    sudo mv "$NGINX_STOCK" "$BACKUP_DIR/nginx.conf.modifie-$(date +%Y%m%d-%H%M%S)"
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q install --reinstall \
      -o Dpkg::Options::=--force-confmiss nginx-common >/dev/null
    echo "nginx.conf du paquet rétabli (l'ancien est dans $BACKUP_DIR) / packaged nginx.conf restored"
  else
    echo "nginx.conf du paquet intact / packaged nginx.conf untouched"
  fi
}

base() {
  step "Paquets : Nginx, Certbot, curl / packages"
  sudo DEBIAN_FRONTEND=noninteractive apt-get -y -q install nginx certbot curl >/dev/null
  sudo apt-mark manual nginx certbot >/dev/null
  restore_stock_nginx_conf

  step "tmpfs dédié du socket du service, monté avant Docker / dedicated socket tmpfs, mounted before Docker"
  [ "$(getent group www-data | cut -d: -f3)" = 33 ] || fail "le groupe www-data doit avoir le gid 33 / must be gid 33"
  sudo install -D -m 644 "$HERE/run-gdprguardian.mount" /etc/systemd/system/run-gdprguardian.mount
  sudo install -D -m 644 "$HERE/docker.service.conf" /etc/systemd/system/docker.service.d/gdprguardian.conf
  # Fichiers temporaires de Nginx en mémoire, recréés à chaque démarrage / Nginx temporary files in memory.
  put /etc/tmpfiles.d/gdprguardian.conf 644 <<'EOF'
# Fichiers temporaires de Nginx : en mémoire, recréés à chaque démarrage. Le dossier du socket du service est un
# tmpfs dédié (run-gdprguardian.mount). Nginx temporary files: in memory, recreated at every boot. The service
# socket's folder is a dedicated tmpfs (run-gdprguardian.mount).
d /run/nginx 0700 www-data www-data -
EOF
  sudo systemd-tmpfiles --create /etc/tmpfiles.d/gdprguardian.conf
  sudo systemctl daemon-reload
  sudo systemctl enable run-gdprguardian.mount >/dev/null 2>&1
  if ! mountpoint -q /run/gdprguardian; then
    sudo systemctl start run-gdprguardian.mount
    echo "tmpfs monté : start recréera le conteneur dessus / tmpfs mounted: start recreates the container on it"
  fi
  findmnt -no FSTYPE,OPTIONS /run/gdprguardian
  stat -c '%A %U:%G %n' /run/gdprguardian /run/nginx

  step "Réglages (aucune clé : service public) / settings (no key: public service)"
  sudo install -d -m 700 "$ENV_DIR"
  if ! sudo test -f "$ENV_FILE"; then
    printf '%s\n' \
      "# Gardien RGPD · GDPR Guardian : réglages facultatifs de l'exploitant (deploy/README.md). Jamais de clé :" \
      "# le service est public ; compose.yaml fixe déjà le mode public, l'en-tête client et la mémoire." \
      "# Exemple : GDPRGUARDIAN_LIMITS=dry-run (compte sans refuser), GDPRGUARDIAN_LIMIT_COST_RATE=0.5" \
      | put "$ENV_FILE" 600
    echo "réglages créés / settings created: $ENV_FILE"
  elif sudo grep -qE '^GDPRGUARDIAN_API_KEYS=' "$ENV_FILE"; then
    # Le service refuse désormais toute clé en clair dans l'environnement : la ligne est retirée (service public).
    # The service now refuses any plaintext key in the environment: the line is removed (public service).
    sudo sed -i '/^GDPRGUARDIAN_API_KEYS=/d' "$ENV_FILE"
    echo "clé d'API en clair retirée des réglages (service public) / plaintext API key removed (public service)"
  else
    echo "réglages déjà présents, conservés / settings kept: $ENV_FILE"
  fi

  step "Jeton local (requêtes du serveur lui-même) / local token (the server's own requests)"
  if sudo test -f "$LOCAL_HEADER" && sudo test -f "$LOCAL_ENV"; then
    echo "jeton local conservé / local token kept"
  else
    # printf est interne au shell : le jeton ne passe dans aucune ligne de commande / printf is a builtin.
    local token digest
    token=$(od -An -N32 -tx1 /dev/urandom | tr -d ' \n')
    digest=$(printf '%s' "$token" | sha256sum | cut -d' ' -f1)
    printf 'X-GG-Local: %s\n' "$token" | put "$LOCAL_HEADER" 600
    printf 'GDPRGUARDIAN_LOCAL_TOKEN_SHA256=%s\n' "$digest" | put "$LOCAL_ENV" 600
    token=""
    echo "jeton local créé (start le prend en compte) / local token created (start picks it up)"
  fi

  # Pare-feu sans journal : ses lignes portent l'adresse source des paquets refusés. Firewall without a log: its
  # lines carry the source address of refused packets.
  if command -v ufw >/dev/null 2>&1; then
    step "ufw : journal coupé / ufw: logging off"
    sudo ufw logging off >/dev/null
    sudo find /var/log -maxdepth 1 -type f -name 'ufw.log.*' -delete
    if sudo test -f /var/log/ufw.log; then sudo truncate -s 0 /var/log/ufw.log; fi
    sudo ufw status verbose | grep -i '^logging'
  fi

  step "Docker Compose"
  sudo install -D -m 644 "$HERE/compose.yaml" "$APP_DIR/compose.yaml"
  sudo docker compose -f "$APP_DIR/compose.yaml" config --quiet && echo "compose.yaml valide / valid"

  step "Nginx : configuration principale dédiée, HTTP seul tant qu'il n'y a pas de certificat"
  sudo install -d -m 755 /var/www/letsencrypt
  sudo rm -f /etc/nginx/sites-enabled/default
  local site=nginx-site-acme.conf
  # Certificat présent : configuration finale, toujours assortie aux réglages communs installés en même temps.
  # Certificate present: final configuration, always matching the shared settings installed with it.
  if sudo test -f "/etc/letsencrypt/live/$CERT_NAME/fullchain.pem"; then site=nginx-site.conf; fi
  local dropin=/etc/systemd/system/nginx.service.d/gdprguardian.conf
  nginx_apply "$HERE/nginx-main.conf:$NGINX_MAIN" \
    "$HERE/nginx-http.conf:/etc/nginx/conf.d/00-gdprguardian.conf" \
    "$HERE/nginx-service-headers.conf:/etc/nginx/snippets/gdprguardian-service-headers.conf" \
    "$HERE/nginx-service-proxy.conf:/etc/nginx/snippets/gdprguardian-service-proxy.conf" \
    "$HERE/nginx-service-errors.conf:/etc/nginx/snippets/gdprguardian-service-errors.conf" \
    "$HERE/$site:/etc/nginx/sites-available/gdprguardian"
  sudo ln -sf /etc/nginx/sites-available/gdprguardian /etc/nginx/sites-enabled/gdprguardian
  sudo install -D -m 644 "$HERE/nginx.service.conf" "$dropin"
  sudo systemctl daemon-reload
  sudo systemctl enable nginx >/dev/null 2>&1
  # Toujours un redémarrage (une seconde) : un rechargement ne change pas de fichier principal, et il échoue en
  # silence quand la clé ou la taille d'une zone limit_req/limit_conn change (erreur au niveau emerg, donc muette).
  # Always a restart (one second): a reload does not switch the main file, and it fails silently when the key or
  # size of a limit_req/limit_conn zone changes (the error is below emerg, so never written).
  sudo systemctl restart nginx
  systemctl show -p ExecStart --value nginx | grep -q -- "-c $NGINX_MAIN" || fail "nginx ne lit pas $NGINX_MAIN"
  drop_static_page
  if sudo test -f "/etc/letsencrypt/live/$CERT_NAME/fullchain.pem" && ! sudo test -S /run/gdprguardian-site/site.sock; then
    echo "attention : démon du site absent, le site répond 502 : install.sh site <binaire> / warning: no site daemon (502)"
  fi

  # Journaux écrits avant ces réglages (adresses complètes possibles) : vidés, anciennes rotations effacées.
  # Logs written before these settings (full addresses possible): emptied, old rotations deleted.
  step "Journaux de Nginx vidés / Nginx logs emptied"
  sudo find /var/log/nginx -maxdepth 1 -type f -name '*.log.*' -delete
  sudo find /var/log/nginx -maxdepth 1 -type f -name '*.log' -exec truncate -s 0 {} +
  sudo ls -la /var/log/nginx

  # Pas de prison fail2ban sur Nginx : elle lirait le journal d'erreurs ; le débit reste borné par Nginx (limit_req,
  # limit_conn) et par le limiteur du service. No fail2ban jail on Nginx: it would read the error log; the rate stays
  # bounded by Nginx and by the service's limiter.
  if sudo test -f /etc/fail2ban/jail.d/10-gdprguardian-nginx.local; then
    sudo rm /etc/fail2ban/jail.d/10-gdprguardian-nginx.local
    sudo systemctl restart fail2ban
  fi
}

check_image() {  # l'image attendue par compose.yaml est chargée / the image compose.yaml expects is loaded
  local want
  want=$(wanted_image)
  sudo docker image inspect "$want" >/dev/null 2>&1 \
    || fail "image $want absente : install.sh image <archive> / image $want missing"
  echo "image attendue présente / expected image present: $want"
}

image() {
  local archive=${1:?archive de « docker save » attendue / docker save archive expected}
  step "Image Docker / Docker image"
  sudo docker load -i "$archive"
  sudo docker image ls gdprguardian
  check_image
}

points_here() {  # $1 : nom ; vrai si IPv4 et IPv6 (si publiée) pointent ici / true if it resolves here
  local mine4 mine6 name=$1
  mine4=$(ip -4 -o addr show scope global | awk '{print $4}' | cut -d/ -f1 | head -1)
  mine6=$(ip -6 -o addr show scope global | awk '{print $4}' | cut -d/ -f1 | head -1)
  getent ahostsv4 "$name" | awk '{print $1}' | grep -qx "$mine4" || return 1
  local v6
  v6=$(getent ahostsv6 "$name" | awk '{print $1}' | grep -v '^::ffff:' | sort -u)
  [ -z "$v6" ] || [ "$v6" = "$mine6" ]
}

cert() {
  step "DNS : noms qui pointent sur ce serveur / names pointing here"
  local name ready=() missing=() have=()
  for name in "${API_NAMES[@]}" "${SITE_NAMES[@]}"; do
    if points_here "$name"; then ready+=("$name"); echo "ok: $name"; else missing+=("$name"); echo "pas encore / not yet: $name"; fi
  done
  for name in "${API_NAMES[@]}"; do
    printf '%s\n' "${ready[@]}" | grep -qx "$name" || { echo "DNS pas prêt pour $name : réessayer plus tard"; exit 3; }
  done
  # Jamais moins de noms que le certificat en service : un nom absent du DNS un instant ne doit pas en sortir.
  # Never fewer names than the live certificate: a name briefly missing from DNS must not drop out of it.
  read -r -a have <<<"$(sudo certbot certificates --cert-name "$CERT_NAME" 2>/dev/null | sed -n 's/^ *Domains: //p' || true)"
  for name in "${have[@]}"; do
    printf '%s\n' "${ready[@]}" | grep -qx "$name" \
      || { echo "$name ne pointe plus ici : certificat inchangé / no longer points here: certificate unchanged"; exit 3; }
  done

  step "Certificat Let's Encrypt (ECDSA, défi HTTP) : ${ready[*]}"
  local args=()
  for name in "${ready[@]}"; do args+=(-d "$name"); done
  sudo certbot certonly --webroot -w /var/www/letsencrypt --cert-name "$CERT_NAME" "${args[@]}" --expand \
    --key-type ecdsa --agree-tos --register-unsafely-without-email --non-interactive --keep-until-expiring \
    --deploy-hook "systemctl reload nginx"
  [ ${#missing[@]} -eq 0 ] || echo "à ajouter plus tard (relancer cert) / add later (rerun cert): ${missing[*]}"
  sudo certbot certificates --cert-name "$CERT_NAME" | grep -E 'Domains|Expiry'
  systemctl is-enabled certbot.timer
}

https() {
  step "Nginx : configuration HTTPS finale / final HTTPS configuration"
  sudo test -f "/etc/letsencrypt/live/$CERT_NAME/fullchain.pem" || { echo "certificat absent / missing: cert"; exit 3; }
  nginx_apply "$HERE/nginx-main.conf:$NGINX_MAIN" \
    "$HERE/nginx-http.conf:/etc/nginx/conf.d/00-gdprguardian.conf" \
    "$HERE/nginx-service-headers.conf:/etc/nginx/snippets/gdprguardian-service-headers.conf" \
    "$HERE/nginx-service-proxy.conf:/etc/nginx/snippets/gdprguardian-service-proxy.conf" \
    "$HERE/nginx-service-errors.conf:/etc/nginx/snippets/gdprguardian-service-errors.conf" \
    "$HERE/nginx-site.conf:/etc/nginx/sites-available/gdprguardian"
  sudo systemctl restart nginx  # pas reload : voir base / not reload: see base
  # Répétition du renouvellement, sans le délai aléatoire (jusqu'à 8 min) des renouvellements non interactifs.
  # Renewal rehearsal, without the random delay (up to 8 min) of non-interactive renewals.
  sudo certbot renew --dry-run --no-random-sleep-on-renew --cert-name "$CERT_NAME" 2>&1 | tail -2
}

# Vidéo de lancement, contrôlée avant tout changement ; faux si les pages du binaire n'en citent aucune (binaire
# d'avant la vidéo : retour en arrière). Sinon chaque fichier de la liste doit être là, et chaque
# /media/…?v=<empreinte> cité désigner un fichier de la liste dont le SHA-256 commence par cette empreinte (Nginx le
# garde un an sous ce lien : une autre version y resterait). Launch video, checked before anything changes; false
# when the binary's pages cite none (a binary from before the video: rollback). Otherwise every listed file must be
# there, and every cited /media/…?v=<digest> name a listed file whose SHA-256 starts with that digest.
check_media() {  # $1 : binaire, $2 : dossier des vidéos / binary, video folder
  local binary=$1 videos=$2 name ref version digest refs
  refs=$(grep -aoE '/media/[A-Za-z0-9._-]+[?]v=[0-9a-f]{8}' "$binary" | sort -u || true)
  if [ -z "$refs" ]; then
    echo "les pages du binaire ne citent aucune vidéo : /media/ inchangé / the binary's pages cite no video"
    return 1
  fi
  [ -d "$videos" ] || fail "dossier des vidéos absent : install.sh site <binaire> <video/out> / missing video folder: $videos"
  for name in "${MEDIA_FILES[@]}"; do
    [ -s "$videos/$name" ] || fail "vidéo absente / missing video file: $videos/$name"
  done
  while read -r ref; do
    name=${ref#/media/}
    version=${name#*\?v=}
    name=${name%%\?*}
    printf '%s\n' "${MEDIA_FILES[@]}" | grep -qxF -- "$name" || fail "$name : hors de la liste / not listed (MEDIA_FILES)"
    digest=$(sha256sum "$videos/$name" | cut -c1-8)
    [ "$digest" = "$version" ] || fail "$name : empreinte $digest, les pages attendent $version / digest mismatch"
  done <<<"$refs"
  echo "vidéos conformes aux pages du binaire / video files match the binary's pages: $(wc -l <<<"$refs") liens / links"
}

# Copie de la liste : seuls les fichiers changés (ETag et Last-Modified stables d'une installation à l'autre), par un
# nom temporaire puis un renommage (jamais un fichier à moitié écrit servi) ; tout autre fichier du dossier retiré.
# Copies the list: changed files only (stable ETags across installs), through a temporary name then a rename (never
# half a file served); any other file in the folder removed.
install_media() {  # $1 : dossier des vidéos / video folder
  local videos=$1 name present changed=0
  sudo install -d -m 755 "$MEDIA_DIR"
  for name in "${MEDIA_FILES[@]}"; do
    if sudo cmp -s "$videos/$name" "$MEDIA_DIR/$name"; then continue; fi
    sudo install -m 644 "$videos/$name" "$MEDIA_DIR/.$name.new"
    sudo mv -f "$MEDIA_DIR/.$name.new" "$MEDIA_DIR/$name"
    changed=$((changed + 1))
  done
  while IFS= read -r -d '' present; do
    printf '%s\n' "${MEDIA_FILES[@]}" | grep -qxF -- "${present##*/}" || sudo rm -f -- "$present"
  done < <(sudo find "$MEDIA_DIR" -mindepth 1 -maxdepth 1 -type f -print0)
  echo "$changed fichier(s) remplacé(s) sur ${#MEDIA_FILES[@]} / file(s) replaced: $MEDIA_DIR"
  if ! sudo grep -qsF 'location ^~ /media/' /etc/nginx/sites-available/gdprguardian; then
    echo "attention : Nginx ne sert pas encore /media/ : install.sh base / warning: Nginx does not serve /media/ yet"
  fi
}

site() {
  local binary=${1:?binaire gdprguardian-site attendu / gdprguardian-site binary expected}
  # Vidéos : dossier donné, sinon video/out du dépôt quand ce script y est lancé / video folder: the one given, else
  # the repository's video/out when this script runs from a checkout.
  local videos=${2:-$HERE/../../video/out}
  [ -f "$binary" ] || { echo "binaire absent / missing binary: $binary"; exit 3; }
  # Fichiers en place avant que la nouvelle page les cite / files in place before the new page cites them.
  step "Site : vidéo de lancement, servie par Nginx sous /media/ / launch video, served by Nginx under /media/"
  if check_media "$binary" "$videos"; then
    install_media "$videos"
  fi
  step "Site : démon Rust / Rust daemon"
  # Groupe 10001 = utilisateur du conteneur du service : il envoie ses comptes d'usage au démon.
  # Group 10001 = the service container's user: it sends its usage counts to the daemon.
  getent group gdprguardian >/dev/null || sudo groupadd --system --gid 10001 gdprguardian
  local gid
  gid=$(getent group gdprguardian | cut -d: -f3)
  [ "$gid" = 10001 ] || { echo "le groupe gdprguardian doit avoir le gid 10001 / must have gid 10001: $gid"; exit 3; }
  if id -u gdprguardian-site >/dev/null 2>&1; then
    sudo usermod --gid www-data --groups gdprguardian --shell /usr/sbin/nologin gdprguardian-site
  else
    sudo useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin --gid www-data \
      --groups gdprguardian gdprguardian-site
  fi
  id gdprguardian-site
  # Remplacement atomique, même pendant que l'ancien tourne / atomic replacement, even while the old one runs.
  sudo install -m 755 "$binary" /usr/local/bin/gdprguardian-site.new
  /usr/local/bin/gdprguardian-site.new --version
  sudo mv -f /usr/local/bin/gdprguardian-site.new /usr/local/bin/gdprguardian-site
  sudo install -D -m 644 "$HERE/gdprguardian-site.tmpfiles" /etc/tmpfiles.d/gdprguardian-site.conf
  sudo systemd-tmpfiles --create /etc/tmpfiles.d/gdprguardian-site.conf
  stat -c '%A %U:%G %n' /run/gdprguardian-stats
  sudo install -D -m 644 "$HERE/gdprguardian-site.service" /etc/systemd/system/gdprguardian-site.service
  sudo systemctl daemon-reload
  sudo systemctl enable --now gdprguardian-site
  sudo systemctl restart gdprguardian-site  # nouveau binaire pris en compte / picks up the new binary
  local listening=""
  for _ in $(seq 1 50); do
    if sudo test -S /run/gdprguardian-site/site.sock && sudo test -S /run/gdprguardian-stats/usage.sock; then
      listening=1
      break
    fi
    sleep 0.2
  done
  [ -n "$listening" ] || { sudo journalctl -u gdprguardian-site -n 20 --no-pager; exit 4; }
  sudo stat -c '%A %U:%G %n' /run/gdprguardian-site/site.sock /run/gdprguardian-stats/usage.sock
  echo "socket du site / site socket: $(sudo curl -s -o /dev/null -w '%{http_code}' \
    --unix-socket /run/gdprguardian-site/site.sock -H 'Host: gardienrgpd.fr' http://localhost/api/stats)"
  systemctl is-active gdprguardian-site
  # Ancienne page statique : gardée tant que Nginx la sert encore (base la retire ensuite) / old static page: kept
  # while Nginx still serves it (base removes it afterwards).
  drop_static_page
}

# /health par le socket, sans en-tête d'adresse (requête du serveur lui-même) / /health through the socket.
socket_health() { sudo curl -fsS --max-time 5 --unix-socket "$SOCKET" http://localhost/health 2>/dev/null; }

# Requête du serveur lui-même par le socket, jeton local compris : hors limites par client, comptée « protocol » par
# le démon du site, jamais comme du trafic public. The server's own request through the socket, local token included:
# outside per-client limits, counted as "protocol" by the site daemon, never as public traffic.
socket_curl() { sudo curl -fsS --max-time 120 --unix-socket "$SOCKET" -H "@$LOCAL_HEADER" "$@"; }

start() {
  step "Service : démarrage / start"
  # La version vient du dossier livré, jamais d'une copie restée dans /opt / the shipped folder decides the version.
  sudo install -D -m 644 "$HERE/compose.yaml" "$APP_DIR/compose.yaml"
  check_image
  mountpoint -q /run/gdprguardian || fail "tmpfs /run/gdprguardian absent : install.sh base / missing tmpfs"
  sudo test -f "$LOCAL_ENV" || fail "jeton local absent : install.sh base / missing local token: install.sh base"
  # Recréé à chaque fois : nouvelle image, nouveaux réglages, montage du tmpfs dédié / recreated every time.
  sudo docker compose -f "$APP_DIR/compose.yaml" up -d --force-recreate --remove-orphans
  local health="" version
  version=$(wanted_version)
  for _ in $(seq 1 45); do
    health=$(socket_health || true)
    case $health in *'"status":"ok"'*) break ;; esac
    sleep 2
  done
  case $health in
    *"\"version\":\"$version\""*) echo "sain, version $version / healthy, version $version" ;;
    *'"status":"ok"'*) fail "version inattendue / unexpected version: $health (attendue / expected $version)" ;;
    *) sudo docker logs --tail 30 "$CONTAINER"; fail "le service ne répond pas / the service does not answer" ;;
  esac
  sudo docker inspect -f 'réseau / network: {{.HostConfig.NetworkMode}} ; lecture seule / read-only: {{.HostConfig.ReadonlyRootfs}} ; utilisateur / user: {{.Config.User}} ; init: {{.HostConfig.Init}}' "$CONTAINER"
  sudo stat -c '%A %U:%G %n' "$SOCKET"  # tmpfs réservé au service et à Nginx / service + Nginx only
  # Un vrai travailleur répond, et le jeton local est reconnu (sinon 404) / a real worker answers, local token known.
  socket_curl -o /dev/null http://localhost/health/deep \
    || fail "sonde profonde (travailleur ou jeton local) / deep probe (worker or local token)"
  echo "travailleurs et jeton local : ok / workers and local token: ok"

  step "Sonde de santé côté hôte, toutes les 2 minutes / host-side health probe, every 2 minutes"
  sudo install -m 755 "$HERE/gdprguardian-watchdog" /usr/local/sbin/gdprguardian-watchdog
  sudo install -D -m 644 "$HERE/gdprguardian-watchdog.service" /etc/systemd/system/gdprguardian-watchdog.service
  sudo install -D -m 644 "$HERE/gdprguardian-watchdog.timer" /etc/systemd/system/gdprguardian-watchdog.timer
  sudo systemctl daemon-reload
  sudo systemctl enable --now gdprguardian-watchdog.timer >/dev/null 2>&1
  systemctl is-active gdprguardian-watchdog.timer
}

# --- updates : calendrier de maintenance (heure de Paris) / maintenance schedule (Paris time) ------------------------
#   chaque nuit à 2 h (1 h 45 le lundi) : sécurité, redémarrage aussitôt si elle l'exige
#   samedi 2 h : sécurité et correctifs stables (-updates : docker.io, nginx…), redémarrage aussitôt s'il le faut
#   lundi 2 h : redémarrage, une fois toute mise à jour en cours terminée
# Every night at 2 am (1:45 on Monday): security, reboot right after when required. Saturday 2 am: security and stable
# updates, same rule. Monday 2 am: reboot, once any running update is over.

MAINTENANCE_UNITS=(gdprguardian-weekly-upgrade.service gdprguardian-weekly-upgrade.timer
                   gdprguardian-weekly-reboot.service gdprguardian-weekly-reboot.timer)

updates() {
  step "Mises à jour automatiques : sécurité chaque nuit, le reste le samedi, redémarrage le lundi / automatic updates"
  sudo install -D -m 644 "$HERE/apt-unattended.conf" /etc/apt/apt.conf.d/52gdprguardian-unattended
  sudo install -D -m 644 "$HERE/apt-weekly.conf" "$ENV_DIR/apt-weekly.conf"
  sudo install -D -m 644 "$HERE/apt-daily.timer.conf" /etc/systemd/system/apt-daily.timer.d/gdprguardian.conf
  sudo install -D -m 644 "$HERE/apt-daily-upgrade.timer.conf" /etc/systemd/system/apt-daily-upgrade.timer.d/gdprguardian.conf
  sudo install -m 755 "$HERE/gdprguardian-maintenance" /usr/local/sbin/gdprguardian-maintenance
  local unit
  for unit in "${MAINTENANCE_UNITS[@]}"; do
    sudo install -D -m 644 "$HERE/$unit" "/etc/systemd/system/$unit"
  done
  sudo systemctl daemon-reload
  sudo systemctl enable --now apt-daily.timer apt-daily-upgrade.timer >/dev/null 2>&1
  sudo systemctl enable --now gdprguardian-weekly-upgrade.timer gdprguardian-weekly-reboot.timer >/dev/null 2>&1
  sudo systemctl restart apt-daily.timer apt-daily-upgrade.timer
  updates_check
  systemctl list-timers --no-pager apt-daily.timer apt-daily-upgrade.timer gdprguardian-weekly-upgrade.timer \
    gdprguardian-weekly-reboot.timer
}

updates_check() {  # origines de chaque nuit : sécurité seulement / nightly origins: security only
  local origins
  origins=$(sudo unattended-upgrade --dry-run -d 2>&1 | grep -m1 'Allowed origins are:' || true)
  echo "$origins"
  case $origins in
    *-updates*) fail "le passage de chaque nuit prend aussi -updates / the nightly run also takes -updates" ;;
    *-security*) ;;
    *) fail "origines de sécurité introuvables / security origins not found" ;;
  esac
  local timer
  for timer in apt-daily-upgrade.timer gdprguardian-weekly-upgrade.timer gdprguardian-weekly-reboot.timer; do
    systemctl is-active -q "$timer" || fail "minuterie inactive / inactive timer: $timer"
  done
  sudo grep -qs 'Automatic-Reboot-Time "now"' /etc/apt/apt.conf.d/52gdprguardian-unattended \
    || fail "redémarrage automatique non réglé / automatic reboot not set"
  # Le redémarrage du lundi attend la fin des mises à jour : sa détection ne doit rien voir quand rien ne tourne.
  # The Monday reboot waits for updates to finish: its detection must see nothing when nothing runs.
  local state
  state=$(sudo /usr/local/sbin/gdprguardian-maintenance check)
  echo "maintenance : $state"
  if [ "$state" != "libre / idle" ] \
    && ! systemctl is-active -q apt-daily.service apt-daily-upgrade.service gdprguardian-weekly-upgrade.service; then
    fail "la maintenance croit apt occupé alors qu'aucune mise à jour ne tourne / maintenance sees apt busy while idle"
  fi
}

# --- verify : chaque contrôle fait échouer la phase / every check fails the phase ---------------------------------

http_code() { curl -s -o /dev/null -w '%{http_code}' --max-time 30 "$@" || true; }

expect_code() {  # $1 : code attendu, puis les arguments de curl / expected code, then curl arguments
  local want=$1 got
  shift
  got=$(http_code "$@")
  [ "$got" = "$want" ] || fail "curl $* : $got (attendu / expected $want)"
}

# Corps JSON refusé par le service (champ inconnu) après lecture complète : prouve le passage par Nginx jusqu'au service
# sans rien anonymiser, donc sans rien compter comme trafic public. A JSON body the service refuses (unknown field)
# after reading it whole: proves the path through Nginx to the service without anonymising, hence without counting
# anything as public traffic.
expect_refused_body() {  # $1 : URL ; $2 : taille du champ de remplissage / filler size
  local url=$1 size=$2 body out
  body=$(mktemp)
  python3 -c 'import sys; sys.stdout.write("{\"text\": \"x\", \"filler\": \"" + "a" * int(sys.argv[1]) + "\"}")' "$size" >"$body"
  out=$(curl -sS --max-time 60 -w ' %{http_code}' -H 'Content-Type: application/json' --data-binary "@$body" "$url") || true
  rm -f "$body"
  case $out in *'"invalid_request"'*' 422') ;; *) fail "$url : ${out:0:200} (attendu / expected 422 invalid_request)" ;; esac
}

verify_api() {  # $1 : URL de base / base URL
  local url=$1 version headers body out
  version=$(wanted_version)
  step "$url"
  body=$(curl -fsS --max-time 10 "$url/health") || fail "$url/health"
  case $body in *"\"version\":\"$version\""*) echo "health: $body" ;; *) fail "version de $url : $body (attendue $version)" ;; esac
  headers=$(curl -sS -D - -o /dev/null --max-time 10 "$url/health" | tr -d '\r')
  printf '%s\n' "$headers" | grep -qi '^strict-transport-security: max-age=' || fail "HSTS absent ($url)"
  printf '%s\n' "$headers" | grep -qi "^content-security-policy: default-src 'none'" || fail "CSP absente ($url)"
  printf '%s\n' "$headers" | grep -qi '^x-content-type-options: nosniff' || fail "nosniff absent ($url)"
  printf '%s\n' "$headers" | grep -qi '^cache-control: no-store' || fail "no-store absent ($url)"
  printf '%s\n' "$headers" | grep -qiE '^server: nginx/' && fail "version de Nginx affichée / nginx version shown"
  printf '%s\n' "$headers" | grep -qi '^set-cookie:' && fail "Set-Cookie ($url)"
  [ "$(printf '%s\n' "$headers" | grep -ci '^strict-transport-security:')" = 1 ] || fail "HSTS en double / twice"
  # Sans clé, par Nginx jusqu'au service : un petit corps et un corps de 2 Mo, refusés par le service après lecture
  # (jamais comptés). Keyless, through Nginx to the service: a small body and a 2 MB one, refused after reading.
  expect_refused_body "$url/v1/anonymize/text" 10
  expect_refused_body "$url/v1/anonymize/text" 2097152
  echo "corps de 2 Mo transmis au service / 2 MB body passed to the service"
  # MCP en ligne sans clé (initialize : rien d'anonymisé) / keyless online MCP (initialize: nothing anonymised).
  out=$(curl -fsS --max-time 30 -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"verify","version":"1"}}}' \
    "$url/mcp") || fail "MCP initialize ($url)"
  printf '%s' "$out" | grep -o '"serverInfo":{[^}]*}' || fail "MCP : pas de serverInfo ($url)"
  # Ni redirection de barre oblique ni HTTP clair / neither trailing-slash redirect nor plain HTTP.
  expect_code 404 -X POST -H 'Content-Type: application/json' -d '{"text":"x"}' "$url/v1/anonymize/text/"
  expect_code 000 "http://${url#https://}/health"
  # Une page d'un autre site ne fait pas travailler ses visiteurs / another site's page cannot use its visitors.
  expect_code 403 -X POST -H 'Sec-Fetch-Site: cross-site' -F 'file=@/etc/hostname' "$url/v1/anonymize/file"
  expect_code 404 "$url/v1/results/up_$(head -c 32 /dev/urandom | base64 | tr '+/' '-_' | tr -d '=' | cut -c1-43)"
}

# Anonymisations de contrôle : par le socket, jeton local compris, donc comptées « protocol », jamais « public ».
# Check anonymisations: through the socket, local token included, hence counted "protocol", never "public".
verify_protocol() {
  local out ticket upload result upload_id token
  step "Anonymisations de contrôle (protocole, par le socket) / check anonymisations (protocol, through the socket)"
  out=$(socket_curl -H 'Content-Type: application/json' \
    -d '{"text": "Contactez Jean Dupont au 06 12 34 56 78, IBAN FR76 3000 6000 0112 3456 7890 189."}' \
    http://localhost/v1/anonymize/text) || fail "anonymisation par le socket / through the socket"
  case $out in *Dupont*|*'06 12 34 56 78'*|*FR76*) fail "anonymisation incomplète / incomplete" ;; esac
  echo "texte anonymisé / text: ${out:0:120}"
  # Envoi hors bande de 2 Mo, aller et retour / 2 MB out-of-band upload round trip.
  upload=$(mktemp)
  python3 -c 'import sys; line = b"Contact jean.dupont@exemple.fr, 06 12 34 56 78.\n"; sys.stdout.buffer.write(line * (2_097_152 // len(line)))' >"$upload"
  ticket=$(socket_curl -H 'Content-Type: application/json' -d '{"filename": "verify.txt"}' http://localhost/v1/uploads) \
    || { rm -f "$upload"; fail "POST /v1/uploads"; }
  upload_id=$(printf '%s' "$ticket" | python3 -c 'import json, sys; print(json.load(sys.stdin)["upload_id"])')
  token=$(printf '%s' "$ticket" | python3 -c 'import json, sys; print(json.load(sys.stdin)["upload_url"].rsplit("/", 1)[1])')
  result=$(socket_curl -X PUT -H 'Content-Type: application/octet-stream' --data-binary "@$upload" \
    "http://localhost/v1/uploads/$token") || { rm -f "$upload"; fail "PUT de 2 Mo / 2 MB PUT"; }
  rm -f "$upload"
  case $result in *'"status":"ready"'*) ;; *) fail "envoi de 2 Mo non traité : ${result:0:200}" ;; esac
  out=$(socket_curl "http://localhost/v1/results/$upload_id?page=1") || fail "lecture du résultat / result read"
  case $out in *'[EMAIL_1]'*) ;; *) fail "résultat sans balise / no placeholder" ;; esac
  case $out in *'@exemple.fr'*|*'06 12 34 56 78'*) fail "résultat non anonymisé / not anonymised" ;; esac
  echo "envoi de 2 Mo : aller et retour / 2 MB upload: round trip ok"
  socket_curl -o /dev/null http://localhost/health/deep || fail "sonde profonde / deep probe"
  echo "sonde profonde / deep probe: ok"
}

# Vidéo de lancement par Nginx : plage d'octets (206, comme Safari la demande), type, en-têtes de sécurité, cache ;
# un nom hors de la liste : 404. Launch video through Nginx: byte range (206, as Safari asks), type, security headers,
# cache; a name outside the list: 404.
verify_media() {  # $1 : nom du site / site name
  local host=$1 name want headers
  for name in "${MEDIA_FILES[@]}"; do
    case $name in
      *.mp4) want=video/mp4 ;;
      *.png) want=image/png ;;
      *) want='text/plain; charset=utf-8' ;;
    esac
    headers=$(curl -sS -D - -o /dev/null --max-time 30 -H 'Range: bytes=0-99' "https://$host/media/$name" | tr -d '\r')
    printf '%s\n' "$headers" | head -1 | grep -q ' 206' \
      || fail "https://$host/media/$name : $(printf '%s\n' "$headers" | head -1) (attendu / expected 206)"
    printf '%s\n' "$headers" | grep -qi '^set-cookie:' && fail "Set-Cookie ($host, $name)"
    printf '%s\n' "$headers" | grep -qi '^content-range: bytes 0-99/' || fail "Content-Range ($host, $name)"
    printf '%s\n' "$headers" | grep -qix "content-type: $want" || fail "Content-Type ($host, $name)"
    printf '%s\n' "$headers" | grep -qi "^content-security-policy: .*media-src 'self'" || fail "CSP ($host, $name)"
    printf '%s\n' "$headers" | grep -qi '^x-content-type-options: nosniff' || fail "nosniff ($host, $name)"
    printf '%s\n' "$headers" | grep -qi '^cache-control: public, max-age=31536000, immutable' || fail "cache ($host, $name)"
  done
  expect_code 404 "https://$host/media/absent.mp4"
  echo "vidéo : ${#MEDIA_FILES[@]} fichiers, plages (206), types, en-têtes ; nom inconnu : 404 / video: ranges, types, headers"
}

verify() {
  step "Écoute réseau : seulement 22, 80 et 443 / network listeners: only 22, 80 and 443"
  local extra
  # Adresses locales, avec ou sans interface (résolveur du système : 127.0.0.53%lo:53) / loopback, with or without an
  # interface suffix (the system resolver).
  extra=$(sudo ss -tlnH | awk '{print $4}' | grep -v -E '^(127\.0\.0\.[0-9]+|\[::1\])(%[A-Za-z0-9]+)?:' \
    | grep -v -E ':(22|80|443)$' || true)
  [ -z "$extra" ] || fail "écoute inattendue / unexpected listener: $extra"
  echo "ok"
  step "Conteneur : ni init, ni clé dans l'environnement / container: no init, no key in the environment"
  [ "$(sudo docker inspect -f '{{.HostConfig.Init}}' "$CONTAINER")" != true ] || fail "init: true"
  if sudo docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$CONTAINER" | grep -q '^GDPRGUARDIAN_API_KEY'; then
    fail "clé dans l'environnement du conteneur / key in the container environment"
  fi
  sudo docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$CONTAINER" \
    | grep -q '^GDPRGUARDIAN_LOCAL_TOKEN_SHA256=' || fail "jeton local non configuré / local token not configured"
  echo "ok"
  step "Aucune adresse vers le disque : swap, pare-feu / no address to disk: swap, firewall"
  [ "$(systemctl show -p MemorySwapMax --value nginx)" = 0 ] || fail "nginx peut aller en swap / nginx may swap"
  if command -v ufw >/dev/null 2>&1; then
    sudo ufw status verbose | grep -qi '^logging: off' || fail "journal ufw actif / ufw logging on"
    if sudo grep -qs 'SRC=' /var/log/ufw.log; then fail "adresses dans /var/log/ufw.log / addresses in ufw.log"; fi
  fi
  if [ -n "$(swapon --show --noheadings 2>/dev/null)" ]; then
    echo "swap présent : nginx (MemorySwapMax=0) et le conteneur (memswap_limit) n'y vont pas / swap present: nginx and the container never use it"
  fi
  echo "ok"
  step "Nginx : la configuration installée est celle qui tourne / the installed configuration is the running one"
  # Un rechargement refusé garde les anciens processus de travail : ils sont alors plus vieux que nos fichiers.
  # A refused reload keeps the old worker processes: they are then older than our files.
  local master newest now age
  master=$(systemctl show -p MainPID --value nginx)
  [ "${master:-0}" -gt 0 ] || fail "nginx arrêté / nginx stopped"
  newest=$(sudo stat -c %Y "$NGINX_MAIN" /etc/nginx/conf.d/00-gdprguardian.conf /etc/nginx/snippets/gdprguardian-*.conf \
    /etc/nginx/sites-available/gdprguardian | sort -n | tail -1)
  now=$(date +%s)
  for age in $(ps -o etimes= --ppid "$master"); do
    [ $((now - age + 1)) -ge "$newest" ] || fail "configuration installée non appliquée (rechargement refusé ?) : sudo systemctl restart nginx / installed configuration not applied"
  done
  echo "ok"
  local url name host sse headers out errors
  for url in "${API_NAMES[@]/#/https://}"; do
    verify_api "$url"
  done
  verify_protocol
  step "Site"
  for name in "${SITE_NAMES[@]}"; do
    points_here "$name" || { echo "$name : DNS pas encore / not yet"; continue; }
    case $(http_code "https://$name/") in
      200|301) echo "$name : ok" ;;
      *) fail "https://$name/ : $(http_code "https://$name/")" ;;
    esac
  done
  for host in gardienrgpd.fr gdprguardian.com; do
    points_here "$host" || continue
    step "https://$host : page, cockpit (/v1/), flux, security.txt, vidéo / page, cockpit, stream, security.txt, video"
    headers=$(curl -sS -D - -o /dev/null "https://$host/" | tr -d '\r')
    printf '%s\n' "$headers" | head -1
    printf '%s\n' "$headers" | grep -qi '^set-cookie:' && fail "Set-Cookie ($host)"
    echo "aucun cookie / no cookie"
    # Contrat du cockpit : /v1/ même origine, vers le service (corps refusé après lecture : rien de compté) ; refusé
    # depuis une autre page ; fermé en HTTP clair. Cockpit contract: same-origin /v1/ to the service (body refused
    # after reading: nothing counted); refused from another page; closed over plain HTTP.
    expect_refused_body "https://$host/v1/anonymize/text" 10
    expect_code 403 -X POST -H 'Sec-Fetch-Site: cross-site' -H 'Content-Type: application/json' -d '{"text":"x"}' \
      "https://$host/v1/anonymize/text"
    expect_code 000 -X POST -H 'Content-Type: application/json' -d '{"text":"x"}' "http://$host/v1/anonymize/text"
    echo "cockpit /v1/ : ok"
    curl -fsS "https://$host/api/stats" | python3 -c 'import json, sys
stats = json.load(sys.stdin)
print("api/stats :", ", ".join(f"{key}={stats.get(key)}" for key in ("uses_hour", "docs_total", "docs_protocol", "visitors_total",
                                                                      "cpu_percent", "since")))' || fail "api/stats ($host)"
    # Premier événement du flux en moins de 5 s / first stream event within 5 s.
    sse=$(curl -sN --max-time 5 "https://$host/api/live" 2>/dev/null || true)
    printf '%s\n' "$sse" | grep -q '^event: stats$' || fail "aucun événement en 5 s / no event within 5 s ($host)"
    echo "api/live : événement « stats » reçu / \"stats\" event received"
    curl -fsS "https://$host/.well-known/security.txt" | grep -E '^(Contact|Expires):' || fail "security.txt ($host)"
    verify_media "$host"
  done
  step "Nom inconnu refusé / unknown name refused"
  expect_code 000 -k --resolve "intrus.example:443:127.0.0.1" https://intrus.example/
  # HTTP/1.1 : le serveur par défaut ferme (444). HTTP/2 : Nginx refuse un Host autre que le nom TLS (421).
  # HTTP/1.1: the default server closes (444). HTTP/2: Nginx refuses a Host other than the TLS name (421).
  expect_code 000 --http1.1 -H 'Host: intrus.example' "https://${API_NAMES[0]}/"
  case $(http_code --http2 -H 'Host: intrus.example' "https://${API_NAMES[0]}/") in
    000|421) ;;
    *) fail "Host inconnu en HTTP/2 accepté / unknown Host accepted over HTTP/2" ;;
  esac
  echo "SNI inconnu et Host inconnu : refusés / unknown SNI and unknown Host: refused"
  step "Rafale depuis une adresse : 429 / burst from one address: 429"
  # 100 requêtes sur une connexion gardée ouverte : bien au-delà de la rafale de Nginx et du service.
  # 100 requests over one kept-alive connection: well beyond the burst of Nginx and of the service.
  local burst=()
  for _ in $(seq 1 100); do burst+=("https://${API_NAMES[0]}/health"); done
  out=$(curl -s --max-time 60 "${burst[@]}" || true)
  case $out in *rate_limited*) ;; *) fail "aucun 429 après 100 requêtes / no 429 after 100 requests" ;; esac
  headers=$(curl -sS -D - -o /dev/null "https://${API_NAMES[0]}/health" | tr -d '\r')
  echo "429 obtenu / 429 received ; $(printf '%s\n' "$headers" | grep -i -e '^retry-after:' -e '^ratelimit:' | tr '\n' ' ')"
  step "Journaux de Nginx : aucune adresse de client / Nginx logs: no client address"
  local mine4
  mine4=$(ip -4 -o addr show scope global | awk '{print $4}' | cut -d/ -f1 | head -1)
  if sudo grep -qs -e 'client: ' -e "$mine4" /var/log/nginx/*.log; then
    fail "adresse de client dans un journal / client address in a log"
  fi
  echo "aucune / none"
  step "Limiteur : aucune erreur interne (il laisse passer en cas d'erreur) / limiter: no internal error (fails open)"
  errors=$(socket_curl http://localhost/status | python3 -c 'import json, sys; print(json.load(sys.stdin)["counters"]["errors"])') \
    || fail "/status"
  [ "$errors" = 0 ] || fail "erreurs internes du limiteur / limiter internal errors: $errors"
  echo "0"
  step "Sonde de santé / health probe"
  systemctl is-active -q gdprguardian-watchdog.timer || fail "gdprguardian-watchdog.timer inactif / inactive"
  echo "gdprguardian-watchdog.timer actif / active"
  step "Mises à jour automatiques / automatic updates"
  updates_check
}

case "${1:-}" in
  base) base ;;
  image) image "${2:-}" ;;
  cert) cert ;;
  https) https ;;
  site) site "${2:-}" "${3:-}" ;;
  start) start ;;
  verify) verify ;;
  updates) updates ;;
  *) sed -n '2,27p' "$0"; exit 2 ;;
esac
