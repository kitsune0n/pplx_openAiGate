# pplx_openAiGate

This project provides a Flask-based web server that acts as an adapter between the OpenAI API format and Unofficial API Wrapper for Perplexity.ai (pip package `perplexity_api_async ` from [helallao/perplexity-ai](https://github.com/helallao/perplexity-ai)). It allows you to use Perplexity's search capabilities and access its underlying language models through tools or applications that expect an OpenAI-compatible endpoint.

## Features

*   OpenAI-compatible `/v1/chat/completions` endpoint.
*   OpenAI-compatible `/v1/models` endpoint listing available Perplexity modes/models.
*   Supports various Perplexity modes (`pro`, `reasoning`, `auto`, `deep research`) and specific models within those modes.
*   Handles text prompts and file uploads (text and images via multipart/form-data or base64 data URLs).
*   Supports different search sources: `web`, `scholar`, `social`, or `None` (disables external search, default behavior).
*   Requires API key authentication (`Bearer` token).
*   Configurable via command-line arguments or environment variables.
*   Can use Perplexity account cookies for potentially personalized results or access to Pro features.
<details>
<summary>Available Models</summary>
<ul>
    <li>pro-default</li>
    <li>pro-sonar</li>
    <li>pro-gpt-4.5</li>
    <li>pro-gpt-4o</li>
    <li>pro-claude-3.7-sonnet</li>
    <li>pro-gemini-2.0-flash</li>
    <li>pro-grok-2</li>
    <li>reasoning-default</li>
    <li>reasoning-r1</li>
    <li>reasoning-o3-mini</li>
    <li>reasoning-claude-3.7-sonnet</li>
    <li>deep-research</li>
</ul>
</details>
## Setup

### Prerequisites

*   Python 3.8+
*   Docker and Docker Compose (for Docker method)
*   Git

### Getting Perplexity Cookies

Using your own Perplexity account cookies might provide access to Pro features or personalized results if you are logged in.

1.  Open the [Perplexity.ai](https://perplexity.ai) website and log in to your account.
2.  Press `F12` or `Ctrl + Shift + I` (or `Cmd + Option + I` on Mac) to open your browser's developer tools (inspector).
3.  Go to the "Network" tab in the inspector.
4.  Refresh the Perplexity page (F5 or Ctrl+R).
5.  Find the first request in the list (usually to `perplexity.ai` or similar). Right-click on it.
6.  Hover over "Copy" (or similar option) and select "Copy as cURL (bash)".
7.  Go to a cURL converter website like [curlconverter.com/python/](https://curlconverter.com/python/).
8.  Paste the copied cURL command into the input box.
9.  Look for the `cookies = {...}` dictionary in the generated Python code.
10. Copy the entire dictionary assignment, including `cookies = {`, all the key-value pairs inside the curly braces `{}`, and the closing brace `}`.
11. Create a file named `cookies.txt` in the root directory of this project.
12. Paste the copied dictionary into the `cookies.txt` file and save it.

## Running the Application

You can run the adapter using Python directly or via Docker.

### Method 1: Using Python Directly

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/kitsune0n/pplx_openAiGate.git # Replace with your repo URL if different
    cd pplx_openAiGate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Create `cookies.txt`:** Follow the instructions in the "Getting Perplexity Cookies" section above to create `cookies.txt` in the project root.

4.  **Set API Key:** You need to provide an API key for clients to authenticate. You can set it via an environment variable or command-line argument. This key is *not* your Perplexity API key (this adapter doesn't use the official Perplexity API), but a secret key *you* define for accessing *this* adapter.
    ```bash
    # Option A: Environment Variable
    export PPLX_OPENAI_KEY="your-chosen-secret-key"

    # Option B: Command-line argument (see below)
    ```

5.  **Run the application:**
    ```bash
    python3 app.py \
        --port 5010 \
        --api-key "your-chosen-secret-key" \
        --cookies-file "cookies.txt" \
        --prefix "perplexity-chat"
        # Add other options as needed, e.g., --sources web scholar
    ```
    *   `--port`: Port to run the server on (default: 5010).
    *   `--api-key`: The secret API key clients must use (overrides `PPLX_OPENAI_KEY` env var). Default: "your-secret-api-key". **Change this!**
    *   `--cookies-file`: Path to the cookies file (default: `cookies.txt`).
    *   `--prefix`: Prefix for model IDs (default: `perplexity-chat`).
    *   `--sources`: Space-separated list of sources (e.g., `web scholar social`).
    *   `--language`: Language code (default: `en-US`).
    *   `--incognito`: Run in incognito mode (boolean flag).

    Use `python3 app.py --help` to see all available options.

### Method 2: Using Docker

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/kitsune0n/pplx_openAiGate.git # Replace with your repo URL if different
    cd pplx_openAiGate
    ```

2.  **Create `cookies.txt`:** Follow the instructions in the "Getting Perplexity Cookies" section above to create `cookies.txt` in the project root. The `docker-compose.yml` file is configured to mount this file into the container.

3.  **Configure Environment Variables:** Edit the `docker-compose.yml` file or create a `.env` file in the project root to set necessary variables, especially `PPLX_OPENAI_KEY`.
    *   **`docker-compose.yml`:** Modify the `environment` section under the `perplexity-api` service.
    *   **`.env` file (Recommended):** Create a file named `.env` with content like:
        ```dotenv
        PORT=5010
        PPLX_OPENAI_KEY=your-chosen-secret-key # Change this!
        COOKIES_FILE=/app/cookies.txt
        LANGUAGE=en-US
        INCOGNITO=false
        SOURCES= # e.g., web scholar
        PREFIX=perplexity-chat
        ```
    **Important:** Make sure to set a secure `PPLX_OPENAI_KEY`.

4.  **Build and run the container:**
    ```bash
    docker-compose up -d --build
    ```
    The service will be available on the host machine at the specified port (default: 5010).

## Configuration

The application can be configured via command-line arguments (when running with Python) or environment variables (recommended for Docker).

*   **`PORT`**: Port number (Default: `5010`)
*   **`PPLX_OPENAI_KEY`**: Secret key for client authentication (Default: `"your-secret-api-key"`) - **Must be changed for security.**
*   **`COOKIES_FILE`**: Path to the Perplexity cookies file (Default: `cookies.txt` in Python, `/app/cookies.txt` in Docker)
*   **`LANGUAGE`**: Language for Perplexity (Default: `en-US`)
*   **`INCOGNITO`**: Enable incognito mode (`true`/`false`) (Default: `false`)
*   **`SOURCES`**: Space-separated search sources (e.g., `"web scholar"`). Determines where Perplexity should search for information.
    *   `web`: General web search.
    *   `scholar`: Search academic papers and sources.
    *   `social`: Search social media platforms like Reddit.
    *   `None` or empty string (`""`): Disables external searching, making the model behave more like a standard LLM without real-time web access. (Default: `""`)
*   **`PREFIX`**: Prefix for generated model IDs (Default: `perplexity-chat`)

When using Docker, the environment variables defined in `docker-compose.yml` or the `.env` file are passed to the `app.py` script as command-line arguments inside the container (see `CMD` in `Dockerfile`).

## Usage

This adapter exposes OpenAI-compatible endpoints.

### Getting Available Models

To see the list of available Perplexity models/modes formatted for OpenAI compatibility, send a `GET` request to the `/v1/models` endpoint.

**Example using `curl`:**

```bash
curl http://<your-server-ip>:<port>/v1/models \
  -H "Authorization: Bearer <your-chosen-secret-key>"
```

Replace `<your-server-ip>`, `<port>`, and `<your-chosen-secret-key>` with your actual values.

### Sending Chat Requests

Send `POST` requests to the chat completions endpoint: `/v1/chat/completions`.

Follow the standard OpenAI API format for the request body:

*   **Headers:** Include `Authorization: Bearer <your-chosen-secret-key>` and `Content-Type: application/json`.
*   **Body (JSON):**
    *   `model`: Specify the desired Perplexity model ID obtained from the `/v1/models` endpoint (e.g., `"perplexity-chat/pro-default"`).
    *   `messages`: Provide the conversation history/prompt in the standard OpenAI `messages` array format.
    *   (Optional) Other standard OpenAI parameters like `stream: true/false`.

*   **File Uploads:** For models supporting file uploads, use `multipart/form-data` or base64 data URLs in message content. (See OpenAI documentation for specifics on formatting these requests).

**Example using `curl` (Text Prompt):**

```bash
curl http://<your-server-ip>:<port>/v1/chat/completions \
   -H "Authorization: Bearer your-secret-api-key" \
   -H "Content-Type: application/json" \
   -d '{
         "model": "perplexity-chat/auto",
         "messages": [
           {"role": "user", "content": "Hello! What is the weather today?"}
         ]
       }'
```

Replace `<your-server-ip>`, `<port>`, and `<your-chosen-secret-key>` with your actual values. Adjust the `model` and `messages` payload as needed.

### Integrating with OpenAI Clients (e.g., OpenWebUI)

You can use this adapter with applications that support connecting to OpenAI-compatible APIs. Configure the client application with the following details:

*   **API Base URL / Endpoint:** `http://<your-server-ip>:<port>/v1`
*   **API Key:** `<your-chosen-secret-key>` (The one you set via `PPLX_OPENAI_KEY` or `--api-key`)
*   **Model Name:** After configuring the base URL and API key, the client should allow you to select from the models listed by the `/v1/models` endpoint (e.g., `perplexity-chat/pro-default`).

Don't use Stream mode, in openwebui or other client set Stream: False.

Replace `<your-server-ip>` with the actual IP address or hostname where the adapter is running, `<port>` with the configured port (default 5010), and `<your-chosen-secret-key>` with the API key you defined.

## License

This project is licensed under the [MIT License](LICENSE).

---
<div>
<a href="https://www.buymeacoffee.com/KitsuneOnline" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>
</div>

<small>USDT(TRC20):</small> `TB3WQiwmK8nRzTQN4NrqUoQbUtptBGbaMu`  
<small>SOL(SOLANA):</small> `0xd14227c1129d5f403ab4e8645b9ebfdfa5cd32b3`  
<small>BNB(BEP20):</small> `DGv49kioDhL9tgyd7JisquBtPNZkA1XPYpZzCL6SN69B`

