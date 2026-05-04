FROM python:3.11-alpine

# Install curl for healthcheck
RUN apk add --no-cache curl

# Create non-root group and user
RUN addgroup -S app && adduser -S app -G app

WORKDIR /app

# Install dependencies as root (pip needs write access)
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY app/ .

# Switch to non-root user
USER app

EXPOSE 3000

CMD ["python", "main.py"]