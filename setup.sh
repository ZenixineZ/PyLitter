#!/bin/bash
sudo cp litter-robot.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/litter-robot.service
sudo systemctl enable litter-robot
sudo systemctl daemon-reload
sudo systemctl start litter-robot