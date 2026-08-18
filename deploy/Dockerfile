# ── Kinexus HRMS – immutable application image ──────────────────────────────
#
# Builds the complete Frappe bench with all five apps and pre-built assets.
# ONE image, run with five different commands (web / socketio / scheduler /
# worker / provisioner). See ARCHITECTURE.md §5 and §12.1.
#
# Build:
#   docker buildx build --platform linux/amd64,linux/arm64 \
#     -f deploy/Dockerfile -t ghcr.io/<org>/hr-app:sha-abc1234 .
#
# The build context is the REPO ROOT (not deploy/), because the three
# first-party apps are copied out of this repo — that is what closes gap G4,
# where production silently ran upstream frappe/hrms instead of this fork.
#
# NOTE: `hrms/frappe-ui` is a git submodule. Clone with --recurse-submodules
# or the PWA build fails.
#
# Optimisation left on the table: a two-stage build using frappe_docker's
# `frappe/base` as the runtime layer produces a much smaller image. It requires
# the builder and runtime images to agree on Python/glibc. Do that once the
# framework version is pinned (ARCHITECTURE.md §21 decision 6).

FROM frappe/bench:latest

ARG FRAPPE_BRANCH=version-16
ARG ERPNEXT_BRANCH=version-16

USER frappe
WORKDIR /home/frappe

ENV PATH="/home/frappe/.local/bin:${PATH}"

# ── 1. Bench + upstream apps, pinned by branch (pin by commit for prod) ─────
RUN bench init --skip-redis-config-generation \
               --frappe-branch "${FRAPPE_BRANCH}" \
               frappe-bench

WORKDIR /home/frappe/frappe-bench

RUN bench get-app --branch "${ERPNEXT_BRANCH}" erpnext

# ── 2. First-party apps, copied from THIS commit ────────────────────────────
COPY --chown=frappe:frappe hrms                 apps/hrms
COPY --chown=frappe:frappe alvoraa_goals          apps/alvoraa_goals
COPY --chown=frappe:frappe alvoraa_portal  apps/alvoraa_portal

# ── 3. Real editable installs — not the .pth/symlink hack (closes G9) ───────
RUN ./env/bin/pip install --no-cache-dir \
        -e apps/hrms \
        -e apps/alvoraa_goals \
        -e apps/alvoraa_portal \
 && printf 'frappe\nerpnext\nhrms\nalvoraa_goals\nalvoraa_portal\n' > sites/apps.txt

# ── 3b. Node dependencies for the copied apps ───────────────────────────────
# `bench get-app` runs yarn install for the app it fetches. COPY does not, so the
# first-party apps arrive without their node_modules and esbuild then fails with
#   Could not resolve "html2canvas"
# html2canvas is declared in hrms/package.json and imported by
# hrms/public/js/hierarchy_chart/hierarchy_chart_desktop.js - it was simply never
# installed. `bench setup requirements --node` covers every app in apps.txt, so this
# stays correct if a first-party app gains JS dependencies later.
RUN bench setup requirements --node

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
RUN bench build --production --app hrms
RUN bench build --production --app alvoraa_goals
RUN bench build --production --app alvoraa_portal

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
