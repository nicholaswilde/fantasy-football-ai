# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Define PUID and PGID for user/group creation
ARG PUID=1000
ARG PGID=1000
ENV PUID=${PUID}
ENV PGID=${PGID}

# Install system dependencies needed for go-task
# go-task is written in Go, which does not require a runtime, but we need
# to install it in the container for our workflow
RUN apt update && \
    apt install -y --no-install-recommends \
        curl && \
    curl -sL https://taskfile.dev/install.sh | sh && \
    mv ./bin/task /usr/local/bin/task && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create a user and group with specified PUID/PGID
RUN groupadd -g ${PGID} abc && \
    useradd -u ${PUID} -g abc -s /bin/bash abc && \
    usermod -aG users abc

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files into the container
COPY . .

# Set ownership of /app to the new user
RUN chown -R abc:abc /app

# Switch to the new user
USER abc

# Create the virtual environment directory
RUN python3 -m venv venv

# Set the entrypoint to the Taskfile, so you can run tasks directly
ENTRYPOINT ["task"]


