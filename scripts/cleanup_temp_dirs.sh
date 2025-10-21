#!/bin/bash
# Script para limpiar directorios temporales de pruebas RTD
# Uso: ./cleanup_temp_dirs.sh [--dry-run]

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 Modo DRY-RUN: solo mostrará qué se borraría"
    echo ""
fi

cd "$(dirname "$0")"

# Patrones de directorios temporales a eliminar
TEMP_PATTERNS=(
    "tmp_debug_*"
    "tmp_outliers_check*"
    "tmp_test_*"
    "tmp_*"
)

echo "📊 Directorios temporales encontrados:"
echo "======================================"
du -sh tmp_* 2>/dev/null | sort -h || echo "No se encontraron directorios tmp_*"
echo ""

# Calcular tamaño total
TOTAL_SIZE=$(du -sh tmp_* 2>/dev/null | awk '{sum+=$1} END {print sum}')
echo "💾 Espacio total: $(du -sh tmp_* 2>/dev/null | tail -1 | awk '{print $1}')"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "✅ Los siguientes directorios se borrarían:"
    ls -d tmp_* 2>/dev/null || echo "  (ninguno)"
    exit 0
fi

# Preguntar confirmación
read -p "⚠️  ¿Deseas eliminar TODOS los directorios tmp_*? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Operación cancelada"
    exit 1
fi

# Eliminar directorios
echo "🗑️  Eliminando..."
for dir in tmp_*; do
    if [ -d "$dir" ]; then
        echo "  - Borrando $dir"
        rm -rf "$dir"
    fi
done

echo ""
echo "✅ Limpieza completada"
