#!/bin/bash

# thanks to https://github.com/lucasrla/shynet-docker-lightsail
# install latest version of docker the lazy way
curl -sSL https://get.docker.com | sh

# add the default ubuntu user to the docker group
# so that we don't need to sudo to run docker commands
usermod -aG docker ubuntu

# install docker-compose
curl -L https://github.com/docker/compose/releases/download/v2.37.1/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# copy the dockerfile into /srv/docker
mkdir /srv/docker
curl -o /srv/docker/docker-compose.yml https://raw.githubusercontent.com/zparmley/SiteStats/master/lightsail/docker-compose.yml

# copy in systemd unit file and register it compose file runs
# on system restart
curl -o /etc/systemd/system/docker-compose-app.service https://raw.githubusercontent.com/zparmley/SiteStats/master/lightsail/docker-compose-app.service
systemctl enable docker-compose-app
