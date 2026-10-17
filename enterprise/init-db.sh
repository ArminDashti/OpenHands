#!/bin/bash
# Initialize additional databases for OpenHands Enterprise

set -e

# Create keycloak database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE keycloak;
    CREATE DATABASE litellm;
    GRANT ALL PRIVILEGES ON DATABASE keycloak TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE litellm TO $POSTGRES_USER;
EOSQL

echo "Additional databases created: keycloak, litellm"
