#!/bin/bash
# Setup script for backend .env file

echo "🔧 Setting up backend environment configuration..."
echo ""

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborting setup."
        exit 0
    fi
fi

# Generate secrets
echo "🔐 Generating secure secrets..."
JWT_SECRET=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "")

if [ -z "$ENCRYPTION_KEY" ]; then
    echo "⚠️  Warning: cryptography module not found, using fallback encryption key"
    ENCRYPTION_KEY="TEMP_KEY_PLEASE_REPLACE_IN_PRODUCTION"
fi

# Check for existing credentials
OPENAI_KEY="${OPENAI_API_KEY:-sk-your-openai-key}"
NGROK_TOKEN="${NGROK_AUTH_TOKEN:-}"

# Create .env file
cat > .env << EOF
# Database (using docker-compose defaults)
DATABASE_URL=postgresql://content_user:content_password@postgres:5432/content_creation

# Redis (using docker-compose service name)
REDIS_URL=redis://redis:6379/0

# JWT Secret (auto-generated)
SECRET_KEY=$JWT_SECRET
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenAI
OPENAI_API_KEY=$OPENAI_KEY

# OAuth Credentials (for backend proxy)
INSTAGRAM_CLIENT_ID=${INSTAGRAM_CLIENT_ID:-}
INSTAGRAM_CLIENT_SECRET=${INSTAGRAM_CLIENT_SECRET:-}
YOUTUBE_CLIENT_SECRETS_FILE=../creds/client_secret_2_80997379597-sb3t0q56k8lqti0rf1ao77edcdsq0ess.apps.googleusercontent.com.json
TIKTOK_CLIENT_KEY=${TIKTOK_CLIENT_KEY:-}
TIKTOK_CLIENT_SECRET=${TIKTOK_CLIENT_SECRET:-}

# Stripe
STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY:-sk_test_}
STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET:-whsec_}

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:5174

# ngrok (for OAuth callbacks in development)
NGROK_AUTH_TOKEN=$NGROK_TOKEN
NGROK_DOMAIN=${NGROK_DOMAIN:-}

# Backend URL
BACKEND_URL=http://localhost:8000

# Encryption key for OAuth tokens (auto-generated)
ENCRYPTION_KEY=$ENCRYPTION_KEY
EOF

echo "✅ .env file created successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Edit backend/.env and add your API keys:"
echo "   - OPENAI_API_KEY (required for AI features)"
echo "   - NGROK_AUTH_TOKEN (optional, for OAuth in development)"
echo "   - INSTAGRAM_CLIENT_ID/SECRET (optional, for Instagram)"
echo "   - TIKTOK_CLIENT_KEY/SECRET (optional, for TikTok)"
echo "   - STRIPE_SECRET_KEY (optional, for billing)"
echo ""
echo "2. Start the backend:"
echo "   cd backend && docker-compose up -d"
echo ""
echo "3. View logs:"
echo "   docker-compose logs -f api"
echo ""



