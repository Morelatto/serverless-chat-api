#!/bin/bash
# Download real icons for the project components

echo "📥 Downloading real icons for your tech stack..."

# Create icons directory (already exists but just in case)
mkdir -p icons

# Download official logos from Simple Icons (tech brands)
echo "Downloading from Simple Icons..."
curl -s -o icons/fastapi.svg https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/fastapi.svg
curl -s -o icons/python.svg https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/python.svg
curl -s -o icons/jwt.svg https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/jsonwebtokens.svg
curl -s -o icons/pytest.svg https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/pytest.svg
curl -s -o icons/redis.svg https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/redis.svg
curl -s -o icons/sqlite.svg https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/sqlite.svg
curl -s -o icons/aws.svg https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/amazonaws.svg
curl -s -o icons/dynamodb.svg https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/amazondynamodb.svg

# Download AI/LLM icons
echo "Downloading AI/LLM icons..."
curl -s -o icons/gemini.svg https://www.gstatic.com/lamda/images/gemini_logo_icon_136375.svg
curl -s -o icons/openai.svg https://upload.wikimedia.org/wikipedia/commons/0/04/ChatGPT_logo.svg

# Download Flaticon icons for libraries without official logos
echo "Downloading generic concept icons..."
curl -s -o icons/rate-limit.png https://cdn-icons-png.flaticon.com/512/3488/3488823.png
curl -s -o icons/protocol.png https://cdn-icons-png.flaticon.com/512/2920/2920277.png
curl -s -o icons/retry.png https://cdn-icons-png.flaticon.com/512/3106/3106868.png
curl -s -o icons/cache.png https://cdn-icons-png.flaticon.com/512/2864/2864598.png
curl -s -o icons/dict.png https://cdn-icons-png.flaticon.com/512/3721/3721619.png
curl -s -o icons/logging.png https://cdn-icons-png.flaticon.com/512/3721/3721641.png

# Additional official logos
echo "Downloading additional official logos..."
curl -s -o icons/pydantic.svg https://docs.pydantic.dev/latest/logo-white.svg || echo "Pydantic logo failed"

# Create aliases for specific uses
echo "Creating icon aliases..."
cp icons/rate-limit.png icons/slowapi.png 2>/dev/null || true
cp icons/retry.png icons/tenacity.png 2>/dev/null || true
cp icons/logging.png icons/loguru.png 2>/dev/null || true
cp icons/openai.svg icons/litellm.svg 2>/dev/null || true
cp icons/openai.svg icons/openrouter.svg 2>/dev/null || true

echo "✅ Icon download complete!"
echo ""
echo "Downloaded icons:"
ls -la icons/*.svg icons/*.png 2>/dev/null | tail -20
