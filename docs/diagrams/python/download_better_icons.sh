#!/bin/bash
# Download better, more specific icons for diagrams

cd /home/storm/Public/server-chat-api/docs/diagrams/python
mkdir -p icons

echo "🎨 Downloading better icons for diagrams..."

# 1. Pydantic Icon (for validation)
wget -q -O icons/pydantic.svg "https://api.iconify.design/simple-icons:pydantic.svg?color=%23e92063"

# 2. Response/Output Icons
wget -q -O icons/response.svg "https://api.iconify.design/heroicons:arrow-left-circle-solid.svg?color=%2322c55e"
wget -q -O icons/output.svg "https://api.iconify.design/heroicons:paper-airplane-solid.svg?color=%2322c55e"

# 3. Request/Input Icons
wget -q -O icons/request.svg "https://api.iconify.design/heroicons:arrow-right-circle-solid.svg?color=%236366f1"
wget -q -O icons/input.svg "https://api.iconify.design/heroicons:inbox-solid.svg?color=%236366f1"

# 4. Cache State Icons
wget -q -O icons/cache-hit.svg "https://api.iconify.design/heroicons:check-circle-solid.svg?color=%2322c55e"
wget -q -O icons/cache-miss.svg "https://api.iconify.design/heroicons:x-circle-solid.svg?color=%23f59e0b"

# 5. Data/State Icons
wget -q -O icons/data.svg "https://api.iconify.design/heroicons:document-text-solid.svg?color=%233b82f6"
wget -q -O icons/state.svg "https://api.iconify.design/heroicons:cube-solid.svg?color=%236366f1"

# 6. Performance Icons
wget -q -O icons/fast.svg "https://api.iconify.design/heroicons:bolt-solid.svg?color=%2322c55e"
wget -q -O icons/slow.svg "https://api.iconify.design/heroicons:clock-solid.svg?color=%23f59e0b"

# 7. Create custom number badges for status codes
for code in 401 422 429 503; do
    case $code in
        401) color="ef4444" ;; # Red for auth errors
        422) color="f59e0b" ;; # Orange for validation
        429) color="f59e0b" ;; # Orange for rate limit
        503) color="8b5cf6" ;; # Purple for server errors
    esac

    # Simple colored circle with number
    cat > icons/${code}.svg << EOF
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="45" fill="#${color}"/>
  <text x="50" y="50" text-anchor="middle" dy=".35em" font-family="Arial" font-size="28" font-weight="bold" fill="white">${code}</text>
</svg>
EOF
done

echo "✅ Downloaded ${#} icon files"

# Convert SVGs to PNGs for graphviz compatibility
echo "🔄 Converting SVGs to PNGs..."

for svg in icons/*.svg; do
    png="${svg%.svg}.png"
    if [[ ! -f "$png" ]] || [[ "$svg" -nt "$png" ]]; then
        convert -background none -density 600 "$svg" -resize 512x512 "$png" 2>/dev/null
        echo "  ✓ $(basename "$svg")"
    fi
done

echo "📊 Icons ready: $(ls icons/*.png 2>/dev/null | wc -l) PNG files"
