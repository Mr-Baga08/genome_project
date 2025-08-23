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
# MODIFIED: Force reinstall motor to ensure compatible pymongo version is installed
RUN pip install --no-cache-dir -r requirements.txt && pip install --upgrade --force-reinstall motor

# --- NEW: Create a tarball of the virtual environment ---
RUN tar -czf /tmp/venv.tar.gz -C /opt venv


# --- Stage 2: Final Image ---
# This is the lean, final image for production
FROM python:3.9-slim

WORKDIR /app

# Install only necessary runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    docker-cli \
    && rm -rf /var/lib/apt/lists/*

# --- MODIFIED: Copy the single tarball instead of the whole directory ---
COPY --from=builder /tmp/venv.tar.gz /tmp/venv.tar.gz

# --- NEW: Unpack the virtual environment ---
RUN tar -xzf /tmp/venv.tar.gz -C /opt && rm /tmp/venv.tar.gz

# Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/uploads /tmp/ugene_workdir

# Expose port
EXPOSE 8000

# Production-ready start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
