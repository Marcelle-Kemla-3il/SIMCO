# This Dockerfile is for deploying the FastAPI backend on Render or similar platforms.
# It is a copy of backend/Dockerfile for compatibility with platforms expecting a root Dockerfile.

FROM node:22-alpine

WORKDIR /app

COPY quiz-frontend/package*.json ./
RUN npm install

COPY quiz-frontend .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
