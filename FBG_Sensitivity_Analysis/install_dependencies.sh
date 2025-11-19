#!/bin/bash
# Install required packages for FBG sensitivity analysis

echo "Installing required Python packages..."
echo "======================================"

pip install --user uproot scipy numpy matplotlib 2>&1 | grep -v "Requirement already satisfied" || echo "All packages installed successfully!"

echo ""
echo "Testing imports..."
python3 -c "import uproot, scipy, numpy, matplotlib; print('✓ All packages imported successfully!')"

echo ""
echo "Ready to run analysis!"
echo "Example: python3 fbg_press_sensitivity_analysis.py --file data.root --auto-plateaus"
