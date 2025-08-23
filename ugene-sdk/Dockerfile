# ugene-sdk/Dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    tar \
    bash \
    python3 \
    python3-pip \
    build-essential \
    libqt5core5a \
    libqt5gui5 \
    libqt5widgets5 \
    libgl1-mesa-glx \
    xvfb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /opt

# Download and install UGENE SDK
RUN curl -L -o ugene-sdk.tar.gz \
    "https://github.com/ugeneunipro/ugene/releases/download/51.0/ugene-51.0-linux-x86-64.tar.gz" \
    && tar -xzf ugene-sdk.tar.gz \
    && rm ugene-sdk.tar.gz \
    && mv ugene-* ugene

# Make UGENE executable
RUN chmod +x /opt/ugene/ugene

# Set up environment
ENV PATH="/opt/ugene:${PATH}"
ENV DISPLAY=:99

# Create startup script
RUN echo '#!/bin/bash\n\
# Start virtual display for headless operation\n\
Xvfb :99 -screen 0 1024x768x24 &\n\
# Keep container running\n\
tail -f /dev/null' > /start.sh && chmod +x /start.sh

# Expose UGENE
CMD ["/start.sh"]

