#!/usr/bin/env bash
#
# scripts/check_nginx_forwarded.sh [path/to/nginx.conf]
#
# Tests deploy/nginx.conf in THROWAWAY containers on this PC, before anybody
# pushes it. One nginx serves production and dev, and a dev deploy restarts it
# with this file - so a typing mistake takes every site down. Run this first.
#
# It never touches the local bench, compose-nginx-1, dev or production.
#
# What it checks (slice 014, OPS-19):
#   1. `nginx -t`: the file parses, with the real TLS lines (self-signed certs).
#   2. the realip module is built into the image (the Cloudflare lines need it).
#   3. a caller-sent X-Forwarded-For never reaches Frappe: the backend sees ONE
#      address, the real one, whatever the caller forges. Frappe keys its rate
#      limits on the first address, so one address = one bucket.
#   4. a caller-sent CF-Connecting-IP is ignored when the caller is not Cloudflare.
#   5. every login path (/api/method/login, /api/v1/..., /api/v2/...) is under
#      the 5-a-minute login limit.
#   6. compression (slice 036, OPS-26): the named pages, /api/ and /assets/ text
#      are gzipped with "Vary: Accept-Encoding"; "page not found" addresses,
#      /files/ and images are NOT (BREACH - see deploy/nginx.conf).
#
# Needs: docker, openssl. Exit code 0 = all passed.

set -uo pipefail

CONF="${1:-deploy/nginx.conf}"
IMAGE="nginx:alpine"
RUN_ID="nginxcheck$$"
NET="$RUN_ID-net"
FAILED=0

pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; FAILED=1; }

# Docker Desktop on Windows needs Windows paths for bind mounts.
winpath() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else echo "$1"; fi; }
export MSYS_NO_PATHCONV=1

[ -f "$CONF" ] || { echo "no such file: $CONF"; exit 2; }
WORK="$(mktemp -d)"
cleanup() {
	docker rm -f "$RUN_ID-proxy" "$RUN_ID-echo" >/dev/null 2>&1
	docker network rm "$NET" >/dev/null 2>&1
	rm -rf "$WORK"
}
trap cleanup EXIT

mkdir -p "$WORK/echo" "$WORK/assets"
# Files for /assets/: text that must be compressed, an image that must not.
# Both well over gzip_min_length, so size is never the reason.
awk 'BEGIN { for (i = 0; i < 200; i++) print "var line" i " = 1;" }' > "$WORK/assets/app.js"
head -c 4096 /dev/urandom > "$WORK/assets/logo.png"
# A config of our own, so a broken OPENSSL_CONF on this PC cannot stop the run.
printf '[req]\ndistinguished_name = dn\n[dn]\n' > "$WORK/openssl.cnf"
# One self-signed certificate for every certificate folder the file names
# (alvoraa-wildcard, alvox.in, ...), so a renamed certificate is tested too.
CERT_NAMES="$(sed -n 's#.*ssl_certificate[^/]*/etc/nginx/ssl/live/\([^/]*\)/.*#\1#p' "$CONF" | sort -u)"
[ -n "$CERT_NAMES" ] || { echo "no ssl_certificate lines found in $CONF"; exit 2; }
for d in $CERT_NAMES; do
	mkdir -p "$WORK/ssl/live/$d"
	openssl req -config "$(winpath "$WORK/openssl.cnf")" -x509 -nodes -newkey rsa:2048 -days 1 -subj "/CN=$d" \
		-keyout "$(winpath "$WORK/ssl/live/$d/privkey.pem")" \
		-out "$(winpath "$WORK/ssl/live/$d/fullchain.pem")" >/dev/null 2>&1 \
		|| { echo "could not make a test certificate with openssl"; exit 2; }
done
cp "$CONF" "$WORK/default.conf"

# A stand-in for Frappe and socket.io: answers with the headers it was given.
cat > "$WORK/echo/default.conf" <<'EOF'
server {
    listen 8000;
    listen 9000;
    location / {
        # HTML and over 1 KB, like a real Frappe page, so the proxy's gzip rules
        # decide. The padding is on its own line; the checks read line one.
        default_type text/html;
        return 200 "xff=[$http_x_forwarded_for] real=[$http_x_real_ip] peer=[$remote_addr]\n<!-- padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding padding -->\n";
    }
}
EOF

W_CONF="$(winpath "$WORK/default.conf")"
W_SSL="$(winpath "$WORK/ssl")"
W_ECHO="$(winpath "$WORK/echo/default.conf")"
W_ASSETS="$(winpath "$WORK/assets")"

# ── 1. syntax ────────────────────────────────────────────────────────────────
T_OUT="$(docker run --rm \
	--add-host compose-backend-1:127.0.0.1 --add-host compose-socketio-1:127.0.0.1 \
	--add-host devstack-backend-1:127.0.0.1 --add-host devstack-socketio-1:127.0.0.1 \
	-v "$W_CONF:/etc/nginx/conf.d/default.conf:ro" -v "$W_SSL:/etc/nginx/ssl:ro" \
	"$IMAGE" nginx -t 2>&1)"
echo "$T_OUT" | sed 's/^/      /'
if echo "$T_OUT" | grep -q "syntax is ok" && echo "$T_OUT" | grep -q "test is successful"; then
	pass "nginx -t"
else
	fail "nginx -t"
	exit 1
fi

# ── 2. realip module ─────────────────────────────────────────────────────────
if docker run --rm "$IMAGE" nginx -V 2>&1 | grep -q -- "--with-http_realip_module"; then
	pass "realip module is built into $IMAGE"
else
	fail "realip module missing from $IMAGE"
fi

# ── the throwaway stack ─────────────────────────────────────────────────────
docker network create "$NET" >/dev/null
docker run -d --name "$RUN_ID-echo" --network "$NET" \
	--network-alias compose-backend-1 --network-alias compose-socketio-1 \
	--network-alias devstack-backend-1 --network-alias devstack-socketio-1 \
	-v "$W_ECHO:/etc/nginx/conf.d/default.conf:ro" "$IMAGE" >/dev/null
sleep 1
docker run -d --name "$RUN_ID-proxy" --network "$NET" \
	-v "$W_CONF:/etc/nginx/conf.d/default.conf:ro" -v "$W_SSL:/etc/nginx/ssl:ro" \
	-v "$W_ASSETS:/home/frappe/frappe-bench/sites/assets:ro" -v "$W_ASSETS:/devstack-sites/assets:ro" \
	"$IMAGE" >/dev/null
sleep 2

# Requests are sent from a third container, so the proxy sees a real, separate peer.
ask() {  # ask HOST PATH [extra wget args...]
	local host="$1" path="$2"; shift 2
	docker run --rm --network "$NET" "$IMAGE" \
		wget -q -O - --no-check-certificate --header "Host: $host" "$@" \
		"https://$RUN_ID-proxy$path" 2>&1
}
status_of() {  # status_of HOST PATH -> HTTP status of a POST
	docker run --rm --network "$NET" "$IMAGE" sh -c \
		"wget -S -O /dev/null --no-check-certificate --header 'Host: $1' --post-data 'x=1' 'https://$RUN_ID-proxy$2' 2>&1 | grep -o 'HTTP/1.[01] [0-9][0-9][0-9]' | tail -1 | cut -d' ' -f2"
}

# ── 3. forged X-Forwarded-For ────────────────────────────────────────────────
for host in alvoraa.co dev.alvoraa.co; do
	# Frappe's rate-limit bucket is keyed on the FIRST address it receives.
	firsts="" forged=0 several=0
	for i in 1 2 3 4 5 6 7 8 9 10 11; do
		out="$(ask "$host" /api/method/ping --header "X-Forwarded-For: 10.66.$i.$i")"
		xff="$(echo "$out" | sed -n 's/.*xff=\[\([^]]*\)\].*/\1/p')"
		firsts="$firsts $(echo "$xff" | cut -d, -f1 | tr -d ' ')"
		case "$xff" in *10.66.*) forged=$((forged + 1)) ;; esac
		case "$xff" in *,*) several=$((several + 1)) ;; esac
	done
	if [ "$forged" = "0" ]; then pass "$host: no forged address reached the backend"
	else fail "$host: a forged address reached the backend in $forged of 11 requests (last xff=[$xff])"; fi
	if [ "$several" = "0" ]; then pass "$host: the backend always got exactly one address"
	else fail "$host: the backend got a list of addresses in $several of 11 requests"; fi
	distinct="$(echo "$firsts" | tr ' ' '\n' | grep -v '^$' | sort -u | wc -l | tr -d ' ')"
	if [ "$distinct" = "1" ]; then
		pass "$host: 11 different forged values -> one rate-limit bucket ($(echo $firsts | cut -d' ' -f1))"
	else
		fail "$host: 11 different forged values -> $distinct rate-limit buckets"
	fi
	for path in /files/x /socket.io/ /some/page /hrms-employee; do
		out="$(ask "$host" "$path" --header "X-Forwarded-For: 10.66.0.1")"
		case "$out" in
			*10.66.0.1*) fail "$host$path: forged address reached the backend" ;;
			*xff=*) pass "$host$path: forged address dropped" ;;
			*) fail "$host$path: no answer: $out" ;;
		esac
	done
done

# ── 4. forged CF-Connecting-IP from a non-Cloudflare caller ──────────────────
out="$(ask alvoraa.co /api/method/ping --header "CF-Connecting-IP: 10.77.7.7")"
case "$out" in
	*10.77.7.7*) fail "CF-Connecting-IP from a non-Cloudflare caller was trusted: $out" ;;
	*xff=*) pass "CF-Connecting-IP from a non-Cloudflare caller is ignored" ;;
	*) fail "no answer: $out" ;;
esac

# ── 6. compression: on where it is safe, off where it is not ───────────────
# Runs before 5 on purpose: 5 uses up this address's login allowance, and
# nothing here touches a login path.
header_of() {  # header_of HOST PATH NAME [gzip] -> that response header's value
	local host="$1" path="$2" name="$3" ae=""
	[ "${4:-}" = "gzip" ] && ae="--header 'Accept-Encoding: gzip'"
	docker run --rm --network "$NET" "$IMAGE" sh -c \
		"wget -S -O /dev/null --no-check-certificate --header 'Host: $host' $ae 'https://$RUN_ID-proxy$path' 2>&1" \
		| tr -d '\r' | sed -n "s/^ *$name: *//Ip" | tail -1
}
for host in alvoraa.co dev.alvoraa.co; do
	# Pages named in nginx.conf, the API, and text assets: compressed.
	for path in /hrms-employee "/hrms-employee?q=x" /desk /desk/employee/EMP-1 / /checkin /api/method/ping /assets/app.js; do
		enc="$(header_of "$host" "$path" Content-Encoding gzip)"
		if [ "$enc" = "gzip" ]; then pass "$host$path: compressed"
		else fail "$host$path: NOT compressed (Content-Encoding=[$enc])"; fi
	done
	vary="$(header_of "$host" /hrms-employee Vary gzip)"
	case "$vary" in
		*Accept-Encoding*) pass "$host/hrms-employee: Vary: $vary" ;;
		*) fail "$host/hrms-employee: no Vary: Accept-Encoding (got [$vary])" ;;
	esac
	# Addresses that end in "page not found" (which repeats the address next
	# to the CSRF token), files, and images: never compressed.
	for path in /hrms-employee/made-up /made-up-page /desk-made-up /files/x /assets/logo.png; do
		enc="$(header_of "$host" "$path" Content-Encoding gzip)"
		if [ -z "$enc" ]; then pass "$host$path: not compressed"
		else fail "$host$path: compressed (Content-Encoding=[$enc]) - BREACH risk or wasted CPU"; fi
	done
	# A client that does not ask for gzip gets plain bytes.
	enc="$(header_of "$host" /hrms-employee Content-Encoding)"
	if [ -z "$enc" ]; then pass "$host/hrms-employee: plain when gzip is not asked for"
	else fail "$host/hrms-employee: compressed although the client did not ask"; fi
done

# ── 5. every login path is under the login limit (5 a minute, burst 3) ──────
for host in alvoraa.co dev.alvoraa.co; do
	for path in /api/method/login /api/v1/method/login /api/v2/method/login; do
		# Every login path shares one bucket per address. A path outside the zone
		# can never answer 429, so a 429 proves the path is covered.
		codes=""
		for i in 1 2 3 4 5 6 7; do codes="$codes $(status_of "$host" "$path")"; done
		case "$codes" in
			*429*) pass "$host$path limited:$codes" ;;
			*) fail "$host$path NOT limited:$codes" ;;
		esac
		sleep 2
	done
done

if [ "$FAILED" = "0" ]; then echo "ALL PASSED"; else echo "SOME CHECKS FAILED"; fi
exit "$FAILED"
