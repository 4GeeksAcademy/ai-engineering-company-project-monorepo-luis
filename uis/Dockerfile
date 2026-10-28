# Dockerfile for serving static UI (website & backoffice)
# Base image: Node (Alpine) – we use http-server to serve static files
FROM node:20-alpine AS builder

# Install http-server globally (lightweight static server)
RUN npm install -g http-server

# Create app directory
WORKDIR /app

# Copy the two UI folders into the image
COPY website/ ./website/
COPY backoffice/ ./backoffice/

# Ensure start script is present
COPY start.sh ./start.sh
RUN chmod +x ./start.sh

# Expose the two ports that will be used
EXPOSE 3000 3001

# Default command runs the start script
CMD ["./start.sh"]

