# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies needed for go-task
# go-task is written in Go, which does not require a runtime, but we need
# to install it in the container for our workflow
RUN apt update && \
    apt install -y --no-install-recommends \
        curl && \
    curl -sL https://taskfile.dev/install.sh | sh && \
    mv go-task /usr/local/bin/task && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files into the container
COPY . .

# Create the virtual environment directory
RUN python3 -m venv venv

# Set the entrypoint to the Taskfile, so you can run tasks directly
ENTRYPOINT ["task"]

