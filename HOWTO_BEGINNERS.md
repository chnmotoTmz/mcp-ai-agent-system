# Getting Started with the MCP AI Agent System (Beginner's Guide)

## 1. What is this? (Introduction)

Welcome to the MCP AI Agent System! In simple terms, this system is like a smart assistant that can take your messages from the LINE app and automatically turn them into blog posts on your Hatena Blog. It uses Artificial Intelligence (AI) with Google's Gemini to help create content, and can even handle images you send!

This guide is for you if you're new to this kind of system and want to try out its main feature: automatically posting from LINE to Hatena Blog. We'll keep things simple and guide you step-by-step.

## 2. Before You Start (Prerequisites)

Here's what you'll need to get going:

**On your computer:**

*   **Python 3**: This system is written in Python. If you don't have it, you can download it from [python.org](https://www.python.org/). (Usually, Python 3.8 or newer is good).
*   **Git**: This tool helps you copy the project's code to your computer. If you don't have it, you can find installation instructions at [git-scm.com](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git).

**Accounts you'll need:**

*   **A LINE account**: And access to the [LINE Developers Console](https://developers.line.biz/console/) to create a "Messaging API channel" (this is your LINE bot).
*   **A Google Account**: To get a Gemini API Key from [Google AI Studio](https://aistudio.google.com/app/apikey) (or Google Cloud).
*   **A Hatena Blog account**: This is where your blog posts will appear. You'll also need your Hatena ID, Blog ID, and API key from your Hatena settings page.
*   **An Imgur account**: For uploading images. You'll need to register an application to get a Client ID from [Imgur API Registration](https://api.imgur.com/oauth2/addclient).

**API Keys (Your Secret Passwords):**

Think of API keys as special passwords that let different services talk to each other securely. You'll need to get these from the services listed above. Keep them safe!

## 3. Setting Up the System (Step-by-Step)

Let's get the system set up on your computer.

### Step 3.1: Get the Code

1.  Open your terminal or command prompt.
2.  Use `git` to copy (clone) the project files:
    ```bash
    git clone https://github.com/chnmotoTmz/mcp-ai-agent-system.git
    ```
3.  This will create a folder named `mcp-ai-agent-system`. Go into this folder:
    ```bash
    cd mcp-ai-agent-system
    ```

### Step 3.2: Run the Basic Setup

This project comes with a setup script to help install some of the tools it needs.

1.  In your terminal, still inside the `mcp-ai-agent-system` folder, run these commands:
    ```bash
    chmod +x setup_mcp.sh
    ./setup_mcp.sh
    ```
    This script might ask for your password as it installs software. It will install Python libraries and other tools.

### Step 3.3: Configure Your Secrets (API Keys)

The system needs your API keys to connect to LINE, Gemini, Hatena, and Imgur.

1.  Copy the example environment file:
    In your terminal, run:
    ```bash
    cp .env.example .env
    ```
    This creates a new file named `.env`. This file is ignored by Git, so your secret keys stay private to you.

2.  Edit the `.env` file:
    Open the `.env` file in a text editor. You'll see lines like `KEY_NAME=your_key_here`. You need to replace `your_key_here` with your actual API keys.

    Here are the **essential keys** you need to fill in:

    ```env
    # LINE Bot settings
    LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
    LINE_CHANNEL_SECRET=your_line_channel_secret_here

    # Gemini API settings
    GEMINI_API_KEY=your_gemini_api_key_here

    # Hatena Blog settings
    HATENA_USER_ID=your_hatena_user_id_here  # Your Hatena ID
    HATENA_BLOG_ID=your_hatena_blog_id_here  # e.g., myblog.hatenablog.com
    HATENA_API_KEY=your_hatena_api_key_here # Found in Hatena settings

    # Imgur API settings (for image uploads)
    IMGUR_CLIENT_ID=your_imgur_client_id_here # Get this from api.imgur.com/oauth2/addclient

    # Other (usually fine as default, but SECRET_KEY should be changed for security if you expose this online)
    SECRET_KEY=a_very_secret_key_please_change_me
    PORT=8084
    # GEMINI_MODEL=gemini-1.5-flash-preview-05-20 # You can often leave this as is
    ```

    *   **LINE Keys**: Find these in your [LINE Developers Console](https://developers.line.biz/console/) under your Messaging API channel's "Channel basic settings" and "Messaging API" tabs.
    *   **GEMINI_API_KEY**: Get this from [Google AI Studio](https://aistudio.google.com/app/apikey).
    *   **HATENA Keys**:
        *   `HATENA_USER_ID`: Your Hatena username.
        *   `HATENA_BLOG_ID`: Your main blog URL (e.g., `yourusername.hatenablog.com`).
        *   `HATENA_API_KEY`: Found in your Hatena Blog's settings page (詳細設定 -> APIキー).
    *   **IMGUR_CLIENT_ID**: Register an application at [Imgur API](https://api.imgur.com/oauth2/addclient). Choose "Anonymous usage without user authorization" for the simplest setup.

    **Important**: Make sure there are no extra spaces or quotes around your keys in the `.env` file.

### Step 3.4: Start the System

Now you're ready to start the main application!

1.  In your terminal (still in the `mcp-ai-agent-system` folder), run:
    ```bash
    python3 start_mcp_system.py
    ```
2.  If everything is set up correctly, you should see some messages indicating the server has started, often including something like `* Running on http://127.0.0.1:8084/` (the address might vary slightly). This means the system is running and waiting for messages!

    Keep this terminal window open. If you close it, the system will stop.

## 4. Your First Automated Blog Post! (Core Functionality)

Now for the exciting part – making your first automated post.

### Step 4.1: Connect Your LINE Bot

Your LINE bot needs to know where to send messages. This is done by setting a "Webhook URL" in your LINE Developer Console.

*   **If your computer is directly accessible online (has a public IP address):**
    You can use `http://your_public_ip:8084/webhook` (replace `your_public_ip` with your computer's public IP and `8084` with the port shown when you started the system, if different).

*   **If your computer is on a local network (most home users):**
    LINE needs a public internet address to send messages to. For local testing, a tool like **ngrok** is very helpful.
    1.  Download and set up ngrok ([ngrok.com](https://ngrok.com/download)).
    2.  In a *new* terminal window, run ngrok to expose your local port 8084:
        ```bash
        ngrok http 8084
        ```
    3.  ngrok will show you a "Forwarding" URL that looks something like `https://randomstring.ngrok.io`. This is your public URL. **Use this HTTPS URL.**

**In your LINE Developer Console:**
1.  Go to your Messaging API channel.
2.  Find the "Webhook settings" section (usually under the "Messaging API" tab).
3.  Enter your Webhook URL:
    *   If using ngrok: `https://randomstring.ngrok.io/webhook` (make sure to add `/webhook` at the end).
    *   If using a public IP: `http://your_public_ip:8084/webhook`.
4.  Enable "Use webhook".
5.  You might see a "Verify" button. Clicking it should work if your system and ngrok (if used) are running.

### Step 4.2: Send a Message via LINE

1.  Open your LINE app on your phone.
2.  Find the bot you created and send it a message (e.g., "Hello world, this is my first AI blog post!").
3.  Try sending an image too!

### Step 4.3: Check Your Hatena Blog

1.  Wait a minute or two. The system needs time to process the message, talk to the AI, and post to Hatena.
2.  Go to your Hatena Blog. You should see a new post with the content from your LINE message! If you sent an image, it should also appear in the post (uploaded via Imgur).

Congratulations! You've made your first automated blog post.

## 5. Is it Working? (Checking System Status)

If you want to check if the system is running and responsive, you can use its status page.

1.  Open a web browser or use a command like `curl`.
2.  Go to `http://localhost:8084/status` (or `http://127.0.0.1:8084/status`).
3.  You should see a simple message indicating the system is alive, for example:
    ```json
    {"status": "ok", "message": "MCP AI Agent System is running"}
    ```
    (The exact message might vary).

## 6. What Next? (Further Learning)

You've just scratched the surface of what this system can do!

*   **Explore More Features**: This guide covered the basic LINE-to-Hatena flow of the main application. The project also includes a more advanced system using "LangGraph" for complex AI agent interactions.
*   **Read the Main Documentation**: For more details on architecture, advanced setup, deployment, and other features, check out the main [README.md](README.md) file in this project.
*   **Deployment**: If you want to run this system more permanently, look into the [DEPLOYMENT.md](DEPLOYMENT.md) guide for instructions on using Docker.

## 7. Simple Troubleshooting

Having trouble? Here are a few common tips:

*   **"I don't see my blog post!"**
    *   **Check API Keys**: Double-check that all your API keys in the `.env` file are correct, without typos or extra spaces.
    *   **System Running?**: Is the `python3 start_mcp_system.py` script still running in its terminal? Are there any error messages?
    *   **ngrok Running?**: If you're using ngrok, is it still running in its own terminal window? Is the Webhook URL in LINE Developers Console correct and using the https ngrok address?
    *   **System Logs**: The terminal where `start_mcp_system.py` is running will show log messages. Look for any errors around the time you sent your LINE message. These can give clues.
    *   **Hatena/Imgur Status**: Very rarely, the external services (Hatena, Imgur, Gemini) might have temporary issues.

*   **"Error when starting the system (`python3 start_mcp_system.py`)"**
    *   **Python Installed?**: Is Python 3 correctly installed and in your system's PATH?
    *   **Dependencies Installed?**: Did the `./setup_mcp.sh` script complete without errors? If not, some needed Python packages might be missing. You might see "ModuleNotFound" errors. Try running `pip install -r requirements.txt` (and `requirements-production.txt` if needed, though setup should handle it).
    *   **Port Conflict**: If it says "address already in use" or similar, another application might be using port 8084. You can change the `PORT` in your `.env` file to something else (e.g., 8085) and restart. Remember to update your ngrok command and LINE Webhook URL if you change the port.

*   **"LINE Webhook Verification Failed"**
    *   Ensure your system (`start_mcp_system.py`) is running.
    *   Ensure ngrok (if used) is running and correctly pointing to your local port.
    *   Make sure the URL in LINE Developers Console is exactly `https://your_ngrok_string.ngrok.io/webhook` (or your public IP equivalent).

We hope this guide helps you get started!
Feel free to explore the rest of the project's documentation for more advanced topics.
