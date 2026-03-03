# PowerShell script for Windows

Write-Host "🚀 SIMCO - Docker Setup" -ForegroundColor Cyan
Write-Host "=======================" -ForegroundColor Cyan
Write-Host ""

# Build and start containers
Write-Host "📦 Building Docker containers..." -ForegroundColor Yellow
docker-compose build

Write-Host ""
Write-Host "🔄 Starting services..." -ForegroundColor Yellow
docker-compose up -d

Write-Host ""
Write-Host "⏳ Waiting for Ollama to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "📥 Pulling Mistral model..." -ForegroundColor Yellow
docker exec simco-ollama ollama pull mistral

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📍 Services running at:" -ForegroundColor Cyan
Write-Host "   - Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "   - Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "   - Ollama:   http://localhost:11434" -ForegroundColor White
Write-Host ""
Write-Host "📋 Useful commands:" -ForegroundColor Cyan
Write-Host "   - View logs:    docker-compose logs -f" -ForegroundColor White
Write-Host "   - Stop:         docker-compose down" -ForegroundColor White
Write-Host "   - Restart:      docker-compose restart" -ForegroundColor White
Write-Host "   - Shell:        docker exec -it simco-backend bash" -ForegroundColor White
Write-Host ""
