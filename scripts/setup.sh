#! /bin/bash

# Install TWS API following instructions from:
# https://www.interactivebrokers.com/campus/ibkr-api-page/twsapi-doc/#unix-install

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Find the 'trading' directory by traversing up from the script location
PROJECT_ROOT="$SCRIPT_DIR"
while [[ "$(basename "$PROJECT_ROOT")" != "trading" && "$PROJECT_ROOT" != "/" ]]; do
    PROJECT_ROOT="$(dirname "$PROJECT_ROOT")"
done

if [[ "$(basename "$PROJECT_ROOT")" != "trading" ]]; then
    echo "Error: Could not find 'trading' directory in the path hierarchy"
    exit 1
fi

TWS_VERSION="1030.01"
TWS_DOWNLOAD_URL="https://interactivebrokers.github.io/downloads/twsapi_macunix.${TWS_VERSION}.zip"
TWS_DOWNLOAD_FP="$PROJECT_ROOT/twsapi.zip"
TWS_INSTALL_DIR="$PROJECT_ROOT/.twsapi"

CP_DOWNLOAD_URL="https://download2.interactivebrokers.com/portal/clientportal.gw.zip"
CP_DOWNLOAD_FP="$PROJECT_ROOT/clientportal.gw.zip"
CP_INSTALL_DIR="$PROJECT_ROOT/.clientportal"

# check if curl is installed
if ! command -v curl &> /dev/null; then
    echo "curl is not installed. Installing curl..."
    
    # detect the operating system and install curl accordingly
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y curl
        else
            echo "Error: Unable to detect package manager. Please install curl manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install curl
        else
            echo "Error: Homebrew not found. Please install curl manually or install Homebrew first."
            exit 1
        fi
    else
        echo "Error: Unsupported operating system. Please install curl manually."
        exit 1
    fi
    
    # verify curl was installed successfully
    if ! command -v curl &> /dev/null; then
        echo "Error: Failed to install curl. Please install it manually."
        exit 1
    fi
    
    echo "curl installed successfully!"
else
    echo "curl is already installed."
fi

# check if unzip is installed
if ! command -v unzip &> /dev/null; then
    echo "unzip is not installed. Installing unzip..."
    
    # detect the operating system and install unzip accordingly
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y unzip
        else
            echo "Error: Unable to detect package manager. Please install unzip manually."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install unzip
        else
            echo "Error: Homebrew not found. Please install unzip manually or install Homebrew first."
            exit 1
        fi
    else
        echo "Error: Unsupported operating system. Please install unzip manually."
        exit 1
    fi
    
    # verify unzip was installed successfully
    if ! command -v unzip &> /dev/null; then
        echo "Error: Failed to install unzip. Please install it manually."
        exit 1
    fi
    
    echo "unzip installed successfully!"
else
    echo "unzip is already installed."
fi

if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo "Downloading TWS API..."
curl -L -o $TWS_DOWNLOAD_FP $TWS_DOWNLOAD_URL

echo "Unzipping TWS API..."
unzip -q -o $TWS_DOWNLOAD_FP -d $TWS_INSTALL_DIR

sudo chmod -R +x "$TWS_INSTALL_DIR/IBJts/source/pythonclient"

echo "Downloading Client Portal..."
curl -L -o $CP_DOWNLOAD_FP $CP_DOWNLOAD_URL

echo "Unzipping Client Portal..."
unzip -q -o $CP_DOWNLOAD_FP -d $CP_INSTALL_DIR

rm -rf $TWS_DOWNLOAD_FP $CP_DOWNLOAD_FP

echo "Installing dependencies..."
uv sync

echo "Installation complete!"

