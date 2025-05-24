# Spew - AI-Powered Celebrity Educational Videos

**Built on Sieve** | _The Most Absurd Way to Actually Learn Stuff_

Spew transforms learning into entertainment by generating AI-powered videos featuring celebrity personas explaining complex topics. Want Steve Jobs to teach you quantum computing or Ariana Grande to explain machine learning? Spew makes it possible through cutting-edge AI technology built entirely on the Sieve platform.

## 🎭 What is Spew?

Users select from celebrity personas and request explanations on any topic, resulting in unique, engaging educational videos that make learning memorable and fun.

**Key Features:**

- 🎤 **Celebrity Voice Cloning**: Authentic voice synthesis for each persona
- 🎬 **Dynamic Video Generation**: AI-generated visuals synchronized with celebrity explanations
- 🤖 **Personality-Driven Scripts**: Content written in each celebrity's unique style
- 📱 **Twitter Bot Integration**: Automated video generation from social media mentions
- 🎨 **Modern Web Interface**: Beautiful dashboard for video creation

## 🏗️ Architecture

**Frontend**: Next.js web application with celebrity selection and real-time job tracking

**Backend**: Flask API with Twitter bot integration and SQLite database

**AI Pipeline (Sieve Functions)**:

1. **Script Generation** - Creates personality-specific educational scripts
2. **Speech Synthesis** - Converts scripts to cloned celebrity voices
3. **Visual Generation** - Creates dynamic educational graphics and animations
4. **Lip Sync Processing** - Applies audio to base celebrity videos
5. **Video Assembly** - Combines everything into final educational videos
6. **Orchestrator** - Coordinates the entire workflow with parallel processing

## 🎯 Celebrity Personas

- **🍎 Steve Jobs**: Innovation-focused with "thinking different" philosophy
- **🎵 Ariana Grande**: Sweet, encouraging with music industry references
- **📺 Kim Kardashian**: Valley girl explanations with lifestyle examples
- **🎬 Leonardo DiCaprio**: Charismatic Wolf of Wall Street style
- **🌍 David Attenborough**: Calm, authoritative nature explanations
- **🎤 Kanye West**: Confident, artistic genius perspectives
- And many more...

## 🤖 Twitter Bot

The `@SpewBot` automatically listens for mentions, parses requests using OpenAI, triggers the Sieve pipeline, and responds with generated videos.

```
@SpewBot Can Steve Jobs explain blockchain to me?
→ Generates and posts video of Steve Jobs explaining blockchain
```

## 🛠️ Technology Stack

- **AI Platform**: Sieve (all AI processing)
- **Frontend**: Next.js, React, TypeScript, Tailwind CSS
- **Backend**: Python, Flask, SQLite
- **Social Media**: Twitter API v2
- **Voice/Video**: S3-hosted models, FFmpeg via Sieve

## 🚀 Setup & Installation

### Frontend Setup (`/client`)

1. **Environment Configuration**

   ```bash
   cd client
   ```

   Create a `.env.local` file:

   ```env
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
   ```

2. **Install Dependencies**

   ```bash
   yarn install
   ```

3. **Run Development Server**
   ```bash
   yarn dev
   ```
   Or for production:
   ```bash
   yarn build && yarn start
   ```

The frontend will be available at `http://localhost:3000`

### Backend Setup (`/server`)

The backend setup is more complex than the frontend and involves multiple components: Python environment, API keys, Sieve account configuration, and function deployment.

#### 1. **Python Environment Setup**

```bash
cd server

# Create and activate Anaconda virtual environment
conda create -n spew-env python=3.11
conda activate spew-env

# Install dependencies
pip install -r requirements.txt
```

#### 2. **Environment Variables Configuration**

Create a `.env` file in the `server/` directory with the following variables:

```env
# Twitter API Configuration
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_KEY_SECRET=your_twitter_api_key_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
TWITTER_BOT_USERNAME=@YourBotUsername

# AI/LLM API Keys
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# PlayHT TTS Configuration (for voice synthesis)
PLAYHT_TTS_USER=your_playht_user_id
PLAYHT_TTS_API_KEY=your_playht_api_key

# Flask Configuration (Optional)
FLASK_DEBUG=true
FLASK_HOST=0.0.0.0
FLASK_PORT=8000
LOG_LEVEL=INFO
MENTIONS_POLLING_INTERVAL_SECONDS=1,200
```

#### 3. **Sieve Account Setup**

1. **Create Sieve Account**: Sign up at [sieve.cloud](https://sieve.cloud)

2. **Set Environment Variables in Sieve**:
   Add all the API keys to your Sieve environment variables dashboard:

   - `OPENAI_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `PLAYHT_TTS_USER`
   - `PLAYHT_TTS_API_KEY`

3. **Authenticate Sieve CLI**:
   ```bash
   sieve login
   ```

#### 4. **Deploy Sieve Functions**

Deploy all AI processing functions to Sieve:

```bash
# Deploy all Sieve functions
sieve deploy sieve_functions/script_generator.py
sieve deploy sieve_functions/speech_synthesizer.py
sieve deploy sieve_functions/visuals_generator.py
sieve deploy sieve_functions/lipsync_processor.py
sieve deploy sieve_functions/video_assembler.py
sieve deploy sieve_functions/orchestrator.py
```

#### 5. **Run the Applications**

**Start the Flask API Server**:

```bash
python app.py
```

The API will be available at `http://localhost:8000`

**Run the Twitter Bot**:

```bash
python twitter_bot/run_bot.py
```

**Optional: Test Bot Setup**:

```bash
python twitter_bot/run_bot.py --check-status
```

#### 6. **Required Data Files**

Ensure the following data files exist:

- `data/personas.json` - Celebrity persona configurations
- `data/base_videos/` - Base video files for each persona
- `data/database.db` - SQLite database (auto-created if missing)

---

**Important Notes**:

- The bot requires all Twitter API credentials with appropriate permissions
- Sieve functions must be deployed before running the bot or API
- PlayHT account needed for high-quality voice synthesis
- The system uses both OpenAI and Anthropic APIs for different processing steps

## 🚀 Powered by Sieve

Spew showcases Sieve's power for complex AI workflows with seamless integration, parallel processing, and automatic scaling. The entire video generation pipeline—from script creation to final assembly—runs on Sieve, demonstrating how sophisticated AI applications can be built using Sieve's function-based architecture.

---

**Spew** represents the future of educational content—where learning meets entertainment through AI. Built entirely on Sieve, it creates engaging, personalized experiences that make education both effective and fun.

_Ready to make learning ridiculously entertaining? Try Spew today!_
