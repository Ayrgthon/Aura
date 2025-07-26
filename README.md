# 🌟 Aura - Universal AI Assistant with Voice

Aura is an advanced artificial intelligence assistant that combines natural language processing, voice synthesis, and extended capabilities through the Model Context Protocol (MCP). It supports multiple AI models including Google Gemini and Ollama.

## 🚀 Key Features

- **🗣️ Voice Interface**: Spanish voice recognition and synthesis
- **🤖 Multiple Models**: Support for Google Gemini and Ollama
- **🔧 Model Context Protocol (MCP)**: Integration with external tools
- **🌐 Web Interface**: Modern frontend with React and Vite
- **📊 System Monitoring**: Real-time statistics visualization
- **🔄 WebSocket**: Real-time communication between frontend and backend

## 📋 Requirements

- Python 3.8+
- Node.js 16+
- npm or yarn
- Arch Linux (recommended) or any Linux distribution

## 🛠️ Installation

### 1. Clone the repository

```bash
git clone <your-repository>
cd Aura_Ollama
```

### 2. Configure environment variables

```bash
cp env.template .env
```

Edit the `.env` file and configure your API keys:

```env
# Google Gemini API
GOOGLE_API_KEY=your_google_api_key

# Brave Search API  
BRAVE_API_KEY=your_brave_api_key

# ElevenLabs API (for premium voice synthesis)
ELEVENLABS_API_KEY=your_elevenlabs_api_key

# Obsidian Vault path (optional)
OBSIDIAN_VAULT_PATH=/path/to/your/vault
```

### 3. Install dependencies

#### Backend (Python)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Frontend (Node.js)
```bash
cd frontend
npm install
cd ..
```

#### MCP Dependencies
```bash
npm install
```

### 4. Start the project

```bash
./start.sh
```

The script will automatically start:
- System statistics API (port 8000)
- WebSocket server (port 8765)
- React frontend (port 5173)

## 🎮 Usage

### Web Interface

1. Open your browser at `http://localhost:5173`
2. Click the microphone button to speak
3. The assistant will process your request and respond by voice

### Terminal Interface

You can also run Aura directly from the terminal:

```bash
cd src
python main.py
```

## 🔌 Model Context Protocol (MCP)

Aura integrates several MCP servers that extend its capabilities:

### 📁 Filesystem MCP
Allows Aura to access and manipulate files in specific system directories.

**Available functions:**
- `list_directory`: Lists the contents of a directory
- `read_file`: Reads the contents of a file
- `write_file`: Writes or modifies files
- `create_directory`: Creates new directories
- `delete_file`: Deletes files
- `move_file`: Moves or renames files

**Configuration:**
Allowed directories are automatically configured based on existing system directories (Documents, Downloads, etc.).

### 🔍 Brave Search MCP
Enables real-time web searches using the Brave search engine.

**Available functions:**
- `brave_search`: Searches for updated information on the web
- `brave_local_search`: Search for local businesses and places
- `brave_news_search`: Specific news search

**Typical usage:**
- "Search for the latest news about AI"
- "What's the current weather in Madrid?"
- "Find information about Python 3.12"

### 🗃️ Obsidian Memory MCP
Integration with Obsidian to create a persistent memory system.

**Available functions:**
- `search_notes`: Search notes by content, tags, or wikilinks
- `read_note`: Reads the complete content of a note
- `create_note`: Creates new notes in the vault
- `update_note`: Updates existing notes
- `list_vault_structure`: Lists the vault structure
- `get_note_metadata`: Gets note metadata

**Configuration:**
Configure your Obsidian vault path in the `.env` file:
```env
OBSIDIAN_VAULT_PATH=/home/user/Documents/My Vault
```

### 📝 Notion MCP
Integration with Notion API for managing pages, databases, and content.

**Available functions:**
- `search_pages`: Search for pages in your Notion workspace
- `get_page`: Retrieve page content and properties
- `create_page`: Create new pages in databases or as children of existing pages
- `update_page`: Update page properties and content
- `get_database`: Retrieve database structure and entries
- `query_database`: Query database entries with filters
- `create_database`: Create new databases
- `get_block_children`: Get child blocks of a page
- `append_block_children`: Add new blocks to a page
- `update_block`: Update block content
- `delete_block`: Delete blocks from pages

**Typical usage:**
- "Create a new page in my project database"
- "Search for pages about AI research"
- "Update the status of my task in the project tracker"
- "Add a new entry to my reading list database"
- "Get all pages tagged with 'important'"

**Configuration:**
Configure your Notion API key in the `.env` file:
```env
NOTION_API_KEY=your_notion_integration_token
```

To get your Notion API key:
1. Go to https://www.notion.so/my-integrations
2. Create a new integration
3. Copy the "Internal Integration Token"
4. Add it to your `.env` file

**Important:** You need to share your Notion pages/databases with your integration for Aura to access them.

### 🌐 Playwright MCP
Advanced web automation for navigation, scraping, and web searches.

**Available functions:**
- `goto`: Navigate to specific URLs
- `click`: Click on page elements
- `fill`: Fill search forms
- `textContent`: Extract text from elements
- `screenshot`: Capture screenshots
- `evaluate`: Execute custom JavaScript
- `waitForSelector`: Wait for specific elements

**Typical usage for Ecommerce:**
- "Search for iPhone 15 price on Amazon"
- "Compare laptop prices on MercadoLibre"
- "Extract product information from eBay"
- "Browse online store catalogs"

**Configuration:**
Playwright is automatically installed with the necessary browsers. No additional configuration required.

## 🎨 Project Architecture

```
Aura_Ollama/
├── src/                    # Main source code
│   ├── main.py            # Main entry point
│   ├── client.py          # AI client (Gemini/Ollama)
│   ├── websocket_server.py # WebSocket server
│   └── system_stats_api.py # Statistics API
├── voice/                  # Voice modules
│   ├── hear.py            # Voice recognition
│   ├── speak.py           # Voice synthesis
│   └── vosk-model-es-0.42/ # Spanish voice model
├── mcp/                    # MCP servers
│   └── obsidian_memory_server.js
├── frontend/               # React application
│   ├── src/
│   ├── public/
│   └── package.json
├── logs/                   # Log files
├── .env                    # Environment variables
├── requirements.txt        # Python dependencies
├── package.json           # Node.js dependencies
└── start.sh               # Startup script
```

## 🔧 Advanced Configuration

### Changing the AI model

By default, Aura uses Google Gemini. To change to Ollama:

1. Install Ollama: https://ollama.ai
2. Download a model: `ollama pull qwen2.5-coder:7b`
3. When starting Aura, select the Ollama option

### Adding new MCPs

To add a new MCP server:

1. Install the MCP server:
```bash
npm install @modelcontextprotocol/server-example
```

2. Modify `src/main.py` or `src/websocket_server.py` to add the configuration:
```python
"example": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-example"],
    "transport": "stdio"
}
```

3. The server will be automatically available on the next run.

### Recommended MCP Configurations

**For Ecommerce (Option 9):**
- Filesystem + Brave Search + Playwright
- Ideal for price searches and comparisons

**For Productivity (Option 10):**
- Notion + Brave Search
- Perfect for managing notes, tasks, and research

**For Development (Option 11):**
- All MCPs (Filesystem + Brave Search + Obsidian Memory + Playwright + Notion)
- Maximum functionality available

**For Basic Searches (Option 7):**
- Obsidian Memory + Brave Search
- Balance between functionality and performance

**For Note Management (Option 5):**
- Notion only
- Focus on Notion workspace management

### Voice synthesis engines

Aura supports multiple TTS engines:

- **gTTS** (default): Free, requires internet connection
- **ElevenLabs**: High quality, requires API key
- **edge-tts**: Free, uses Microsoft Edge voices

To change the engine, use the command in the web interface or modify `voice/speak.py`.

## 🐛 Troubleshooting

### Voice recognition not working
- Verify you have a microphone connected
- Make sure the Vosk model is in `voice/vosk-model-es-0.42/`
- Check microphone permissions on your system

### WebSocket connection error
- Verify that port 8765 is not in use
- Check logs in `logs/websocket.log`

### Frontend not loading
- Make sure you've installed dependencies with `npm install`
- Verify that port 5173 is free
- Check logs in `logs/frontend.log`

## 📝 Logs

Logs are saved in the `logs/` folder:
- `backend_stats.log`: Statistics API
- `websocket.log`: WebSocket server
- `frontend.log`: React application

## 🤝 Contributions

Contributions are welcome. Please:
1. Fork the project
2. Create a branch for your feature (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is under the MIT License. See the `LICENSE` file for more details.

## 🙏 Acknowledgments

- Google Gemini and Ollama for AI models
- Vosk for offline voice recognition
- Model Context Protocol for the extensible architecture
- The open source community

---

**Developed with ❤️ by Ary** 