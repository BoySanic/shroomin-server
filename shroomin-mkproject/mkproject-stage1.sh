psql -h postgres -U ${SHROOM_DB_USER} -c "CREATE DATABASE ${SHROOM_DB_NAME};"
psql -h postgres -U ${SHROOM_DB_USER} -d ${SHROOM_DB_NAME} -f init.sql