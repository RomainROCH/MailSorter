FROM python:3.10-slim

# Install system deps if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app dir
WORKDIR /app

# Copy only dependency metadata first for caching
COPY pyproject.toml poetry.lock* ./

# Install poetry and deps
RUN pip install --no-cache-dir poetry && poetry config virtualenvs.create false && poetry install --no-dev --no-interaction --no-ansi

# Copy project
COPY . /app

# Default command
CMD ["poetry", "run", "python", "-m", "backend.main"]
