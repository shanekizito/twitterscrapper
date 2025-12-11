#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Install Chrome
CHROME_DIR=/opt/render/project/.render/chrome
if [[ ! -d "$CHROME_DIR" ]]; then
  echo "...Downloading Chrome"
  mkdir -p "$CHROME_DIR"
  cd "$CHROME_DIR"
  wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x google-chrome-stable_current_amd64.deb .
  rm google-chrome-stable_current_amd64.deb
  cd -
else
  echo "...Using Chrome from cache"
fi

# Export Chrome path for the runtime
echo "export CHROME_BIN=$CHROME_DIR/opt/google/chrome/google-chrome" >> ~/.bashrc
