#!/bin/bash
set -e

# Update package list
sudo apt update

# Install Podman
sudo apt install -y podman

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install NVM (Node Version Manager)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Install PHP
sudo apt install -y php php-cli

# Install Composer
curl -sS https://getcomposer.org/installer | php
sudo mv composer.phar /usr/local/bin/composer

echo "Installation complete. Please restart your shell or run 'source ~/.bashrc' to use nvm and uv."