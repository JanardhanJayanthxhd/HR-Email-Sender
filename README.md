# Telegram Job Application Email Bot

A Telegram bot that reads a job post, identifies a matching role and application email, and prepares an application email using one of two fixed templates. You review the draft before sending it with your resume attached.

## What it does

- Extracts the company, one relevant role, and an application email from a pasted job post.
- Lets you choose between a slightly detailed or straightforward email template.
- Lets you review, edit, send, or skip the email.
- Attaches a PDF resume and records sent or skipped applications in SQLite.
- Restricts bot access to the configured Telegram user ID.

The email templates are fixed in `src/mailer/email_templates.py`.

## Requirements

- Python 3.11 or newer
- [Ollama](https://ollama.com/) for the default local LLM provider
- A Telegram bot token
- A Gmail account with a Google App Password
- A PDF resume in the project's `resume/` directory

## Setup

### 1. Install Python dependencies

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) first, then from the project root create and activate a virtual environment.

**Windows PowerShell:**

```powershell
uv venv --python 3.12 .venv
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

If PowerShell prevents environment activation, either allow scripts for the current terminal according to your organization's policy, or run the virtualenv's Python directly:

```powershell
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

**macOS/Linux:**

```bash
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

`requirements.txt` installs the Python libraries used by the bot. The main dependencies provide Telegram bot handling, LangChain's model interface and Ollama adapter, `.env` configuration, asynchronous Gmail SMTP, SQLite storage, and validation/retry support. These are Python packages; Ollama and its model are installed separately in the next step.

### 2. Install and prepare Ollama

Ollama is a separate application and local model service; installing the Python dependencies does **not** install Ollama or download a model.

1. Install Ollama from [ollama.com/download](https://ollama.com/download) for your operating system.
2. Start Ollama. On Windows, the installed Ollama app normally runs the local service. If it is not running, open a separate terminal and run:

    ```powershell
    ollama serve
    ```

    Keep that terminal open if you started the service this way. If Ollama is already running as an app/service, do not start a second copy. The bot expects Ollama's API at `http://localhost:11434` by default.

3. Download the model configured by default in this project:

    ```powershell
    ollama pull qwen3:4b-instruct-2507-q4_K_M
    ```

    This downloads the model once; it may require several gigabytes of disk space. Initial model loading or inference can take longer on a CPU-only or memory-constrained computer.

4. Confirm the model is installed:

    ```powershell
    ollama list
    ```

    The output should include `qwen3:4b-instruct-2507-q4_K_M`.

5. Optionally test the model directly:

    ```powershell
    ollama run qwen3:4b-instruct-2507-q4_K_M
    ```

    Enter a short prompt, then type `/bye` to exit.

The bot sends the job post to this local Ollama service for extraction. Keep the service running while using the bot. To use a different model, pull it with `ollama pull <model-name>` and set `LLM_MODEL` in `.env` to that exact Ollama model name.

### 3. Create a Telegram bot and configure access

1. In Telegram, message [@BotFather](https://t.me/BotFather), create a bot with `/newbot`, and copy its token.
2. Find your numeric Telegram user ID (for example, using a Telegram user-ID lookup bot).
3. Copy `.env.example` to `.env`:

    ```powershell
    Copy-Item .env.example .env
    ```

    On macOS/Linux, use `cp .env.example .env`.

4. Set `TELEGRAM_BOT_TOKEN` and `ALLOWED_USER_ID` in `.env`. The bot only processes messages from this user ID.

### 4. Configure Gmail

1. Enable 2-Step Verification on the Google account that will send email.
2. Create an [App Password](https://myaccount.google.com/apppasswords). Use this password—not your normal Google password—for `GMAIL_APP_PASSWORD`.
3. Fill in these `.env` values:
    - `GMAIL_ADDRESS`: Gmail account used as the sender.
    - `GMAIL_APP_PASSWORD`: the generated App Password.
    - `REPLY_TO_EMAIL`: address recipients should reply to.
    - `SENDER_NAME`: name displayed in the From header and email signature.
    - `SENDER_PHONE`: optional phone number for the email signature. Leave blank to omit it.

Email is sent through Gmail SMTP using STARTTLS on port 587. The templates get the sender name and optional phone number from `.env`; no personal signature details are hardcoded. `REPLY_TO_EMAIL` is used as the message's Reply-To header.

### 5. Add your resume

Place at least one PDF resume in the project's `resume/` directory. If there are multiple PDFs, the bot lets you select one in Telegram.

## Configure the bot

The `.env` file uses these settings:

| Variable             | Purpose                                                        | Default                         |
| -------------------- | -------------------------------------------------------------- | ------------------------------- |
| `TELEGRAM_BOT_TOKEN` | Token from BotFather                                           | Required                        |
| `ALLOWED_USER_ID`    | Telegram user ID allowed to use the bot                        | Required                        |
| `LLM_PROVIDER`       | LLM provider (`ollama` by default)                             | `ollama`                        |
| `LLM_MODEL`          | Model name already pulled in Ollama                            | `qwen3:4b-instruct-2507-q4_K_M` |
| `LLM_TEMPERATURE`    | Model response temperature                                     | `0.0`                           |
| `OLLAMA_BASE_URL`    | Ollama API URL                                                 | `http://localhost:11434`        |
| `OLLAMA_NUM_CTX`     | Ollama context window                                          | `8192`                          |
| `GMAIL_ADDRESS`      | Gmail sender account                                           | Required                        |
| `GMAIL_APP_PASSWORD` | Google App Password                                            | Required                        |
| `REPLY_TO_EMAIL`     | Reply-To address                                               | Required                        |
| `SENDER_NAME`        | Name in the email From header and signature                    | Required                        |
| `SENDER_PHONE`       | Optional phone number included in the email signature          | Empty (omitted)                 |
| `DAILY_SEND_CAP`     | Maximum sends allowed in a 24-hour period                      | `15`                            |
| `SEND_DELAY_MIN`     | Minimum delay value shown in the post-send message, in seconds | `30`                            |
| `SEND_DELAY_MAX`     | Maximum delay value shown in the post-send message, in seconds | `60`                            |

The `SEND_DELAY_MIN` and `SEND_DELAY_MAX` values currently affect only the message shown after sending; the bot does not pause between sends. Keep `.env` private and do not commit it. The optional Google provider requires `langchain-google-genai` and a Google API key; Ollama is the default and needs no cloud API key.

## Run

Make sure Ollama is running and the configured model has been pulled, then from the project root run:

```powershell
python -m src.main
```

In Telegram:

1. Send `/start` and choose a resume if prompted.
2. Paste a job post that includes an application email address.
3. Review the selected role and choose template **1** or **2**.
4. Review the generated email, then choose **Send**, **Edit**, or **Skip**.

Use `/help` for the bot's command summary and `/resume` to change the selected resume.

## Troubleshooting

- **Ollama connection error:** make sure the Ollama app or `ollama serve` is running and `OLLAMA_BASE_URL` points to the right address.
- **Model not found:** run `ollama pull` with the exact value of `LLM_MODEL`.
- **Slow first extraction:** Ollama may need to load the model into memory. Check available system memory and whether Ollama is using CPU or GPU.
- **Gmail authentication failure:** confirm 2-Step Verification is enabled and `GMAIL_APP_PASSWORD` is an App Password for `GMAIL_ADDRESS`.
- **No resume found:** add a PDF file to `resume/`.
- **Database:** application history is stored at `data/applications.db`, created automatically.
