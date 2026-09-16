#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BITWIG_JAR="/opt/bitwig-studio/bin/bitwig.jar"
EXTENSIONS_DIR="$HOME/Bitwig Studio/Extensions"
TARGET_FILE="$EXTENSIONS_DIR/BitwigAgentBridge.bwextension"

if [ ! -f "$BITWIG_JAR" ]; then
    echo "[!] Error: Bitwig jar not found at $BITWIG_JAR"
    exit 1
fi

echo "==> Compiling Bitwig Agent Java Extension..."
rm -rf "$DIR/build"
mkdir -p "$DIR/build/classes"

javac --release 17 \
    -encoding UTF-8 \
    -cp "$BITWIG_JAR" \
    -d "$DIR/build/classes" \
    "$DIR"/src/main/java/com/bitwig/agent/*.java

echo "==> Copying resources..."
cp -r "$DIR/src/main/resources/"* "$DIR/build/classes/"

echo "==> Packaging BitwigAgentBridge.bwextension..."
jar cf "$DIR/build/BitwigAgentBridge.bwextension" -C "$DIR/build/classes" .

mkdir -p "$EXTENSIONS_DIR"
cp "$DIR/build/BitwigAgentBridge.bwextension" "$TARGET_FILE"

echo "[✓] Successfully built and deployed extension to:"
echo "    $TARGET_FILE"
