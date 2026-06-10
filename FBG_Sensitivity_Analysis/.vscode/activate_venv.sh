#!/bin/bash
# Activar automáticamente el venv de FBG

VENV_PATH="/afs/cern.ch/user/v/vgarciap/rtd-calibration-ana/FBG_Sensitivity_Analysis/.venv-fbg"

if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
    echo "✅ FBG venv activado automáticamente"
else
    echo "❌ No se encuentra el venv en $VENV_PATH"
fi
