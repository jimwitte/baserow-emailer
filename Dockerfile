# Use the official Python slim image as the base
FROM python:3.12.2-slim-bullseye

# Set environment variables to avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Set the working directory inside the container
WORKDIR /app

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app's source code into the container
COPY app/ ./app/

# Ensure the shared config.yml file can be accessed from the Docker host
# The config.yml will be mounted as a volume, so we don't copy it in the container

# Set the entrypoint to run the Python script when the container starts
CMD ["python", "app/main.py"]
