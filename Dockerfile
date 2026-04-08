FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install the specific openenv version (or it is in requirements.txt)
RUN pip install "openenv-core>=0.2.0" uvicorn fastapi

COPY . .

# Expose the standard HF Spaces port
EXPOSE 7860

# We use the built server app explicitly
CMD ["python", "-m", "server.app"]
