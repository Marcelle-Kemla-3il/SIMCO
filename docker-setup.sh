#!/bin/bash

echo "🚀 SIMCO - Docker Setup"
echo "======================="
echo ""

# Build and start containers
echo "📦 Building Docker containers..."
docker-compose build

echo ""
echo "🔄 Starting services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for Ollama to be ready..."
sleep 10

echo ""
echo "📥 Pulling Mistral model..."
docker exec simco-ollama ollama pull mistral

echo ""
echo "✅ Setup complete!"
echo ""
echo "📍 Services running at:"
echo "   - Frontend: http://localhost:5173"
echo "   - Backend:  http://localhost:8000"
echo "   - Ollama:   http://localhost:11434"
echo ""
echo "📋 Useful commands:"
echo "   - View logs:    docker-compose logs -f"
echo "   - Stop:         docker-compose down"
echo "   - Restart:      docker-compose restart"
echo "   - Shell:        docker exec -it simco-backend bash"
echo ""
