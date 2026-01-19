# Weinig Hydromat Tool Manager

Advanced tool management system for Weinig Hydromat 2000 woodworking machines.

## Windows 7 Compatibility

This application has been optimized for Windows 7 with the following requirements:

### System Requirements
- **OS**: Windows 7 SP1 (64-bit recommended)
- **Python**: 3.8.x (latest 3.8.x release recommended)
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Disk Space**: 200MB free space
- **Display**: 1024x768 minimum resolution

### Prerequisites
1. Install the latest Windows 7 updates
2. Install [Microsoft Visual C++ 2015-2022 Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
3. Install [.NET Framework 4.8](https://dotnet.microsoft.com/download/dotnet-framework/thank-you/net48-offline)

## Features

- **Profile Management**: Create, edit, and delete processing profiles
- **Tool Management**: Manage tools with automatic code generation
- **Head Assignment**: Assign tools to 10 milling heads with parameters
- **Image Support**: Add images to profiles and tools
- **Status Tracking**: Track tool status (Ready, Worn, In Service)
- **Export Functionality**: Export configurations to various formats
- **Search & Filter**: Powerful search and filtering capabilities

## Installation

### Windows 7 Installation Steps

1. **Install Python 3.8.x**
   - Download Python 3.8.x from [python.org](https://www.python.org/downloads/windows/)
   - During installation, check "Add Python to PATH"
   - Verify installation: `python --version`

2. **Install Dependencies**
   ```bash
   # Navigate to the project directory
   cd path\to\Weinig_Hydromat\XXX
   
   # Install required packages
   pip install -r requirements.txt
   ```

3. **Run Compatibility Check**
   ```bash
   python check_win7_compatibility.py
   ```
   Follow any instructions to resolve compatibility issues.

4. **Run the Application**
   ```bash
   python main.py
   ```

### Creating a Windows Executable (Optional)

To create a standalone executable for Windows 7:

```bash
# Install PyInstaller
pip install pyinstaller==4.10

# Build the executable
python -m PyInstaller --onefile --windowed --icon=img/icon.ico main.py

# The executable will be in the 'dist' folder
```

## Troubleshooting Windows 7 Issues

### Common Issues and Solutions

1. **Application fails to start**
   - Ensure all prerequisites are installed
   - Run the application as administrator
   - Check the `logs` folder for error messages

2. **Display issues**
   - Right-click the application shortcut
   - Select Properties > Compatibility
   - Check "Disable display scaling on high DPI settings"
   - Try different compatibility modes if needed

3. **Missing DLL errors**
   - Install the latest Visual C++ Redistributable
   - Run Windows Update to install missing system files

4. **Performance issues**
   - Close other applications
   - Disable visual effects in Windows Performance Options
   - Run the application in Windows 7 Basic theme

## Support

For Windows 7 specific issues, please include:
- Windows version and service pack level
- Python version (`python --version`)
- Contents of `logs/weinig_tool_manager.log`
- Screenshot of any error messages

## Installation

### Using pip (recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/weinig-tool-manager.git
cd wenig-tool-manager

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py