ARG build_variant=full

FROM python:3.12-alpine3.21 AS base

WORKDIR /app

RUN apk add curl git
RUN apk add uv

RUN addgroup -S limgroup
RUN adduser -S limited -G limgroup
RUN chown limited:limgroup /app

COPY --chown=limited:limgroup . .

USER limited

FROM base AS sync_full
RUN uv sync --all-groups

FROM base AS sync_min
RUN uv sync

FROM sync_${build_variant} AS final
CMD uv run python -m maxtgfwd
