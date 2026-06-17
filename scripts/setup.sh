#!/bin/bash
# ==============================================================================
# CodeBattle — Quick Setup Script
# Copies .env.example to .env for backend and frontend
# ==============================================================================

set -e

echo "🚀 Setting up CodeBattle development environment..."

# Backend .env
if [ ! -f "backend/.env" ]; then
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env from .env.example"
    echo "   ⚠️  IMPORTANT: Edit backend/.env and set a strong SECRET_KEY!"
else
    echo "⏭️  backend/.env already exists, skipping."
fi

# Frontend .env.local
if [ ! -f "frontend/.env.local" ]; then
    cp frontend/.env.example frontend/.env.local
    echo "✅ Created frontend/.env.local from .env.example"
else
    echo "⏭️  frontend/.env.local already exists, skipping."
fi

echo ""
echo "✅ Environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit backend/.env and set your SECRET_KEY"
echo "  2. Run: docker compose up --build"
echo "  3. Open: http://localhost:3000"
