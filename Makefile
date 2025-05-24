# Spew - AI-Powered Celebrity Educational Videos
# Makefile for development and deployment

# Variables
CONDA_ENV_NAME = spew-env
PYTHON_VERSION = 3.11
CLIENT_DIR = client
SERVER_DIR = server
SIEVE_FUNCTIONS_DIR = server/sieve_functions

# Default target
.PHONY: help
help:
	@echo "🎭 Spew - AI-Powered Celebrity Educational Videos"
	@echo "================================================="
	@echo ""
	@echo "Available targets:"
	@echo "  setup-all          - Complete project setup (conda env + dependencies)"
	@echo "  setup-conda        - Create and setup conda environment"
	@echo "  install-deps       - Install all dependencies (client + server)"
	@echo "  install-client     - Install client dependencies"
	@echo "  install-server     - Install server dependencies"
	@echo ""
	@echo "  dev                - Run both client and server in development mode"
	@echo "  dev-client         - Run client development server"
	@echo "  dev-server         - Run Flask API server"
	@echo "  run-bot           - Run Twitter bot"
	@echo "  check-bot         - Check Twitter bot status"
	@echo ""
	@echo "  deploy-sieve      - Deploy all Sieve functions"
	@echo "  deploy-functions  - Deploy individual Sieve functions"
	@echo "  sieve-login       - Login to Sieve"
	@echo ""
	@echo "  build-client      - Build client for production"
	@echo "  start-client      - Start client in production mode"
	@echo "  clean             - Clean build artifacts and cache"

# Environment Setup
.PHONY: setup-all
setup-all: setup-conda install-deps
	@echo "✅ Complete setup finished!"
	@echo "Next steps:"
	@echo "  1. Configure your .env file in server/ directory"
	@echo "  2. Run 'make sieve-login' to authenticate with Sieve"
	@echo "  3. Run 'make deploy-sieve' to deploy AI functions"
	@echo "  4. Run 'make dev' to start development servers"

.PHONY: setup-conda
setup-conda:
	@echo "🐍 Setting up Anaconda environment..."
	conda create -n $(CONDA_ENV_NAME) python=$(PYTHON_VERSION) -y
	@echo "✅ Conda environment '$(CONDA_ENV_NAME)' created!"
	@echo "💡 Activate with: conda activate $(CONDA_ENV_NAME)"

# Dependencies
.PHONY: install-deps
install-deps: install-client install-server

.PHONY: install-client
install-client:
	@echo "📱 Installing client dependencies..."
	cd $(CLIENT_DIR) && yarn install
	@echo "✅ Client dependencies installed!"

.PHONY: install-server
install-server:
	@echo "🔧 Installing server dependencies..."
	@echo "💡 Make sure conda environment is activated: conda activate $(CONDA_ENV_NAME)"
	cd $(SERVER_DIR) && pip install -r requirements.txt
	@echo "✅ Server dependencies installed!"

# Development
.PHONY: dev
dev:
	@echo "🚀 Starting development servers..."
	@echo "💡 This will run both client and server"
	@echo "📱 Client: http://localhost:3000"
	@echo "🔧 Server: http://localhost:8000"
	$(MAKE) -j2 dev-client dev-server

.PHONY: dev-client
dev-client:
	@echo "📱 Starting client development server..."
	cd $(CLIENT_DIR) && yarn dev

.PHONY: dev-server
dev-server:
	@echo "🔧 Starting Flask API server..."
	@echo "💡 Make sure conda environment is activated: conda activate $(CONDA_ENV_NAME)"
	cd $(SERVER_DIR) && python app.py

.PHONY: run-bot
run-bot:
	@echo "🤖 Starting Twitter bot..."
	@echo "💡 Make sure conda environment is activated: conda activate $(CONDA_ENV_NAME)"
	cd $(SERVER_DIR) && python twitter_bot/run_bot.py

.PHONY: check-bot
check-bot:
	@echo "📊 Checking Twitter bot status..."
	@echo "💡 Make sure conda environment is activated: conda activate $(CONDA_ENV_NAME)"
	cd $(SERVER_DIR) && python twitter_bot/run_bot.py --check-status

# Sieve Deployment
.PHONY: sieve-login
sieve-login:
	@echo "🔐 Logging into Sieve..."
	sieve login

.PHONY: deploy-sieve
deploy-sieve: deploy-functions
	@echo "✅ All Sieve functions deployed!"

.PHONY: deploy-functions
deploy-functions:
	@echo "🚀 Deploying Sieve functions..."
	@echo "💡 Make sure you're logged into Sieve: make sieve-login"
	cd $(SERVER_DIR) && sieve deploy sieve_functions/script_generator.py
	cd $(SERVER_DIR) && sieve deploy sieve_functions/speech_synthesizer.py
	cd $(SERVER_DIR) && sieve deploy sieve_functions/visuals_generator.py
	cd $(SERVER_DIR) && sieve deploy sieve_functions/lipsync_processor.py
	cd $(SERVER_DIR) && sieve deploy sieve_functions/video_assembler.py
	cd $(SERVER_DIR) && sieve deploy sieve_functions/orchestrator.py
	@echo "✅ All functions deployed to Sieve!"

# Production
.PHONY: build-client
build-client:
	@echo "🏗️ Building client for production..."
	cd $(CLIENT_DIR) && yarn build
	@echo "✅ Client build complete!"

.PHONY: start-client
start-client:
	@echo "🚀 Starting client in production mode..."
	cd $(CLIENT_DIR) && yarn start

# Maintenance
.PHONY: clean
clean:
	@echo "🧹 Cleaning build artifacts and cache..."
	cd $(CLIENT_DIR) && rm -rf .next node_modules/.cache
	cd $(SERVER_DIR) && find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	cd $(SERVER_DIR) && find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Clean complete!"

# Individual Sieve function deployments (for debugging)
.PHONY: deploy-script
deploy-script:
	cd $(SERVER_DIR) && sieve deploy sieve_functions/script_generator.py

.PHONY: deploy-speech
deploy-speech:
	cd $(SERVER_DIR) && sieve deploy sieve_functions/speech_synthesizer.py

.PHONY: deploy-visuals
deploy-visuals:
	cd $(SERVER_DIR) && sieve deploy sieve_functions/visuals_generator.py

.PHONY: deploy-lipsync
deploy-lipsync:
	cd $(SERVER_DIR) && sieve deploy sieve_functions/lipsync_processor.py

.PHONY: deploy-assembler
deploy-assembler:
	cd $(SERVER_DIR) && sieve deploy sieve_functions/video_assembler.py

.PHONY: deploy-orchestrator
deploy-orchestrator:
	cd $(SERVER_DIR) && sieve deploy sieve_functions/orchestrator.py 