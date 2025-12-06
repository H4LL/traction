#!/bin/bash

# based on code developed by Sovrin:  https://github.com/hyperledger/aries-acapy-plugin-toolbox

if [[ "${TRACTION_ENV}" == "local" ]]; then
	echo "using ngrok end point [$NGROK_NAME]"

	NGROK_ENDPOINT=null
	while [ -z "$NGROK_ENDPOINT" ] || [ "$NGROK_ENDPOINT" = "null" ]
	do
	    echo "Fetching end point from ngrok service"
	    NGROK_ENDPOINT=$(curl --silent $NGROK_NAME:4040/api/tunnels | ./jq -r '.tunnels[] | select(.proto=="https") | .public_url')

	    if [ -z "$NGROK_ENDPOINT" ] || [ "$NGROK_ENDPOINT" = "null" ]; then
	        echo "ngrok not ready, sleeping 5 seconds...."
	        sleep 5
	    fi
	done

	export ACAPY_ENDPOINT=$NGROK_ENDPOINT
fi

echo "fetched end point [$ACAPY_ENDPOINT]"

echo "Provisioning wallet first for --no-ledger mode..."

# Step 1: Provision the wallet to create database schema
aca-py provision \
    --wallet-type askar-anoncreds \
    --wallet-storage-type postgres_storage \
    --wallet-name "${TRACTION_ACAPY_WALLET_NAME}" \
    --wallet-key "${TRACTION_ACAPY_WALLET_ENCRYPTION_KEY}" \
    --wallet-storage-config "{\"url\":\"${POSTGRESQL_HOST}:5432\",\"wallet_scheme\":\"DatabasePerWallet\",\"max_connections\":5}" \
    --wallet-storage-creds "{\"account\":\"${POSTGRESQL_USER}\",\"password\":\"${POSTGRESQL_PASSWORD}\",\"admin_account\":\"${POSTGRESQL_USER}\",\"admin_password\":\"${POSTGRESQL_PASSWORD}\"}" \
    --no-ledger

echo "Starting aca-py agent ..."

# ... if you want to echo the aca-py startup command ...
set -x

# Step 2: Start ACA-Py normally (wallet already provisioned)
exec aca-py start \
    --auto-provision \
    --wallet-local-did \
    --no-ledger \
    --wallet-type askar-anoncreds \
    --wallet-storage-type postgres_storage \
    --inbound-transport http "0.0.0.0" ${TRACTION_ACAPY_HTTP_PORT} \
    --outbound-transport http \
    --endpoint ${ACAPY_ENDPOINT} \
    --wallet-name "${TRACTION_ACAPY_WALLET_NAME}" \
    --wallet-key "${TRACTION_ACAPY_WALLET_ENCRYPTION_KEY}" \
    --wallet-storage-config "{\"url\":\"${POSTGRESQL_HOST}:5432\",\"wallet_scheme\":\"DatabasePerWallet\",\"max_connections\":5}" \
    --wallet-storage-creds "{\"account\":\"${POSTGRESQL_USER}\",\"password\":\"${POSTGRESQL_PASSWORD}\",\"admin_account\":\"${POSTGRESQL_USER}\",\"admin_password\":\"${POSTGRESQL_PASSWORD}\"}" \
    --admin "0.0.0.0" ${TRACTION_ACAPY_ADMIN_PORT} \
    --multitenant \
    --multitenant-admin \
    --jwt-secret "${ACAPY_MULTITENANT_JWT_SECRET}" \
    --multitenancy-config "{\"wallet_type\":\"single-wallet-askar\"}" \
    --plugin multitenant_provider.v1_0 \
    --plugin traction_plugins.traction_innkeeper.v1_0 \
    --plugin basicmessage_storage.v1_0 \
    --plugin connections \
    --plugin connection_update.v1_0 \
    --plugin rpc.v1_0 \
    --plugin webvh \
    --plugin cheqd
