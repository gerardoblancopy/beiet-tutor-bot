# How to Set Up and Deploy BEIET

This guide will walk you through the steps to configure and run the BEIET Discord Tutor Bot on your local machine or a cloud environment like Hugging Face Spaces.

## Prerequisites

Before you begin, ensure you have the following installed and ready:
- **Python 3.11+**
- **Git**
- A **Discord account** and permissions to add bots to a server.
- A **Google AI Studio account** for the Gemini API.

## Step 1: Clone the Repository

Clone the project to your local machine:

```bash
git clone https://github.com/gerardoblancopy/beiet-tutor-bot.git
cd beiet-tutor-bot
```

## Step 2: Set Up the Virtual Environment

It is recommended to use a virtual environment to manage dependencies:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

Install the required packages:

```bash
pip install -r requirements.txt
```

## Step 3: Configure Environment Variables

The bot relies on several connection strings and API keys to function. 

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` in your text editor.
3. Replace the placeholder values with your actual credentials:
   - `DISCORD_TOKEN`: Obtain this from the [Discord Developer Portal](https://discord.com/developers/applications).
   - `GEMINI_API_KEY`: Obtain this from [Google AI Studio](https://aistudio.google.com/).

## Step 4: Run the Bot

Start the bot by executing the main Python module:

```bash
python -m bot.main
```

If everything is configured correctly, you should see logs indicating the database tables were created and the bot connected to Discord successfully.

## Next Steps
- Head over to your Discord server and type `/registro` to create your student profile.
- See the [How to Ingest Documents for RAG](how-to-ingest-documents.md) guide to load the course material into ChromaDB.
