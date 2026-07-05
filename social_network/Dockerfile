# ==========================================
# STAGE 1: Build the Application
# ==========================================
FROM node:22-alpine AS builder
WORKDIR /app

# Copy configuration and package files
COPY package*.json tsconfig.json ./
COPY client/package*.json ./client/

# Install ALL dependencies (including devDependencies like typescript)
RUN npm install
RUN cd client && npm install

# Copy source directories needed for building
COPY prisma ./prisma/
COPY client ./client/
COPY src ./src/
COPY public ./public/

# Generate Prisma Client, build frontend, and build backend
RUN npx prisma generate
RUN cd client && npm run build
RUN npm run build

# Remove development dependencies to keep production light
RUN npm prune --production

# ==========================================
# STAGE 2: Production Run Environment
# ==========================================
FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Copy only what is strictly necessary to run the app from Stage 1
COPY package*.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/public ./public
COPY --from=builder /app/prisma ./prisma

# Open port 3000
EXPOSE 3000

# Start the compiled JavaScript application
CMD ["npm", "start"]

# Run migrations, conditionally seed, and start the app
# CMD npx prisma migrate deploy && \
#     if [ "$SEED_DB" = "true" ]; \
#     then npx prisma db seed; \
#     else echo "Skipping seed"; fi \
#     && npm start