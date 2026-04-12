FROM node:20-alpine

# psql is used by seed-entrypoint.sh to detect whether the DB is already seeded
RUN apk add --no-cache postgresql-client openssl

WORKDIR /app/data-explorer

# Install dependencies before copying source to maximise layer cache
COPY data-explorer/package.json data-explorer/package-lock.json* ./
RUN npm ci

# Copy app source
COPY data-explorer/ .

# Generate Prisma client (no DB connection required at build time)
RUN npx prisma generate

# Copy the seed entrypoint used by the migrate service
COPY docker/seed-entrypoint.sh /app/docker/seed-entrypoint.sh
RUN chmod +x /app/docker/seed-entrypoint.sh

EXPOSE 3000
# -H 0.0.0.0 ensures Next.js binds to all interfaces inside the container
CMD ["npx", "next", "dev", "-H", "0.0.0.0", "--webpack"]
