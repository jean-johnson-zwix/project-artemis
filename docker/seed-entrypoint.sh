#!/bin/sh
set -e

cd /app/data-explorer

echo "==> Running Prisma migrations..."
npx prisma migrate deploy

echo "==> Checking if database is already seeded..."
COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM assets;" 2>/dev/null | tr -d ' \n' || echo "0")

if [ "$COUNT" -gt "0" ] 2>/dev/null; then
  echo "==> Database already seeded ($COUNT assets found). Skipping."
else
  echo "==> Seeding database (3M+ rows — this takes 1-3 minutes)..."
  npx prisma db seed
  echo "==> Seed complete."
fi
