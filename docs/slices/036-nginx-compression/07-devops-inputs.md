# 036 — Compression in nginx (OPS-26): DevOps inputs

One nginx container, `compose-nginx-1`, serves production (`alvoraa.co`,
`dtc.alvoraa.co`, `aahr.alvoraa.co`) and dev from one file, `deploy/nginx.conf`.
A deploy to dev restarts that container, so **this change reaches production the
moment it reaches dev**. Nothing here has been pushed. Everything below was built
and measured on this PC, in throwaway containers, against the local bench.

**I advise. Every decision below is yours.**

---

## §5 Release readiness — 2026-09-22

### What changed

| File | Change |
|---|---|
| `deploy/nginx.conf` | gzip switched on for text answers; `gzip off` on `location /` and `location /files/`; one new location naming the pages whose HTML may be compressed. Same in both server blocks. |
| `scripts/check_nginx_conf.py` | New rule 5 — a text check in CI that the `gzip off` lines stay, that the compressed-page lists in the two server blocks match, and that no already-compressed type is listed. |
| `scripts/check_nginx_forwarded.sh` | New section 6 — proves in throwaway containers what is compressed and what is not. `/hrms-employee` added to the forged-address checks. |

The directives, and why:

| Directive | Value | Why |
|---|---|---|
| `gzip` | `on` | Frappe compresses nothing itself (measured: no `Content-Encoding` even when asked). |
| `gzip_comp_level` | `5` | Measured on the real 1.05 MB page: level 5 → 235 KB, level 6 → 231 KB at twice the CPU, level 9 → 229 KB at three times. |
| `gzip_min_length` | `1024` | Below ~1 KB the gzip wrapper costs more than it saves. |
| `gzip_vary` | `on` | Sends `Vary: Accept-Encoding`, so a cache in front never hands a squeezed copy to a client that cannot read it. |
| `gzip_proxied` | `any` | This is about the request, not `proxy_pass`. If Cloudflare's proxy is ever switched on, requests arrive with a `Via` header and the default (`off`) would quietly stop all compression. |
| `gzip_types` | CSS, JS, JSON, SVG, XML, `eot/ttf/otf` | Text only. Images, PDFs, zips and woff/woff2 are left out — they are compressed already. HTML is always included by nginx and cannot be listed. |
| `gzip_static` | not used | Frappe's build writes no `.gz` files (checked in the `dev-3830ed3` image: zero). It would only make nginx look for files that never exist. |

### Measured, through the real config, on the local bench (2026-09-22)

Two throwaway nginx containers (`nginx:1.31.6-alpine`, the version production
runs), one with today's `origin/dev` config, one with the new one, both in front
of `hrlocal-bench`. Bytes on the wire, signed in, `Accept-Encoding: gzip`.

| Answer | Before | After | Saved |
|---|---:|---:|---:|
| `/hrms-employee` (the landing page) | 1,070,629 | 235,463 | 78% |
| `/desk` | 517,021 | 64,260 | 88% |
| `/checkin` (the field app) | 76,177 | 22,344 | 71% |
| `/alvoraa-login` (signed out) | 175,626 | 28,591 | 84% |
| `frappe-web.bundle...js` | 824,974 | 249,747 | 70% |
| `website.bundle...css` | 468,550 | 75,474 | 84% |
| `lucide/icons.svg` | 450,258 | 78,959 | 82% |
| A 50-row Employee JSON answer | 6,260 | 1,154 | 82% |
| `/hrms-employee/made-up` (a 404) | 9,954 | 9,954 | 0% — on purpose |

**Whole first screen** (page + both stylesheets + the web bundle + the four
preloaded icon sets): **3,087,611 → 720,759 bytes, 77% less.** On a 3G phone at
about 1.6 Mbit/s that is roughly **15.4 s → 3.6 s** of download time (estimate:
bytes ÷ throughput, no allowance for latency or render). Return visits keep the
assets in cache and pay only the HTML: 1.05 MB → 235 KB.

Browser-facing headers confirmed on the compressed answers:
`Content-Encoding: gzip` and `Vary: Accept-Encoding`. A client that does not ask
for gzip still gets plain bytes.

Against the NFR budget (`nfr-budget.md`: ≤ 300 ms server, ≤ 2.5 s on 3G): this
does not reach 2.5 s on its own — the page is still 235 KB of HTML that Frappe
has to build — but it removes about four fifths of the bytes. The remaining gap
belongs to the slice 009 redesign.

### BREACH — what applies here, and what I did about it

**It applies, on one kind of page: the "page not found" page.** BREACH is an
attack on compressed pages. If one answer holds both a secret and text the
attacker chose, someone who can watch the encrypted traffic can learn the secret
from how the answer's size changes as they vary their text.

Measured on the bench, signed in:

- Every signed-in page carries the session's CSRF token — the code that proves a
  form came from our own page (`frappe.csrf_token = "<56 hex characters>"`).
- Normal pages ignore the address: `/hrms-employee?q=<made-up word>` and every
  other portal page never write the word into the HTML. Ten routes checked.
- Frappe's 404 page **does** repeat the address: `<div id="page-404"
  data-path="hrms-employee/<made-up word>">` — next to the token. Both
  ingredients, one answer.
- `/api/` answers often repeat what was sent, but carry no token. No secret, no
  oracle.

**Mitigation chosen: compress HTML only on named pages, matched exactly.**
Anything longer — which is what a 404 always is — falls through to `location /`,
where gzip is off. `/files/` is off for the same reason. This keeps the whole
1.05 MB saving on the landing page and is safe by default: a new page is simply
sent uncompressed until someone checks it and adds it to the list.

Why not simply accept the risk? It is genuinely hard to exploit — the session
cookie is `SameSite=Lax`, so a request from a stranger's website carries no
cookie and gets no token, and the attacker also needs to watch the traffic. But
all tenants share `alvoraa.co`, so a page on one tenant is "same site" as
another tenant, and cookies **are** sent on those requests. A tenant
administrator can publish a page with their own JavaScript. That is a thin but
real path, and closing it cost one location block.

What is left, and I am not hiding it: a handful of Frappe screens under `/api/`
render HTML with the token (for example the OAuth "Confirm Access" screen and
the unsubscribe page). I checked the ones I could reach — none repeated my
input — but I did not audit all 24 places Frappe can render such a page. They
are rare, they need a signed-in victim, and the attacker still needs to watch
the network. **OPS-26c** below offers the alternative if you want that closed too.

### Proof — what I ran, and the result

| Check | Result |
|---|---|
| `python scripts/check_nginx_conf.py` | **OK** on the new file. |
| Same check, four deliberately broken copies (a missing `gzip off`, an image type in `gzip_types`, the two server blocks disagreeing, dev's `location /` compressed) | **Fails each one, with the right message.** |
| Same check on today's `origin/dev` file | **OK** — the new rules only apply once gzip is on. |
| `scripts/check_nginx_parses.sh` with the certificate layout mocked (self-signed `alvoraa-wildcard` and `alvox.in`), on `nginx:1.31.6-alpine` (the server's version) and on `nginx:alpine` | **OK** on both. A copy with one missing semicolon is refused. |
| `scripts/check_nginx_forwarded.sh` on the new file | **ALL PASSED** — 54 checks: forged addresses still dropped on every route, Cloudflare header still ignored, all three login paths still rate-limited, and the new compression checks. |
| The same script against today's `origin/dev` file and against a broken copy | Fails exactly where it should — the new section is not a rubber stamp. |
| `python scripts/check_app_integrity.py` | see below |

No server, dev site, production site or local bench container was changed. Every
throwaway container was removed.

### Recommendations

| ID | Recommendation | Why | Cost of ignoring it | Weight | Decision |
|---|---|---|---|---|---|
| OPS-26a | Land this change in a quiet window you choose — it restarts the shared nginx and changes production's proxy at the same moment as dev's | One nginx serves both; the dev deploy restarts it | Two live tenants see a ~2 second proxy restart at an unplanned time | Recommend | |
| OPS-26b | Keep the compressed-page list exact-match, and check a new page for echoed input before adding it | A page that repeats address text next to the token is a BREACH oracle | A future page silently becomes an oracle | Recommend | |
| OPS-26c | If the residual `/api/` HTML screens worry you, turn gzip off for `/api/` as well | Closes the last HTML-with-token path | ~82% more bytes on every API answer | Consider | |
| OPS-26d | Pin the nginx image (`nginx:1.31.6-alpine`) instead of the floating `nginx:alpine` in `docker-compose.app.yml` | Today the tag decides the nginx version at recreate time; the deploy tests one version and may run another | A future nginx behaves differently from the one that passed the gate | Consider | |
| OPS-26e | Later: have the image build write `.gz` files and switch on `gzip_static` for `/assets/` | Saves ~50 ms of CPU per uncached bundle | Slightly more CPU per first-time visitor; no user-visible harm | FYI | |
| OPS-26f | Do not add Brotli | It needs a custom nginx image; gzip already removes ~78% | ~15% more bytes than Brotli would give | FYI | |

### How to land it safely — for you to approve, and for you to run

1. **Pick a quiet window.** India evening or a weekend: two live tenants
   (`dtc.alvoraa.co`, `aahr.alvoraa.co`) share this proxy.
2. **Merge this branch into `dev` and push it** — your word, not mine. The
   deploy's own nginx gate runs `scripts/check_nginx_parses.sh` on the file from
   git before anything restarts, and again on the file on disk.
3. **Optional belt and braces, before the push** — read-only on the server:
   ```bash
   ssh -o IdentitiesOnly=yes -i ~/.ssh/id_ed25519 root@100.127.29.62
   cd /var/www/html/hr-app && git fetch origin
   TMP=$(mktemp -d)
   git show origin/dev:deploy/nginx.conf > $TMP/nginx.conf
   bash scripts/check_nginx_parses.sh $TMP/nginx.conf /etc/letsencrypt
   ```
   It only starts a throwaway container. If it does not say OK, do not deploy.
4. **Watch, for about five minutes after the deploy.** From your PC:
   ```bash
   for h in alvoraa.co dtc.alvoraa.co aahr.alvoraa.co dev.alvoraa.co; do
     curl -s -o /dev/null -w "$h %{http_code} %{size_download}\n" \
       -H 'Accept-Encoding: gzip' https://$h/alvoraa-login
   done
   ```
   Expect: every host `200`, and the sizes far smaller than before. Measured
   here, the sign-in page goes from 175,626 to 28,591 bytes. Then sign in to one tenant and
   confirm the landing page loads normally, with
   `Content-Encoding: gzip` on the page and on the `/assets/` files.
5. **Rollback, if anything looks wrong.** Revert the one commit on `dev` and
   deploy again; the deploy restarts nginx with the old file:
   ```bash
   git revert <commit> && git push origin dev
   ```
   Faster, by hand on the server, only if a site is actually down: check out the
   previous `deploy/nginx.conf`, run the parse check, then
   `docker restart compose-nginx-1`.
6. **What to watch for over the next day:** any report of a blank or broken
   page, 502s in `docker logs compose-nginx-1`, and CPU on the box. Compression
   costs about 50 ms of CPU for a 1 MB page; at two tenants that is noise.

### Capacity

No new service, no new storage, no new spend. CPU per request rises slightly and
bandwidth out drops by about three quarters.
