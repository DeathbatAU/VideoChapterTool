#!/bin/bash

# Cross-platform installer for Python, ffmpeg, moviepy, and yt-dlp
# Supports Linux (apt/yum/dnf/pacman), macOS (homebrew), and Windows (chocolatey)
# Also installs tkinter for GUI applications

set -e  # Exit on any error

echo "🚀 Installing Python, ffmpeg, moviepy, and yt-dlp dependencies..."
echo "================================================"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Python packages
install_python_packages() {
    echo "📦 Installing Python packages..."
    
    # Upgrade pip first
    python3 -m pip install --upgrade pip
    
    # Install moviepy and yt-dlp
    python3 -m pip install moviepy yt-dlp
    
    echo "✅ Python packages installed successfully"
}

# Detect operating system
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🐧 Detected Linux system"
    
    # Detect package manager and install Python + dependencies
    if command_exists apt-get; then
        echo "📦 Using apt package manager..."
        sudo apt update
        sudo apt install -y python3 python3-pip python3-tk ffmpeg
    elif command_exists yum; then
        echo "📦 Using yum package manager..."
        sudo yum install -y epel-release
        sudo yum install -y python3 python3-pip python3-tkinter ffmpeg
    elif command_exists dnf; then
        echo "📦 Using dnf package manager..."
        sudo dnf install -y python3 python3-pip python3-tkinter ffmpeg
    elif command_exists pacman; then
        echo "📦 Using pacman package manager..."
        sudo pacman -Sy python python-pip tk ffmpeg --noconfirm
    else
        echo "❌ No supported package manager found (apt, yum, dnf, pacman)"
        echo "Please install Python, ffmpeg, and tkinter manually for your distribution"
        exit 1
    fi
    
    install_python_packages

elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 Detected macOS system"
    
    # Check if Homebrew is installed
    if ! command_exists brew; then
        echo "📦 Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    echo "📦 Installing Python and ffmpeg via Homebrew..."
    brew install python ffmpeg
    
    install_python_packages

elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ "$OS" == "Windows_NT" ]]; then
    echo "🪟 Detected Windows system"
    
    # Check if Chocolatey is installed
    if ! command_exists choco; then
        echo "📦 Installing Chocolatey..."
        powershell -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
    fi
    
    echo "📦 Installing Python and ffmpeg via Chocolatey..."
    choco install python ffmpeg -y
    
    # Refresh PATH
    refreshenv
    
    install_python_packages

else
    echo "❌ Unsupported operating system: $OSTYPE"
    echo "Please install dependencies manually:"
    echo "1. Install Python from https://python.org/downloads/"
    echo "2. Install ffmpeg from https://ffmpeg.org/download.html"
    echo "3. Install Python packages: pip install moviepy yt-dlp"
    exit 1
fi

echo ""
echo "🎉 Installation completed successfully!"
echo "================================================"
echo "Installed components:"
echo "✅ Python 3 - Programming language and runtime"
echo "✅ pip - Python package installer (included with Python)"
echo "✅ tkinter - Python GUI toolkit (for desktop applications)"
echo "✅ ffmpeg - Video/audio processing"
echo "✅ moviepy - Python video editing library"
echo "✅ yt-dlp - YouTube downloader"
echo ""
echo "You can now use these tools in your scripts!"

# Verify installations
echo "🔍 Verifying installations..."
echo ""

if command_exists python3; then
    echo "✅ Python: $(python3 --version)"
else
    echo "❌ Python 3 not found in PATH"
fi

if python3 -c "import tkinter" 2>/dev/null; then
    echo "✅ tkinter: Available"
else
    echo "❌ tkinter not available"
fi

if command_exists ffmpeg; then
    echo "✅ ffmpeg: $(ffmpeg -version | head -n1)"
else
    echo "❌ ffmpeg not found in PATH"
fi

if python3 -c "import moviepy" 2>/dev/null; then
    echo "✅ moviepy: $(python3 -c "import moviepy; print(f'v{moviepy.__version__}')" 2>/dev/null || echo "installed")"
else
    echo "❌ moviepy not available"
fi

if command_exists yt-dlp; then
    echo "✅ yt-dlp: $(yt-dlp --version)"
else
    echo "❌ yt-dlp not found in PATH"
fi

echo ""
echo "📝 Note: You may need to restart your terminal or run 'source ~/.bashrc' for PATH changes to take effect."