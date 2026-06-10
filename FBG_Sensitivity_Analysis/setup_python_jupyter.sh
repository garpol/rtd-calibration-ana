#!/bin/bash
# Script para configurar correctamente VS Code con Python y Jupyter

WORKSPACE_PATH="/afs/cern.ch/user/v/vgarciap/rtd-calibration-ana/FBG_Sensitivity_Analysis"
VENV_PATH="$WORKSPACE_PATH/.venv-fbg"
PYTHON_BIN="$VENV_PATH/bin/python"

echo "🔧 Configurando VS Code para FBG..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. Verificar que el venv existe
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Error: No se encuentra el venv en $VENV_PATH"
    exit 1
fi
echo "✅ Venv encontrado: $VENV_PATH"

# 2. Verificar que Python está disponible
if [ ! -f "$PYTHON_BIN" ]; then
    echo "❌ Error: No se encuentra Python en $PYTHON_BIN"
    exit 1
fi
echo "✅ Python disponible: $PYTHON_BIN"

# 3. Verificar que Jupyter está instalado en el venv
if ! "$PYTHON_BIN" -c "import jupyter; print(f'✅ Jupyter v{jupyter.__version__}')" 2>/dev/null; then
    echo "❌ Jupyter no está instalado en el venv"
    exit 1
fi

# 4. Verificar el kernel de Jupyter
KERNEL_DIR="$HOME/.local/share/jupyter/kernels/fbg-venv"
if [ -d "$KERNEL_DIR" ]; then
    echo "✅ Kernel 'fbg-venv' encontrado"
    echo "   Ubicación: $KERNEL_DIR"
    
    # Verificar que el kernel.json apunta al venv correcto
    if grep -q "$VENV_PATH" "$KERNEL_DIR/kernel.json"; then
        echo "✅ kernel.json apunta al venv correcto"
    fi
else
    echo "⚠️  Kernel 'fbg-venv' no encontrado, recreando..."
    mkdir -p "$KERNEL_DIR"
    cat > "$KERNEL_DIR/kernel.json" << EOF
{
 "argv": ["$PYTHON_BIN", "-m", "ipykernel_launcher", "-f", "{connection_file}"],
 "display_name": "Python (fbg-venv)",
 "language": "python"
}
EOF
    echo "✅ Kernel recreado en $KERNEL_DIR"
fi

# 5. Listar kernels disponibles
echo ""
echo "📋 Kernels disponibles en Jupyter:"
"$PYTHON_BIN" -m jupyter kernelspec list

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Configuración completada"
echo ""
echo "📝 PRÓXIMOS PASOS EN VS CODE:"
echo "1. Cierra VS Code completamente (Ctrl+K Ctrl+Q)"
echo "2. Reabre VS Code"
echo "3. En el notebook, haz click en 'Select Kernel'"
echo "4. Debería aparecer 'Python (fbg-venv)' - selecciónalo"
echo "5. Si no aparece, presiona Ctrl+Shift+P y busca 'Python: Select Interpreter'"
