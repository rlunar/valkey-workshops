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

# Install Java 17 (OpenJDK) — required for Spring Boot backend and Maven sample
sudo apt install -y openjdk-17-jdk

# Install Maven — required for the standalone jdbc-query-cache-sample project
sudo apt install -y maven

# Install Node.js via NVM (NVM is already installed above)
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm install --lts
nvm use --lts

echo "Installation complete. Please restart your shell or run 'source ~/.bashrc' to use nvm and uv."