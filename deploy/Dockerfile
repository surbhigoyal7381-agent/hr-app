# ── Kinexus HRMS – immutable application image ──────────────────────────────
#
# Builds the complete Frappe bench with all twelve apps and pre-built assets
# (frappe, erpnext, india_compliance, crm, frappe_whatsapp, payments, lms,
# telephony, helpdesk, hrms, alvoraa_goals, alvoraa_portal). ONE image, run with
# five different commands (web / socketio / scheduler / worker / provisioner).
# See ARCHITECTURE.md §5 and §12.1.
#
# Build:
#   docker buildx build --platform linux/amd64,linux/arm64 \
#     -f deploy/Dockerfile -t ghcr.io/<org>/alvoraa-app:sha-abc1234 .
#
# The build context is the REPO ROOT (not deploy/), because the three
# first-party apps are copied out of this repo — that is what closes gap G4,
# where production silently ran upstream frappe/hrms instead of this fork.
#
# NOTE: `hrms/frappe-ui` was once a git submodule. It is not any more (there is
# no .gitmodules), so a plain clone builds. Corrected in slice 040.
#
# Optimisation left on the table: a two-stage build using frappe_docker's
# `frappe/base` as the runtime layer produces a much smaller image. It requires
# the builder and runtime images to agree on Python/glibc. Do that once the
# framework version is pinned (ARCHITECTURE.md §21 decision 6).

FROM frappe/bench:latest

# ── The framework, pinned to release TAGS (ALV-156, slice 055) ──────────────
#
# These three were `version-16` - a MOVING branch. Two builds of the same commit
# of our code could contain different Frappe, different ERPNext and different
# India Compliance, and nothing in the repository recorded which one an image got.
# Measured on 2026-09-27: production (prod-65878e8, built 20 Sep) ran Frappe
# v16.34.0 / ERPNext v16.35.0 / India Compliance v16.9.1, while dev (dev-3bb22ac,
# built 27 Sep) ran v16.35.0 / v16.36.0 / v16.10.0 from the same branch names.
#
# 2026-09-28, after the release: production now runs prod-a9fc88f, and its three
# versions are v16.35.0 / v16.36.0 / v16.10.0 - EXACTLY the three pinned below.
# So this pin changes nothing that is running. It records what is already there,
# which is the whole point: rebuild this commit in a month and you get the same
# software back. Checked on the server, not inferred.
#
# So: a tag, like CRM_TAG below. Frappe and ERPNext tag every release on
# version-16 and the branch tip sits on the newest tag, so a tag costs nothing in
# freshness and buys a build you can reproduce. Raised on purpose, never by
# itself - the procedure is in docs/slices/055-pin-framework-versions/
# 07-devops-inputs.md §4.
#
# Change these three together with .github/workflows/ci.yml, which builds its own
# bench for the Python tests. scripts/check_version_pins.py checks they agree.
ARG FRAPPE_TAG=v16.35.0
ARG ERPNEXT_TAG=v16.36.0
# Indian statutory compliance: GST returns, e-invoicing, e-way bills, TDS on
# vendor payments, and the Companies Act audit trail. Sold as a module - see
# subscription.py - so it is present in the image but installed on a site only
# when the plan includes it.
#
# Its own release line, not Frappe's: v16.x here is india-compliance's numbering.
ARG INDIA_COMPLIANCE_TAG=v16.10.0
# Frappe CRM (frappe/crm): leads, deals, email, telephony - the standalone CRM,
# sold as the `crm` feature in subscription.py. Present in the image, installed on
# a site only when sold, and only AFTER that site's setup wizard has finished
# (its setup_wizard_complete hook seeds fake users and leads otherwise).
#
# Pinned to a release TAG, not a branch. Its Vue frontend links @framework/ui to
# apps/frappe/ui, so a moving branch could break every future image build with
# no change on our side. Bump the tag on purpose, in one place (slice 040).
ARG CRM_TAG=v1.84.0
# Frappe WhatsApp (shridarpatil/frappe_whatsapp): Meta's WhatsApp Cloud API,
# sold as the `whatsapp` feature in subscription.py. Present in the image,
# installed on a site only when sold. No setup-wizard hook, so provisioning
# installs it directly.
#
# Pinned to a COMMIT on master: the newest tag (v1.0.11, Nov 2025) predates
# multi-account support, which only master has. Bump on purpose, in one place
# (slice 042).
ARG WHATSAPP_COMMIT=08bc1f6af2e3

# Frappe Payments (frappe/payments): infrastructure only. It exists here because
# LMS declares `required_apps = ["frappe/payments"]` in its own hooks.py - a
# tenant never buys Payments on its own and no course or batch is ever given a
# price, so LMS Settings' "Payments installed, no gateway configured" state is
# never exercised (checked, not just read: docs/slices/166-167-helpdesk-lms/
# 01d-devops-first-look.md §2). Installed unconditionally inside the `has_feature
# lms` branch in provision_tenant.sh, same as india_compliance's own ERPNext
# prerequisites, not sold as its own feature.
#
# Pinned to a COMMIT on `version-16`, the WhatsApp treatment: get-app cannot
# take a bare commit, so fetch the branch, then checkout it.
ARG PAYMENTS_COMMIT=cca07d9f9392e2ea0e521c5975151db9e4b6c321
# Frappe LMS (frappe/lms): courses, lessons, quizzes, certificates - sold as the
# `lms` feature in subscription.py (ALV-167), off by default, internal training
# only. Present in the image, installed on a site only when sold.
#
# Pinned to a COMMIT on `version-16`, not `develop`/the numbered `v2.6x` tags -
# those track `frappe = ">=17.0.0-dev,<18.0.0"`, a Frappe version we do not run.
# `version-16` itself declares no Frappe bound at all, so re-verify it still
# matches our Frappe pin before ever bumping this. Bump on purpose, in one
# place (slice 166/167).
ARG LMS_COMMIT=87168fc7b2f24559e474ea4702cf1aa63b0db4e8
# Telephony (frappe/telephony): required by Helpdesk for its call log doctype.
# No required_apps of its own.
#
# No release has ever been cut - one branch, `develop`, no tag - the thinnest
# supply chain in this image. Pinned to a COMMIT on `develop`, the WhatsApp
# treatment. Re-check this before every future bump, not just this one.
ARG TELEPHONY_COMMIT=039cf39f245d6818ead03cf94eea6ce7f9c1e1f7
# Frappe Helpdesk (frappe/helpdesk): tickets, SLAs, a customer portal, email-to-
# ticket - sold as the `helpdesk` feature in subscription.py (ALV-166), off by
# default. A resold customer-support desk, not an internal HR tool - Surbhi's
# decision, 28 Sep 2026.
#
# Pinned to the release TAG v1.30.1, like CRM: it exists, it is legible in a
# diff, and a tag is preferred over a branch+commit whenever one exists.
ARG HELPDESK_TAG=v1.30.1

USER frappe
WORKDIR /home/frappe

ENV PATH="/home/frappe/.local/bin:${PATH}"

# ── yarn's download cache stays OUT of the image ──────────────────────────────
# Five of the steps below run `yarn install` (bench init, three get-apps and
# setup requirements --node). Each one left its downloads in
# /home/frappe/.cache/yarn, inside its own layer: 2.6 GB across the four layers of
# the pre-CRM image, more with the CRM. A `yarn cache clean` at the end would not
# help - a file deleted in a later layer still costs its bytes in the earlier one.
# A BuildKit cache mount is the right tool: the directory exists only while the
# step runs, is reused between builds on the same machine, and is never written to
# a layer. uid/gid 1000 is the `frappe` user, or yarn cannot write to it.
# (ALV-109. On 23 Sep 2026 the CRM build filled the GitHub runner's disk.)
# ── 1. Bench + upstream apps, pinned by release tag (ALV-156) ───────────────
RUN --mount=type=cache,target=/home/frappe/.cache/yarn,uid=1000,gid=1000 bench init --skip-redis-config-generation \
               --frappe-branch "${FRAPPE_TAG}" \
               frappe-bench

WORKDIR /home/frappe/frappe-bench

RUN --mount=type=cache,target=/home/frappe/.cache/yarn,uid=1000,gid=1000 bench get-app --branch "${ERPNEXT_TAG}" erpnext

# Declares required_apps = ["frappe/erpnext"], so it must follow erpnext.
RUN --mount=type=cache,target=/home/frappe/.cache/yarn,uid=1000,gid=1000 bench get-app --branch "${INDIA_COMPLIANCE_TAG}" https://github.com/resilient-tech/india-compliance

# No required_apps of its own. get-app runs its pip install (adds twilio) and the
# frontend's yarn install; the Vite build itself happens in step 4 below.
RUN --mount=type=cache,target=/home/frappe/.cache/yarn,uid=1000,gid=1000 bench get-app --branch "${CRM_TAG}" https://github.com/frappe/crm

# get-app cannot take a commit, so: fetch master, then pin. The editable pip
# install get-app already did stays valid - the checkout changes files in place.
RUN --mount=type=cache,target=/home/frappe/.cache/yarn,uid=1000,gid=1000 bench get-app --branch master https://github.com/shridarpatil/frappe_whatsapp \
 && git -C apps/frappe_whatsapp checkout --quiet "${WHATSAPP_COMMIT}" \
 && git -C apps/frappe_whatsapp log -1 --format='frappe_whatsapp pinned at %h (%cs)'

# Declares required_apps = ["frappe/payments"] in LMS's hooks.py, so this must
# come before it. No frontend of its own.
RUN --mount=type=cache,target=/home/frappe/.cache/yarn,uid=1000,gid=1000 bench get-app --branch version-16 https://github.com/frappe/payments \
 && git -C apps/payments checkout --quiet "${PAYMENTS_COMMIT}" \
 && git -C apps/payments log -1 --format='payments pinned at %h (%cs)'

# Both LMS and this app's own Helpdesk (below) declare a `frappe-ui` git
# submodule in their `.gitmodules`. It is deliberately left uninitialised - no
# `git submodule update` runs here. Neither app's Vite build reads it: each
# `frontend`/`desk` package.json lists `frappe-ui` as a normal npm dependency,
# and `yarn install` pulls a real, populated copy into its own node_modules.
# The empty submodule folder is silently irrelevant. Proven on a throwaway
# build, not assumed: docs/slices/166-167-helpdesk-lms/01e-test-build-results.md
# §3. A future engineer bumping either pin should not "fix" this - there is
# nothing to fix.
RUN --mount=type=cache,target=/home/frappe/.cache/yarn,uid=1000,gid=1000 bench get-app --branch version-16 https://github.com/frappe/lms \
 && git -C apps/lms checkout --quiet "${LMS_COMMIT}" \
 && git -C apps/lms log -1 --format='lms pinned at %h (%cs)'

# Declares required_apps = ["telephony"] in Helpdesk's hooks.py, so this must
# come before it. No frontend of its own.
RUN --mount=type=cache,target=/home/frappe/.cache/yarn,uid=1000,gid=1000 bench get-app --branch develop https://github.com/frappe/telephony \
 && git -C apps/telephony checkout --quiet "${TELEPHONY_COMMIT}" \
 && git -C apps/telephony log -1 --format='telephony pinned at %h (%cs)'

# See the frappe-ui note on the LMS get-app step above - it applies here too.
RUN --mount=type=cache,target=/home/frappe/.cache/yarn,uid=1000,gid=1000 bench get-app --branch "${HELPDESK_TAG}" https://github.com/frappe/helpdesk

# ── 2. First-party apps, copied from THIS commit ────────────────────────────
COPY --chown=frappe:frappe hrms                 apps/hrms
COPY --chown=frappe:frappe alvoraa_goals          apps/alvoraa_goals
COPY --chown=frappe:frappe alvoraa_portal  apps/alvoraa_portal

# ── 3. Real editable installs — not the .pth/symlink hack (closes G9) ───────
RUN ./env/bin/pip install --no-cache-dir \
        -e apps/hrms \
        -e apps/alvoraa_goals \
        -e apps/alvoraa_portal \
 && printf 'frappe\nerpnext\nindia_compliance\ncrm\nfrappe_whatsapp\npayments\nlms\ntelephony\nhelpdesk\nhrms\nalvoraa_goals\nalvoraa_portal\n' > sites/apps.txt

# ── 3b. Node dependencies for the copied apps ───────────────────────────────
# `bench get-app` runs yarn install for the app it fetches. COPY does not, so the
# first-party apps arrive without their node_modules and esbuild then fails with
#   Could not resolve "html2canvas"
# html2canvas is declared in hrms/package.json and imported by
# hrms/public/js/hierarchy_chart/hierarchy_chart_desktop.js - it was simply never
# installed. `bench setup requirements --node` covers every app in apps.txt, so this
# stays correct if a first-party app gains JS dependencies later.
RUN --mount=type=cache,target=/home/frappe/.cache/yarn,uid=1000,gid=1000 bench setup requirements --node

# ── 4. Bake assets: sites/assets + employee PWA + roster SPA ────────────────
# Built one app at a time, deliberately.
#
# `bench build --production` on its own bundles every app in a single process -
# frappe, erpnext, hrms (which includes two Vue applications, the employee PWA and
# the roster SPA) and both first-party apps. That is one large memory peak, and when
# the runner reclaims memory the process dies with SIGTERM, surfacing as exit 143 with
# no compile error to read.
#
# Sequencing lowers the peak to whichever single app is largest, and - just as useful -
# a failure now names the app that caused it. The previous form reported nothing at all.
#
# The per-app split was originally added chasing a suspected memory problem. It was not
# memory - the real cause was the missing node_modules handled in step 3b, and exit 143
# was the shell reporting a terminated esbuild rather than an OOM kill. The split is kept
# anyway: it names the failing app, which is what turned that guesswork into a one-line
# fix. NODE_OPTIONS is not raised, since there is no evidence it was ever needed.
RUN bench build --production --app frappe
RUN bench build --production --app erpnext
RUN bench build --production --app india_compliance
RUN bench build --production --app crm
RUN bench build --production --app frappe_whatsapp
RUN bench build --production --app payments
# LMS and Helpdesk both build a real Vue/Vite frontend, the biggest of which
# still downloads and links packages the way CRM and WhatsApp's own builds do -
# the yarn cache mount is needed here too, not just at get-app time.
RUN --mount=type=cache,target=/home/frappe/.cache/yarn,uid=1000,gid=1000 bench build --production --app lms
RUN bench build --production --app telephony
RUN --mount=type=cache,target=/home/frappe/.cache/yarn,uid=1000,gid=1000 bench build --production --app helpdesk
RUN bench build --production --app hrms
RUN bench build --production --app alvoraa_goals
RUN bench build --production --app alvoraa_portal

# ── 4b. Turn the asset symlinks into real files ─────────────────────────────
# `bench build` links sites/assets/<app> -> apps/<app>/<app>/public. The backend
# container has /apps so the links resolve there, but nginx mounts ONLY the sites
# volume and has no /apps - it follows a dangling link and 404s every CSS and JS file.
# The portal then renders with no styling and every panel stuck on "Loading...", which
# reads as an application fault and is not one.
#
# Dereferencing here means the image ships real files. Note this does NOT help when
# `bench build` is run inside a live container, because that writes into the sites
# volume and re-creates the symlinks - run scripts/materialise_assets.sh afterwards.
COPY --chown=frappe:frappe scripts/materialise_assets.sh /workspace/materialise_assets.sh
RUN bash /workspace/materialise_assets.sh

# ── 5. Tenant provisioning script, available to the provisioner role ────────
COPY --chown=frappe:frappe deploy/provision_tenant.sh /workspace/provision_tenant.sh

EXPOSE 8000 9000

# Default role = web. Overridden per service in docker-compose / k8s:
#   socketio  : node apps/frappe/socketio.js
#   scheduler : bench schedule                 (EXACTLY ONE replica — see §5)
#   worker    : bench worker --queue default,short
#   worker    : bench worker --queue long
CMD ["gunicorn", "--bind", "0.0.0.0:8000", \
     "--workers", "4", "--threads", "2", "--worker-class", "gthread", \
     "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", \
     "frappe.app:application"]
