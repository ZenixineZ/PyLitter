#!/bin/bash
if [[ ! -f account_info.json ]]; then
	echo "account_info.json must exist!"
	exit 1
fi
curl -fsSL https://pyenv.run | bash
if ! grep -iq pyenv ~/.bashrc; then 
	cat << EOF > ~/.bashrc
		export PYENV_ROOT="\$HOME/.pyenv"
		[[ -d \$PYENV_ROOT/bin ]] && export PATH="\$PYENV_ROOT/bin:\$PATH"
		eval "\$(pyenv init - bash)"
EOF
	export PYENV_ROOT="$HOME/.pyenv"
	[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
	eval "$(pyenv init - bash)"
fi
sudo apt update
sudo apt install -y \
  screen \
  exfatprogs \
  build-essential \
  libssl-dev \
  zlib1g-dev \
  libbz2-dev \
  libreadline-dev \
  libsqlite3-dev \
  libffi-dev \
  libncursesw5-dev \
  libgdbm-dev \
  liblzma-dev \
  tk-dev \
  uuid-dev
pyenv install 3.11.4
pyenv global 3.11.4
pip3 install opencv-python
sudo pip3 install pylitterbot
sudo mkdir /opt/litter-robot
sudo cp account_info.json /opt/litter-robot
sudo cp litter-robot.py /opt/litter-robot
sudo cp litter-robot.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/litter-robot.service
sudo systemctl enable litter-robot
sudo systemctl daemon-reload
sudo systemctl start litter-robot

if [[ -n $1 ]]; then
	if [ -e "/dev/disk/by-uuid/$1" ]; then
		sudo mkdir -p /mnt/video_storage
		echo "UUID=$1  /mnt/video_storage  exfat  defaults,nofail,uid=1000,gid=1000,umask=022  0  0" | sudo tee -a /etc/fstab
		sudo mount -a 
	fi
fi
