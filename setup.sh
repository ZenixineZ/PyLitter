#!/bin/bash
set -e

# ─────────────────────────────────────────────
# Litter Robot 4 – RPi Setup Script
# ─────────────────────────────────────────────

PYTHON_VERSION="3.11.4"
APP_DIR="/opt/litter-robot"
SERVICE_NAME="litter-robot"

usage() {
    cat <<EOF
Usage: sudo bash setup.sh [options]

Options:
  -u <user>       System user to run the service as (default: current user)
  -d <directory>  Install directory (default: /opt/litter-robot)
  -m <uuid>       UUID of external drive to mount at /mnt/video_storage
  -h              Show this help message

Examples:
  sudo bash setup.sh
  sudo bash setup.sh -u pi
  sudo bash setup.sh -u john -d /opt/litter-robot
  sudo bash setup.sh -u pi -m 1234-ABCD
EOF
    exit 0
}

# ── Parse arguments ──────────────────────────
SERVICE_USER="${SUDO_USER:-$USER}"
DRIVE_UUID=""

while getopts ":u:d:m:h" opt; do
    case $opt in
        u) SERVICE_USER="$OPTARG" ;;
        d) APP_DIR="$OPTARG" ;;
        m) DRIVE_UUID="$OPTARG" ;;
        h) usage ;;
        :) echo "ERROR: Option -$OPTARG requires an argument."; echo; usage ;;
        \?) echo "ERROR: Unknown option -$OPTARG"; echo; usage ;;
    esac
done

# ── Validate ─────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    echo "ERROR: This script must be run as root."
    echo "       Try: sudo bash setup.sh -u <user>"
    exit 1
fi

if ! id "$SERVICE_USER" &>/dev/null; then
    echo "ERROR: User '$SERVICE_USER' does not exist on this system."
    exit 1
fi

if [[ ! -f account_info.json ]]; then
    echo "ERROR: account_info.json not found in current directory."
    echo "       Copy account_info_sample.json to account_info.json and fill in your credentials."
    exit 1
fi

# ── Install ───────────────────────────────────
echo "================================================"
echo " Litter Robot 4 Setup"
echo "   User:        $SERVICE_USER"
echo "   Install dir: $APP_DIR"
echo "   Python:      $PYTHON_VERSION (via pyenv)"
echo "================================================"

echo ""
echo ">>> Updating packages..."
apt-get update -qq

echo ""
echo ">>> Installing build dependencies for pyenv..."
apt-get install -y -qq \
    build-essential libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev libffi-dev libncursesw5-dev \
    libgdbm-dev liblzma-dev tk-dev uuid-dev curl git

USER_HOME=$(eval echo "~$SERVICE_USER")
PYENV_ROOT="$USER_HOME/.pyenv"
PYTHON_BIN="$PYENV_ROOT/versions/$PYTHON_VERSION/bin/python"

echo ""
echo ">>> Installing pyenv for $SERVICE_USER..."
if [[ ! -d "$PYENV_ROOT" ]]; then
    sudo -u "$SERVICE_USER" bash -c 'curl -fsSL https://pyenv.run | bash'
else
    echo "    pyenv already installed, skipping."
fi

# Add pyenv to the user's shell profile if not already present
PROFILE="$USER_HOME/.bashrc"
if ! grep -q 'pyenv init' "$PROFILE"; then
    sudo -u "$SERVICE_USER" bash -c "cat >> $PROFILE" <<'PYENV_INIT'

# pyenv
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"
PYENV_INIT
fi

echo ""
echo ">>> Installing Python $PYTHON_VERSION via pyenv (this may take a few minutes)..."
sudo -u "$SERVICE_USER" bash -c "
    export PYENV_ROOT=$PYENV_ROOT
    export PATH=$PYENV_ROOT/bin:\$PATH
    eval \"\$(pyenv init - bash)\"
    pyenv install --skip-existing $PYTHON_VERSION
    pyenv global $PYTHON_VERSION
"

echo ""
echo ">>> Installing pylitterbot..."
sudo -u "$SERVICE_USER" bash -c "
    export PYENV_ROOT=$PYENV_ROOT
    export PATH=$PYENV_ROOT/bin:\$PATH
    eval \"\$(pyenv init - bash)\"
    pip install --quiet --upgrade pip
    pip install --quiet pylitterbot
"

echo ""
echo ">>> Creating app directory at $APP_DIR..."
mkdir -p "$APP_DIR"
cp account_info.json "$APP_DIR/"
cp litter-robot.py "$APP_DIR/"
chmod 600 "$APP_DIR/account_info.json"
chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"

echo ""
echo ">>> Writing systemd service..."
cat > /etc/systemd/system/"$SERVICE_NAME".service <<EOF
[Unit]
Description=Litter Robot 4 Auto-Clean Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$APP_DIR
Environment="PYENV_ROOT=$PYENV_ROOT"
Environment="PATH=$PYENV_ROOT/bin:$PYENV_ROOT/shims:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$PYTHON_BIN -u $APP_DIR/litter-robot.py

# Restart behaviour
Restart=on-failure
RestartSec=30
StartLimitIntervalSec=300
StartLimitBurst=5

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
chmod 644 /etc/systemd/system/"$SERVICE_NAME".service

echo ""
echo ">>> Enabling and starting service..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo ""
echo ">>> Checking service status..."
sleep 2
systemctl status "$SERVICE_NAME" --no-pager || true

# ── Optional: mount external drive ───────────
if [[ -n "$DRIVE_UUID" ]]; then
    echo ""
    echo ">>> Mounting drive with UUID: $DRIVE_UUID"
    if [ -e "/dev/disk/by-uuid/$DRIVE_UUID" ]; then
        apt-get install -y -qq exfatprogs
        mkdir -p /mnt/video_storage
        if ! grep -q "$DRIVE_UUID" /etc/fstab; then
            echo "UUID=$DRIVE_UUID  /mnt/video_storage  exfat  defaults,nofail,uid=$(id -u "$SERVICE_USER"),gid=$(id -g "$SERVICE_USER"),umask=022  0  0" \
                | tee -a /etc/fstab
        fi
        mount -a
        echo "    Mounted at /mnt/video_storage"
    else
        echo "    WARNING: No drive found with UUID '$DRIVE_UUID' – skipping mount."
    fi
fi

# ── Done ──────────────────────────────────────
echo ""
echo "================================================"
echo " Setup complete!"
echo ""
echo " Useful commands:"
echo "   View logs:     journalctl -u $SERVICE_NAME -f"
echo "   Status:        sudo systemctl status $SERVICE_NAME"
echo "   Restart:       sudo systemctl restart $SERVICE_NAME"
echo "   Stop:          sudo systemctl stop $SERVICE_NAME"
echo "   Files at:      $APP_DIR"
echo "================================================"