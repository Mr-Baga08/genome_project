# --- Stage 1: Builder ---
# This stage builds the Python dependencies
FROM python:3.9-slim as builder

# Install build-time dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++

# Set up a virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# --- Stage 2: Final Image ---
# This is the lean, final image for production
FROM python:3.9-slim

WORKDIR /app

# Install only necessary runtime dependencies
# We install 'docker-cli' to interact with the Docker socket, NOT the full daemon
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    docker-cli \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Create necessary directories
# Note: These are also managed by volumes in docker-compose, which is good practice
RUN mkdir -p /app/uploads /tmp/ugene_workdir

# Expose port
EXPOSE 8000

# Production-ready start command (NO --reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
