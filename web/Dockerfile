# Frontend Dockerfile for AI Skill Eval Platform
FROM node:20-alpine

WORKDIR /app

# Copy dependency files
COPY package.json pnpm-lock.yaml ./

# Install pnpm and dependencies
RUN npm install -g pnpm && \
    pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Set environment variable for API URL
ENV NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Build Next.js application
RUN pnpm build

# Expose frontend port
EXPOSE 3000

# Start Next.js production server
CMD ["pnpm", "start"]
