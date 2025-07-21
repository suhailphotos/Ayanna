# scripts/backup.sh – dump before every sync
ts=$(date +%Y%m%d-%H%M)
pg_dump --file "backup/swara-$ts.sql.gz" \
        --dbname "$DATABASE_URL" \
        --format=custom \
        --no-owner --no-acl --compress=9
