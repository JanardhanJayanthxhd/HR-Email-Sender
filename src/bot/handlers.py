import random
import uuid
from pathlib import Path

from email_validator import EmailNotValidError, validate_email
from telegram import Update
from telegram.ext import ContextTypes

from src.bot.auth import authorized_only
from src.bot.keyboards import approval_keyboard, email_template_keyboard, resume_choice_keyboard
from src.config import Settings
from src.llm.extractor import extract_job_post
from src.llm.factory import get_llm
from src.logger import log
from src.mailer.email_templates import EMAIL_TEMPLATES, render_email_template
from src.mailer.gmail import send_email
from src.storage.db import get_daily_send_count, init_db, insert_application

settings = Settings()


def _list_resumes() -> list[Path]:
    try:
        return list(settings.resume_dir.glob("*.pdf"))
    except OSError:
        log.exception("Failed to scan the resume directory")
        raise


@authorized_only(settings)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    # Check for resumes
    resume_files = _list_resumes()

    if not resume_files:
        await update.message.reply_text(
            "⚠️ No resume found. Please add a PDF to the resume/ directory."
        )
        return

    if len(resume_files) == 1:
        context.user_data["selected_resume"] = resume_files[0]
        await update.message.reply_text(
            f"👋 Welcome! Using resume: {resume_files[0].name}\n\n"
            "Send me a LinkedIn job post to get started."
        )
    else:
        context.user_data["resume_files"] = resume_files
        await update.message.reply_text(
            "Found multiple resumes. Which one should I use?",
            reply_markup=resume_choice_keyboard(resume_files),
        )


@authorized_only(settings)
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = """
🤖 **Job Application Bot**

**How to use:**
1. Paste a LinkedIn job post
2. I'll select one role that best matches your Python/backend/AI experience
3. Choose an email template
4. Review, edit, send, or skip the email

**Commands:**
/start - Start the bot
/help - Show this help
/resume - Change resume selection

**Tips:**
- Make sure the job post includes an email address
- Check the draft before sending
- Edit if you want to customize the email
"""
    await update.message.reply_text(help_text)


@authorized_only(settings)
async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /resume command."""
    resume_files = _list_resumes()
    log.info("Scanned resume directory", resume_count=len(resume_files))

    if not resume_files:
        await update.message.reply_text("⚠️ No resume found.")
        return

    if len(resume_files) == 1:
        context.user_data["selected_resume"] = resume_files[0]
        await update.message.reply_text(f"Using: {resume_files[0].name}")
    else:
        context.user_data["resume_files"] = resume_files
        await update.message.reply_text(
            "Which resume?", reply_markup=resume_choice_keyboard(resume_files)
        )


@authorized_only(settings)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming job post text."""
    message = update.effective_message
    if message is None or message.text is None:
        log.warning("Ignored Telegram update without text")
        if message is not None:
            await message.reply_text("Please send the job post as text.")
        return

    job_text = message.text
    log.info("Received job post text", character_count=len(job_text))
    # Check if in edit mode
    if context.user_data.get("waiting_for_edit"):
        draft_id = context.user_data["waiting_for_edit"]
        draft_data = context.user_data[draft_id]
        draft_data["body"] = job_text
        context.user_data["waiting_for_edit"] = None

        await message.reply_text(
            f"📧 **Updated Draft**\n\n**Subject:** {draft_data['subject']}\n\n{draft_data['body']}",
            reply_markup=approval_keyboard(draft_id),
        )
        return

    # Check for multiple job posts
    if job_text.count("@") > 3 or len(job_text) > 3000:
        await message.reply_text(
            "⚠️ Found multiple job posts. Please send them one at a time."
        )
        return

    await message.reply_text("🔍 Extracting details...")

    try:
        job_post = await extract_job_post(job_text, get_llm(settings))
        log.info("Extracted job post details")

        if not job_post:
            await message.reply_text(
                "❌ No email address found in the job post. Please check and try again."
            )
            return

        try:
            validate_email(job_post.hr_email)
        except EmailNotValidError:
            log.warning("Extracted HR email failed format validation")
            await message.reply_text("❌ Invalid email address format in the job post.")
            return

        context.user_data["pending_application"] = {"job_post": job_post}
        await message.reply_text(
            f"Role selected based on your Python/backend/AI experience: {job_post.role}\n\n"
            f"Choose an email template (1-{len(EMAIL_TEMPLATES)}):",
            reply_markup=email_template_keyboard(),
        )

    except Exception:
        log.exception("Failed to process job post")
        await message.reply_text(
            "❌ Failed to process the job post.\n\n"
            "Please try rephrasing or check the job post format."
        )


@authorized_only(settings)
async def handle_template_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Render the user's selected email template for the pending application."""
    query = update.callback_query
    await query.answer()

    pending = context.user_data.get("pending_application")
    if not pending:
        await query.message.reply_text(
            "❌ This template selection expired. Send the job post again."
        )
        return

    try:
        template_number = int(query.data.removeprefix("template_"))
        job_post = pending["job_post"]
        draft = render_email_template(
            template_number,
            company=job_post.company,
            role=job_post.role,
        )
    except (ValueError, KeyError):
        log.warning("Invalid or incomplete email template selection")
        await query.message.reply_text(
            "❌ Invalid template selection. Please send the job post again."
        )
        return

    draft_id = str(uuid.uuid4())[:8]
    context.user_data[draft_id] = {
        "job_post": job_post,
        "subject": draft.subject,
        "body": draft.body,
    }
    del context.user_data["pending_application"]

    await query.message.reply_text(
        f"📋 **Job Details:**\n"
        f"Company: {job_post.company}\n"
        f"Role: {job_post.role}\n"
        f"HR: {job_post.hr_email}\n\n"
        f"📧 **Draft Email ({template_number}. "
        f"{EMAIL_TEMPLATES[template_number - 1].name}):**\n\n"
        f"**Subject:** {draft.subject}\n\n"
        f"{draft.body}",
        reply_markup=approval_keyboard(draft_id),
    )


@authorized_only(settings)
async def handle_send_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Send button callback."""
    await update.callback_query.answer()

    draft_id = update.callback_query.data.replace("send_", "")
    draft_data = context.user_data.get(draft_id)

    if not draft_data:
        await update.callback_query.message.reply_text("❌ Draft expired.")
        return

    # Check daily cap (Review Focus #3)
    try:
        await init_db(settings.database_path)
        sent_count = await get_daily_send_count(settings.database_path)
    except Exception:
        log.exception("Failed to check the daily email send limit")
        await update.callback_query.message.reply_text(
            "❌ Could not check the daily send limit. Please try again."
        )
        return

    if sent_count >= settings.daily_send_cap:
        await update.callback_query.message.reply_text(
            f"⚠️ Daily send limit reached ({sent_count}/{settings.daily_send_cap}). "
            "Try again tomorrow."
        )
        return

    # Get resume
    resume_path = context.user_data.get("selected_resume")
    if not resume_path or not resume_path.exists():
        await update.callback_query.message.reply_text("❌ Resume not found.")
        return

    await update.callback_query.message.reply_text("📤 Sending email...")

    # Send email
    job_post = draft_data["job_post"]
    success = await send_email(
        to=job_post.hr_email,
        subject=draft_data["subject"],
        body=draft_data["body"],
        attachment_path=resume_path,
        sender_email=settings.gmail_address,
        sender_password=settings.gmail_app_password,
        sender_name=settings.sender_name,
        reply_to=settings.reply_to_email,
    )

    if success:
        # Log to database
        try:
            await insert_application(
                db_path=settings.database_path,
                company=job_post.company,
                role=job_post.role,
                hr_email=job_post.hr_email,
                subject=draft_data["subject"],
                body=draft_data["body"],
                status="sent",
            )
        except Exception:
            log.exception("Email was sent, but its application record could not be saved")
            await update.callback_query.message.reply_text(
                "✅ Email sent, but the application record could not be saved."
            )
            del context.user_data[draft_id]
            return

        # Random delay for next send
        delay = random.randint(settings.send_delay_min, settings.send_delay_max)

        await update.callback_query.message.reply_text(
            f"✅ Email sent to {job_post.hr_email}!\n\n"
            f"Sent today: {sent_count + 1}/{settings.daily_send_cap}\n"
            f"(Waiting {delay}s before next send)"
        )

        # Clean up
        del context.user_data[draft_id]
    else:
        await update.callback_query.message.reply_text(
            "❌ Failed to send email. Check your Gmail credentials and network."
        )


@authorized_only(settings)
async def handle_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Edit button callback."""
    await update.callback_query.answer()

    draft_id = update.callback_query.data.replace("edit_", "")
    context.user_data["waiting_for_edit"] = draft_id

    await update.callback_query.message.reply_text("✏️ Send me the new email body:")


@authorized_only(settings)
async def handle_skip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Skip button callback."""
    await update.callback_query.answer()

    draft_id = update.callback_query.data.replace("skip_", "")
    draft_data = context.user_data.get(draft_id)

    if draft_data:
        # Log as skipped
        await init_db(settings.database_path)
        job_post = draft_data["job_post"]
        await insert_application(
            db_path=settings.database_path,
            company=job_post.company,
            role=job_post.role,
            hr_email=job_post.hr_email,
            subject=draft_data["subject"],
            body=draft_data["body"],
            status="skipped",
        )

        del context.user_data[draft_id]

    await update.callback_query.message.reply_text("⏭️ Skipped.")


@authorized_only(settings)
async def handle_email_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle email selection from multiple candidates."""
    await update.callback_query.answer()

    index = int(update.callback_query.data.replace("email_", ""))
    emails = context.user_data.get("candidate_emails", [])

    if index < len(emails):
        context.user_data["selected_email"] = emails[index]
        await update.callback_query.message.reply_text(f"✅ Selected: {emails[index]}")


@authorized_only(settings)
async def handle_resume_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle resume selection from multiple files."""
    await update.callback_query.answer()

    index = int(update.callback_query.data.replace("resume_", ""))
    resume_files = context.user_data.get("resume_files", [])

    if index < len(resume_files):
        context.user_data["selected_resume"] = resume_files[index]
        await update.callback_query.message.reply_text(
            f"✅ Selected: {resume_files[index].name}\n\nSend me a job post to get started."
        )
