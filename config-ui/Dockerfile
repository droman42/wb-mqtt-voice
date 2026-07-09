# BUILD-9 (design D-4): config-ui as a bridge-style static nginx image.
# ONE multi-arch manifest (amd64+arm64+armv7) — the dist is arch-independent, only the
# nginx base differs per platform. Published as ghcr.io/droman42/wb-mqtt-voice-ui; NOT
# deployed to the controller (the repo owns the config there — run this on a workstation).
#
# No proxy stage: Irene's API has no /api prefix and serves permissive CORS, so the
# browser talks to the backend directly. The API base is runtime-injected via
# /runtime-config.js (API_BASE_URL env; empty = same-hostname:8080 fallback in code).

FROM node:22-slim AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.d/40-runtime-config.sh

# Non-root, like the backend images (BUILD-25). Nothing here needs uid 0: nginx listens on
# 3000 (>1024, no privileged bind) and the entrypoint writes only inside the html root. The
# base image's own `nginx` user (uid 101) owns everything the worker + entrypoint touch —
# the pid file must be pre-created, since /var/run itself stays root-owned. The `user`
# directive is dropped: it is meaningless without uid 0 and nginx warns about it on every start.
RUN chmod +x /docker-entrypoint.d/40-runtime-config.sh \
    && sed -i '/^user /d' /etc/nginx/nginx.conf \
    && touch /var/run/nginx.pid \
    && chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/run/nginx.pid
USER nginx

EXPOSE 3000
# 127.0.0.1, NOT localhost: `listen 3000` binds IPv4 only, musl resolves localhost to ::1
# first, and busybox wget does not fall back — the probe could never succeed (BUILD-25).
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:3000/ || exit 1
