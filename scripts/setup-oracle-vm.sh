#!/bin/bash
# Grace Drinks HRMS – Oracle Arm A1 (Ubuntu 22.04) one-time setup
# ─────────────────────────────────────────────────────────────────
# Run ONCE after SSH-ing into the freshly provisioned Oracle VM:
#
#   ssh ubuntu@<oracle-public-ip>
#   curl -fsSL https://raw.githubusercontent.com/surbhigoyal7381-agent/hr-app/main/scripts/setup-oracle-vm.sh | bash
#
# OR copy the file and run it:
#   bash setup-oracle-vm.sh
# ─────────────────────────────────────────────────────────────────

set -e

REPO_URL="https://github.com/surbhigoyal7381-agent/hr-app.git"
APP_DIR="/opt/hr-app"

log() { echo ""; echo "━━━ $* ━━━"; }

# ── 1. System update ──────────────────────────────────────────────────────────
log "System update"
sudo apt-get update -y
sudo apt-get upgrade -y

# ── 2. Docker Engine ──────────────────────────────────────────────────────────
log "Installing Docker Engine"
sudo apt-get install -y ca-certificates curl gnupg lsb-release git

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
   https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Allow current user to run Docker without sudo
sudo usermod -aG docker "$USER"
echo "  → Docker installed. Version: $(docker --version)"

# ── 3. Oracle VM firewall  ─────────────────────────────────────────────────────
# Oracle Linux (and Ubuntu on Oracle) blocks ports at the iptables level even
# if the VCN Security List is open.  We add persistent rules here.
log "Opening ports 80 and 443 in iptables"
sudo apt-get install -y iptables-persistent || true
sudo iptables  -I INPUT  6 -p tcp --dport 80  -j ACCEPT
sudo iptables  -I INPUT  6 -p tcp --dport 443 -j ACCEPT
sudo ip6tables -I INPUT  6 -p tcp --dport 80  -j ACCEPT
sudo ip6tables -I INPUT  6 -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save || true
echo "  → Firewall rules saved."

# ── 4. Clone the repo ─────────────────────────────────────────────────────────
log "Cloning Grace Drinks repository"
sudo mkdir -p "$APP_DIR"
sudo chown "$USER":"$USER" "$APP_DIR"

if [ -d "$APP_DIR/.git" ]; then
    echo "  → Repo already cloned – pulling latest."
    git -C "$APP_DIR" pull origin main
else
    git clone "$REPO_URL" "$APP_DIR"
    # Also initialise the nested hrms sub-repo if it has its own .git
    if [ -d "$APP_DIR/hrms/.git" ]; then
        git -C "$APP_DIR/hrms" fetch --all
        git -C "$APP_DIR/hrms" checkout develop
    fi
fi

# ── 5. Backup directory ───────────────────────────────────────────────────────
mkdir -p "$APP_DIR/backups/latest"

# ── 6. .env file ──────────────────────────────────────────────────────────────
if [ ! -f "$APP_DIR/deploy/.env" ]; then
    cp "$APP_DIR/deploy/.env.example" "$APP_DIR/deploy/.env"
    echo ""
    echo "════════════════════════════════════════════════════════"
    echo "  ACTION REQUIRED: Set your credentials in .env"
    echo "  nano $APP_DIR/deploy/.env"
    echo "  (Change DB_ROOT_PASSWORD and ADMIN_PASSWORD)"
    echo "════════════════════════════════════════════════════════"
else
    echo "  → .env already exists – skipping."
fi

# ── 7. Instructions ───────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Setup complete.  Next steps:"
echo ""
echo "  1. Log out and back in (so docker group takes effect):"
echo "       exit"
echo "       ssh ubuntu@<your-oracle-ip>"
echo ""
echo "  2. Set your passwords:"
echo "       nano $APP_DIR/deploy/.env"
echo ""
echo "  3. Start the stack:"
echo "       cd $APP_DIR/deploy"
echo "       docker compose up -d"
echo ""
echo "  4. Watch the first-run setup (takes ~20-30 min):"
echo "       docker compose logs -f frappe"
echo ""
echo "  5. Once 'Serving on http://0.0.0.0:8000' appears, open:"
echo "       http://<your-oracle-public-ip>"
echo "       Login: Administrator / <your ADMIN_PASSWORD>"
echo ""
echo "  6. Remember to open ports 80 and 443 in the Oracle VCN"
echo "     Security List (Networking → Virtual Cloud Networks →"
echo "     your VCN → Security Lists → Default → Add Ingress Rules)"
echo "════════════════════════════════════════════════════════════"
