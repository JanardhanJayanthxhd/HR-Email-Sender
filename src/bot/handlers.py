import random
import uuid
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes, filters
from email_validator import validate_email, EmailNotValidError

from src.config import Settings
from src.bot.auth import authorized_only
from src.bot.keyboards import approval_keyboard, email_choice_keyboard, resume_choice_keyboard
from src.llm.factory import get_llm
from src.llm.extractor import extract_job_post
from src.llm.drafter import draft_email
from src.mailer.gmail import send_email
from src.storage.db import init_db, insert_application, get_daily_send_count


settings = Settings()


@authorized_only(settings)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    # Check for resumes
    resume_dir = settings.resume_dir
    resume_files = list(resume_dir.glob("*.pdf"))

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
            reply_markup=resume_choice_keyboard(resume_files)
        )


@authorized_only(settings)
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = """
🤖 **Job Application Bot**

**How to use:**
1. Paste a LinkedIn job post
2. I'll extract company, role, and HR email
3. Review the draft email
4. Tap Send to send it

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
    resume_files = list(settings.resume_dir.glob("*.pdf"))

    if not resume_files:
        await update.message.reply_text("⚠️ No resume found.")
        return

    if len(resume_files) == 1:
        context.user_data["selected_resume"] = resume_files[0]
        await update.message.reply_text(f"Using: {resume_files[0].name}")
    else:
        context.user_data["resume_files"] = resume_files
        await update.message.reply_text(
            "Which resume?",
            reply_markup=resume_choice_keyboard(resume_files)
        )


@authorized_only(settings)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming job post text."""
    # Check if in edit mode
    if context.user_data.get("waiting_for_edit"):
        draft_id = context.user_data["waiting_for_edit"]
        draft_data = context.user_data[draft_id]
        draft_data["body"] = update.message.text
        context.user_data["waiting_for_edit"] = None

        await update.message.reply_text(
            f"📧 **Updated Draft**\n\n"
            f"**Subject:** {draft_data['subject']}\n\n"
            f"{draft_data['body']}",
            reply_markup=approval_keyboard(draft_id)
        )
        return

    job_text = update.message.text

    # Check for multiple job posts
    if job_text.count("@") > 3 or len(job_text) > 3000:
        await update.message.reply_text(
            "⚠️ Found multiple job posts. Please send them one at a time."
        )
        return

    await update.message.reply_text("🔍 Extracting details...")

    try:
        # Get LLM
        llm = get_llm(settings)

        # Extract job post
        job_post = await extract_job_post(job_text, llm)

        if not job_post:
            await update.message.reply_text(
                "❌ No email address found in the job post. Please check and try again."
            )
            return

        # Validate email format (Review Focus #5)
        try:
            validate_email(job_post.hr_email)
        except EmailNotValidError:
            await update.message.reply_text(
                f"❌ Invalid email address format: {job_post.hr_email}"
            )
            return

        # Load profile
        profile_path = settings.profile_path
        if profile_path.exists():
            profile_content = profile_path.read_text()
        else:
            profile_content = "Python developer with 1 year experience."

        # Draft email
        draft = await draft_email(job_post, profile_content, settings.sender_name, llm)

        # Store draft
        draft_id = str(uuid.uuid4())[:8]
        context.user_data[draft_id] = {
            "job_post": job_post,
            "subject": draft.subject,
            "body": draft.body,
        }

        # Show draft
        await update.message.reply_text(
            f"📋 **Job Details:**\n"
            f"Company: {job_post.company}\n"
            f"Role: {job_post.role}\n"
            f"HR: {job_post.hr_email}\n\n"
            f"📧 **Draft Email:**\n\n"
            f"**Subject:** {draft.subject}\n\n"
            f"{draft.body}",
            reply_markup=approval_keyboard(draft_id)
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Failed to extract job details: {str(e)}\n\n"
            "Please try rephrasing or check the job post format."
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
    await init_db(settings.database_path)
    sent_count = await get_daily_send_count(settings.database_path)

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
        reply_to=settings.reply_to_email
    )

    if success:
        # Log to database
        await insert_application(
            db_path=settings.database_path,
            company=job_post.company,
            role=job_post.role,
            hr_email=job_post.hr_email,
            subject=draft_data["subject"],
            body=draft_data["body"],
            status="sent"
        )

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

    await update.callback_query.message.reply_text(
        "✏️ Send me the new email body:"
    )


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
            status="skipped"
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
            f"✅ Selected: {resume_files[index].name}\n\n"
            "Send me a job post to get started."
        )