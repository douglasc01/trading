# trading

This project provides broker clients designed for easy integration into your own trading strategy loops. By abstracting away the complexities of broker APIs, you can focus on developing and testing your trading strategies with minimal setup.

## Features

- Ready-to-use broker clients for algorithmic trading
- Simple interfaces for requesting market data, placing orders, and managing positions
- Designed for seamless use in custom strategy loops
- Currently only supports IBKR TWS API

## Getting Started

### Prerequisites

- **macOS** or **Linux** machine
- [Just](https://just.systems/) command runner installed

### Setup Instructions

1. **Install Just**

   On macOS (using Homebrew):

   ```sh
   brew install just
   ```

   On Linux (using Homebrew):

   ```sh
   brew install just
   ```

   Or, follow the [official installation instructions](https://just.systems/man/en/#installation) for your platform.

2. **Clone the Repository**

   ```sh
   git clone <your-repo-url>
   cd <your-repo-directory>
   ```

3. **Run the Setup Command**

   Use the provided `just` recipe to set up the project:

   ```sh
   just setup
   ```

   This will make sure all dependencies are installed and the environment is ready for development.

## Usage

After setup, you can start implementing your trading strategies by importing and using the provided broker clients in your own strategy loops.

Here's a minimal example of how to use the IBKRClient by subclassing it and implementing your own strategy loop:

```
import threading

from trading.clients.ibkr_client import IBKRClient, TWSConnectionConfig

class DummyStrategy(IBKRClient):
    def strategy_loop(self, stop_event: threading.Event) -> None:
        # strategy logic here

strategy = DummyStrategy(
    connection_config=TWSConnectionConfig(
        host="0.0.0.0",
        port="7497,
        client_id=1,
    ),
)
strategy.start()
```
