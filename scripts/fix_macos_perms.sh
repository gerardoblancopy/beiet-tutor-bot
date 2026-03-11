#!/bin/bash
# Emergency Permissions Fix for BEIET Bot on macOS

TARGET_DIR="/Users/gerardoblanco/beiet-tutor-bot"

echo "🚀 Iniciando limpieza de permisos en $TARGET_DIR..."

# 1. Quitar banderas de sistema (bloqueo de archivos)
echo "🔓 Desbloqueando archivos (chflags)..."
sudo chflags -R nouchg "$TARGET_DIR" 2>/dev/null

# 2. Resetear permisos base
echo "🔑 Ajustando permisos básicos (chmod)..."
chmod -R 755 "$TARGET_DIR"

# 3. Eliminar atributos extendidos (Quarantine, Provenance, etc)
echo "🧹 Eliminando atributos extendidos de macOS (xattr)..."
# Intentamos uno por uno para evitar errores fatales en el loop
find "$TARGET_DIR" -exec xattr -c {} \; 2>/dev/null

# 4. Caso especial: .env y base de datos
echo "📝 Forzando acceso a archivos críticos..."
[ -f "$TARGET_DIR/.env" ] && xattr -c "$TARGET_DIR/.env"
[ -f "$TARGET_DIR/beiet_final.db" ] && xattr -c "$TARGET_DIR/beiet_final.db"

echo "✅ Proceso completado. Por favor, intenta ejecutar el bot ahora."
