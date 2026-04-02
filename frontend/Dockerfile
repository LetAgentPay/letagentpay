FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Install enterprise deps if overlay was applied (posthog-js for analytics)
RUN if grep -q posthog-js src/lib/posthog.ts 2>/dev/null; then npm install posthog-js; fi

ARG NEXT_PUBLIC_SELF_HOSTED=true
ARG NEXT_PUBLIC_SITE_URL=http://localhost:3000
ARG INTERNAL_API_URL=http://localhost:8000
ARG APP_VERSION=dev

ENV NEXT_PUBLIC_SELF_HOSTED=$NEXT_PUBLIC_SELF_HOSTED
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
ENV INTERNAL_API_URL=$INTERNAL_API_URL
ENV APP_VERSION=$APP_VERSION

RUN npm run build

FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0

# Install curl for health checks (busybox wget --spider unreliable)
RUN apk add --no-cache curl

# Create non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 appuser

COPY --from=builder --chown=appuser:appgroup /app/.next/standalone ./
COPY --from=builder --chown=appuser:appgroup /app/.next/static ./.next/static
COPY --from=builder --chown=appuser:appgroup /app/public ./public

USER appuser

EXPOSE 3000

CMD ["node", "server.js"]
