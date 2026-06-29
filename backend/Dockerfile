# backend/Dockerfile
FROM python:3.10-slim 

# 1. Install system compilation dependencies and portaudio
RUN apt-get update && apt-get install -y \
    gcc \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Proceed with your existing steps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the port FastAPI runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]