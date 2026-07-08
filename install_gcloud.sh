#!/bin/bash
set -e

echo "=== Cleaning up previous invalid repository configurations ==="
rm -f /etc/apt/sources.list.d/google-cloud-
rm -f /etc/apt/sources.list.d/google-cloud-sdk
rm -f /etc/apt/sources.list.d/google-cloud-sdk.
rm -f /etc/apt/sources.list.d/google-cloud-sdk.list

echo "=== Installing dependencies ==="
apt-get update
apt-get install -y apt-transport-https ca-certificates gnupg curl

echo "=== Fetching Google Cloud GPG Key ==="
curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg --yes

echo "=== Adding Google Cloud CLI repository ==="
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" > /etc/apt/sources.list.d/google-cloud-sdk.list

echo "=== Updating repository sources ==="
apt-get update

echo "=== Installing google-cloud-cli ==="
apt-get install -y google-cloud-cli

echo "=== Verification ==="
which gcloud
gcloud --version

echo "=== SUCCESS! Please login with: gcloud auth login ==="
