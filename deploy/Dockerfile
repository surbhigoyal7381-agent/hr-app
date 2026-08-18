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

# ── 4. Bake assets: sites/assets + employee PWA + roster SPA ────────────────
RUN bench build --production

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
