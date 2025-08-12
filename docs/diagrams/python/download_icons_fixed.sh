#!/bin/bash
# Download working icons for the project (December 2024 tested URLs)

echo "📥 Downloading working icons for your tech stack..."

# Create icons directory
mkdir -p icons

# Simple Icons - Working URLs with colors
echo "Downloading from Simple Icons CDN..."
wget -q -O icons/fastapi.svg "https://cdn.simpleicons.org/fastapi/009688"
wget -q -O icons/python.svg "https://cdn.simpleicons.org/python/3776AB"
wget -q -O icons/redis.svg "https://cdn.simpleicons.org/redis/DC382D"
wget -q -O icons/sqlite.svg "https://cdn.simpleicons.org/sqlite/003B57"
wget -q -O icons/aws.svg "https://cdn.simpleicons.org/amazonaws/FF9900"
wget -q -O icons/dynamodb.svg "https://cdn.simpleicons.org/amazondynamodb/4053D6"
wget -q -O icons/pytest.svg "https://cdn.simpleicons.org/pytest/0A9EDC"
wget -q -O icons/jwt.svg "https://cdn.simpleicons.org/jsonwebtokens/000000"
wget -q -O icons/docker.svg "https://cdn.simpleicons.org/docker/2496ED"

# GitHub raw content
echo "Downloading from GitHub..."
wget -q -O icons/pydantic.png "https://raw.githubusercontent.com/pydantic/pydantic/main/docs/logo-white.png"

# Iconify API for additional icons
echo "Downloading from Iconify API..."
wget -q -O icons/gemini.svg "https://api.iconify.design/logos:google-gemini.svg"
wget -q -O icons/openai.svg "https://api.iconify.design/logos:openai-icon.svg"
wget -q -O icons/lambda.svg "https://api.iconify.design/logos:aws-lambda.svg"
wget -q -O icons/litellm.svg "https://api.iconify.design/logos:openai-icon.svg"
wget -q -O icons/openrouter.svg "https://api.iconify.design/simple-icons:openai.svg?color=%2310B981"

# Material Design Icons for generic concepts
echo "Downloading Material Design icons..."
wget -q -O icons/rate-limit.svg "https://api.iconify.design/mdi:speedometer.svg?color=%23ff9900"
wget -q -O icons/slowapi.svg "https://api.iconify.design/mdi:speedometer-slow.svg?color=%23ff9900"
wget -q -O icons/retry.svg "https://api.iconify.design/mdi:reload.svg?color=%23009688"
wget -q -O icons/tenacity.svg "https://api.iconify.design/mdi:sync.svg?color=%23f59e0b"
wget -q -O icons/cache.svg "https://api.iconify.design/mdi:memory.svg?color=%234053d6"
wget -q -O icons/protocol.svg "https://api.iconify.design/mdi:api.svg?color=%233776ab"
wget -q -O icons/dict.svg "https://api.iconify.design/mdi:code-json.svg?color=%23009688"
wget -q -O icons/logging.svg "https://api.iconify.design/mdi:text-box-outline.svg?color=%2300acc1"
wget -q -O icons/loguru.svg "https://api.iconify.design/mdi:file-document-outline.svg?color=%2300acc1"

# Additional helper icons
echo "Downloading additional icons..."
wget -q -O icons/jose.svg "https://api.iconify.design/mdi:lock.svg?color=%232e7d32"
wget -q -O icons/mangum.svg "https://api.iconify.design/mdi:lambda.svg?color=%23ff6b6b"
wget -q -O icons/middleware.svg "https://api.iconify.design/mdi:middleware.svg?color=%236366f1"
wget -q -O icons/handler.svg "https://api.iconify.design/mdi:alert-box.svg?color=%23ef4444"
wget -q -O icons/aiosqlite.svg "https://api.iconify.design/simple-icons:sqlite.svg?color=%23003B57"

echo "✅ Icon download complete!"
echo ""
echo "Downloaded icons:"
ls -1 icons/*.svg icons/*.png 2>/dev/null | wc -l
echo "files in ./icons/"

# Verify critical icons
echo ""
echo "Verifying critical icons..."
for icon in fastapi python jwt redis sqlite aws dynamodb; do
    if [ -f "icons/${icon}.svg" ]; then
        size=$(stat -f%z "icons/${icon}.svg" 2>/dev/null || stat -c%s "icons/${icon}.svg" 2>/dev/null)
        if [ "$size" -gt 100 ]; then
            echo "✓ ${icon}.svg (${size} bytes)"
        else
            echo "✗ ${icon}.svg is too small (${size} bytes)"
        fi
    else
        echo "✗ ${icon}.svg missing"
    fi
done
