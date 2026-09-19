# Durable certificates — one wildcard instead of a manual step per tenant

**Written:** 12 Sep 2026 · **Asked for by:** Surbhi
**Status:** script written (`deploy/setup_wildcard_cert.sh`), **blocked on one
decision that is Surbhi's** — see §3.

---

## 1. Why this is worth doing

Today `deploy/add_tenant_cert.sh` must be run **by hand for every new tenant**.
HTTP-01 can only prove a name that already answers on the internet, so the
certificate cannot be issued until after the site exists.

That manual step is exactly why `ppj.dev.alvoraa.co` was provisioned, looked
healthy, and had **no usable certificate** — which would have killed the phone
demo outright, because a browser gives a page no camera and no GPS unless it
arrived over HTTPS on a name the certificate covers.

It also carries limits that get worse with every customer:

| Limit | Today | With a wildcard |
|---|---|---|
| Names per certificate | 100 — so 100 tenants, ever | No limit |
| Duplicate certificates per week | 5 — six new tenants in a week locks you out | Not reached |
| Hostname must serve HTTP before issuance | Yes | No |
| A retired tenant breaks renewal for everyone | Yes — the script carries a `RETIRED` list to work around it | No |
| Manual step per tenant | Yes | **None** |

## 2. The one detail that is easy to get wrong

**A wildcard covers exactly one label.** Verified, not assumed:

| Pattern | Host | Covered |
|---|---|---|
| `*.alvoraa.co` | `demo.alvoraa.co` | ✅ |
| `*.alvoraa.co` | `ppj.dev.alvoraa.co` | ❌ |
| `*.dev.alvoraa.co` | `ppj.dev.alvoraa.co` | ✅ |

Production tenants are `<tenant>.alvoraa.co`; dev tenants are
`<tenant>.dev.alvoraa.co`. So the certificate needs **three** names:

```
alvoraa.co   *.alvoraa.co   *.dev.alvoraa.co
```

Asking for only `*.alvoraa.co` would be all of this work and still no
certificate for a dev tenant.

## 3. ⚠ The blocker — DNS is on GoDaddy

A wildcard requires a **DNS-01** challenge, which means certbot must write a TXT
record into the zone. Measured on the server today:

- Nameservers: `ns07.domaincontrol.com`, `ns08.domaincontrol.com` — **GoDaddy**
- certbot 2.9.0, installed from apt
- Plugins present: `standalone`, `webroot` only — **no DNS plugin**
- Renewal already automated by `certbot.timer` ✅

**GoDaddy has no official certbot DNS plugin.** There are community ones, and
GoDaddy's own API has in recent years been restricted to accounts holding a
minimum number of domains or a paid Discount Domain Club membership.
`[verify — check whether the API is available on this specific account before
committing to option B]`

### The three ways forward

| | Option A — move DNS to Cloudflare **(recommended)** | Option B — GoDaddy API | Option C — automate what we have |
|---|---|---|---|
| What changes | Nameservers point at Cloudflare. Domain stays registered with GoDaddy. | Install a community plugin, get a GoDaddy API key | Call `add_tenant_cert.sh` from provisioning |
| Official plugin | ✅ `python3-certbot-dns-cloudflare` | ❌ third party | n/a |
| Cost | Free | Possibly a paid GoDaddy tier | Free |
| Gets wildcards | ✅ | ✅ | ❌ |
| Removes the 100-tenant ceiling | ✅ | ✅ | ❌ |
| Risk | DNS cutover — do it at a quiet hour; records must be copied exactly first | Depends on an unofficial plugin at renewal time, unattended, at 3am | Low, but keeps every limit in §1 |
| Effort | ~1 hour, plus propagation | ~1 hour if the API is available | ~30 min |

**Recommendation: A.** The plugin is maintained by the certbot project, which
matters most for the thing nobody watches — the unattended renewal 60 days from
now. Option C is a reasonable stopgap for this week and can be done *as well*.

## 4. What is already written

`deploy/setup_wildcard_cert.sh` — assumes option A, and will not run until the
prerequisites are real. It deliberately:

- **refuses to start** without the plugin or a `600`-mode credentials file
- asks for a **scoped token** (Zone / DNS / Edit on `alvoraa.co` only), never the
  Global API Key, which can do anything to the account
- waits 30s for propagation, because a TXT record checked too early fails the
  whole order and wastes a rate-limit slot
- **issues but does not switch nginx over.** Swapping the live certificate is a
  separate, reviewable step; doing both in one run means a mistake takes every
  site down at once with nothing to fall back to.

## 5. Steps, when the decision is made

1. Create the Cloudflare zone for `alvoraa.co`, and **copy every existing record
   exactly**, including the ones nobody remembers — mail, TXT, SPF, DKIM. Getting
   this wrong breaks email, not just the website.
2. Lower the TTL on the current provider first, a day ahead, so a mistake is
   quick to undo.
3. Change nameservers at GoDaddy. Wait for propagation.
4. `apt-get install -y python3-certbot-dns-cloudflare`
5. Create `/root/.secrets/cloudflare.ini`, `chmod 600`.
6. `deploy/setup_wildcard_cert.sh --dry-run` — must pass before the real run.
7. `deploy/setup_wildcard_cert.sh`
8. Point `ssl_certificate` / `ssl_certificate_key` in `deploy/nginx.conf` at
   `/etc/letsencrypt/live/alvoraa-wildcard/`.
9. `nginx -t`, then `nginx -s reload`.
10. Test a hostname that was **never** on the old certificate — that is the only
    test that proves the wildcard is doing the work.
11. Leave the old certificate to expire on its own. Do not delete it by hand.
12. Then delete `add_tenant_cert.sh` and the `RETIRED` list it carries, and
    remove the manual step from the provisioning runbook.

## 6. Until then

Every new tenant still needs this run by hand after provisioning:

```
ssh root@<server> "bash /opt/build/deploy/add_tenant_cert.sh <host>"
```

Worth adding to the tenant-provisioning checklist as an explicit step, rather
than leaving it as something one person remembers.
