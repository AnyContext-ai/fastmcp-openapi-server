# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.10-bookworm-slim

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

RUN uv build
RUN uv tool install .

# Place executables in the environment at the front of the path
ENV PATH="/root/.local/bin:/root/.local/share/uv/tools/fastmcp-openapi-server/bin:$PATH"

EXPOSE 8000

CMD ["sh", "-c", "fastmcp-openapi-server --transport sse \
    --openapi $OPENAPI \
    ${HEADERS:+--headers \"$HEADERS\"} \
    ${OAUTH2_CLIENT_ID:+--oauth2-client-id \"$OAUTH2_CLIENT_ID\"} \
    ${OAUTH2_CLIENT_SECRET:+--oauth2-client-secret \"$OAUTH2_CLIENT_SECRET\"} \
    ${OAUTH2_TOKEN_URL:+--oauth2-token-url \"$OAUTH2_TOKEN_URL\"} \
    ${OAUTH2_SCOPES:+--oauth2-scopes \"$OAUTH2_SCOPES\"}"]
