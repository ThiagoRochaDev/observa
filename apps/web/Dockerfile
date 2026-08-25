FROM node:20-slim AS deps
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

FROM node:20-slim AS build
WORKDIR /web
COPY --from=deps /web/node_modules ./node_modules
COPY apps/web ./
# NEXT_PUBLIC_* é lido em build-time e embutido no bundle do cliente.
ARG NEXT_PUBLIC_API_URL=http://localhost:8080
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:20-slim AS runtime
WORKDIR /web
ENV NODE_ENV=production
COPY --from=build /web/public ./public
COPY --from=build /web/.next/standalone ./
COPY --from=build /web/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
