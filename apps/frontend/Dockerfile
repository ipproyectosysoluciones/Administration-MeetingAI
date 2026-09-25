# ReunionAI frontend — builds the static Astro site, then serves it with nginx
# and proxies /api/* to the backend service (see infra/nginx/nginx.conf).
FROM node:22-alpine AS build

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /srv/frontend

COPY package.json ./
# pnpm v10 CI refuses dependency build scripts unless explicitly allowed.
RUN pnpm config set dangerously-allow-all-builds true
RUN pnpm install

COPY . .
RUN pnpm build

FROM nginx:1.27-alpine
COPY --from=build /srv/frontend/dist /usr/share/nginx/html
COPY default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
# OCI labels: link the GHCR package back to this repo (permissions inherit,
# Actions workflows get automatic package access).
LABEL org.opencontainers.image.source="https://github.com/ipproyectosysoluciones/Administration-MeetingAI"
LABEL org.opencontainers.image.description="ReunionAI frontend portal"
LABEL org.opencontainers.image.licenses="MIT"
