"""Main application with Tkinter UI for automated email sending."""

import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from dotenv import load_dotenv

from email_sender import EmailSender
from email_templates import get_template


class EmailSenderApp:
    """Main application class for email sender UI."""

    def __init__(self, root):
        """Initialize the application.

        Args:
            root: Tkinter root window.
        """
        self.root = root
        self.root.title("Auto Email Sender")
        self.root.geometry("600x500")
        self.root.configure(bg="#1e1e1e")

        load_dotenv()

        self.sender_email = os.getenv("SENDER_EMAIL", "")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")
        self.sender_name = os.getenv("SENDER_NAME", "")

        self.resume_path = None

        self._setup_styles()
        self._create_widgets()

    def _setup_styles(self):
        """Configure UI styles for dark minimal theme."""
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Dark.TFrame", background="#1e1e1e")
        style.configure(
            "Dark.TLabel",
            background="#1e1e1e",
            foreground="#ffffff",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Header.TLabel",
            background="#1e1e1e",
            foreground="#ffffff",
            font=("Segoe UI", 16, "bold"),
        )
        style.configure(
            "Dark.TButton",
            background="#2d2d2d",
            foreground="#ffffff",
            borderwidth=0,
            focuscolor="none",
            font=("Segoe UI", 10),
        )
        style.map("Dark.TButton", background=[("active", "#3d3d3d")])

    def _create_widgets(self):
        """Create and layout all UI widgets."""
        main_frame = ttk.Frame(self.root, style="Dark.TFrame", padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Header
        header = ttk.Label(main_frame, text="Auto Email Sender", style="Header.TLabel")
        header.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # HR Email
        ttk.Label(main_frame, text="HR Email:", style="Dark.TLabel").grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        self.hr_email_var = tk.StringVar()
        hr_email_entry = tk.Entry(
            main_frame,
            textvariable=self.hr_email_var,
            bg="#2d2d2d",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 10),
        )
        hr_email_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, ipady=5)

        # Company Name
        ttk.Label(main_frame, text="Company:", style="Dark.TLabel").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        self.company_var = tk.StringVar()
        company_entry = tk.Entry(
            main_frame,
            textvariable=self.company_var,
            bg="#2d2d2d",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 10),
        )
        company_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, ipady=5)

        # Position
        ttk.Label(main_frame, text="Position:", style="Dark.TLabel").grid(
            row=3, column=0, sticky=tk.W, pady=5
        )
        self.position_var = tk.StringVar()
        position_entry = tk.Entry(
            main_frame,
            textvariable=self.position_var,
            bg="#2d2d2d",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 10),
        )
        position_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, ipady=5)

        # Template Selection
        ttk.Label(main_frame, text="Template:", style="Dark.TLabel").grid(
            row=4, column=0, sticky=tk.W, pady=5
        )
        self.template_var = tk.StringVar(value="template1")
        template_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        template_frame.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5)

        templates = [
            ("Template 1", "template1"),
            ("Template 2", "template2"),
            ("Template 3", "template3"),
        ]
        for text, value in templates:
            rb = tk.Radiobutton(
                template_frame,
                text=text,
                variable=self.template_var,
                value=value,
                bg="#1e1e1e",
                fg="#ffffff",
                selectcolor="#2d2d2d",
                activebackground="#1e1e1e",
                activeforeground="#ffffff",
                font=("Segoe UI", 9),
            )
            rb.pack(side=tk.LEFT, padx=5)

        # Resume Selection
        ttk.Label(main_frame, text="Resume:", style="Dark.TLabel").grid(
            row=5, column=0, sticky=tk.W, pady=5
        )
        resume_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        resume_frame.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=5)

        self.resume_label = tk.Label(
            resume_frame,
            text="No resume selected",
            bg="#1e1e1e",
            fg="#888888",
            font=("Segoe UI", 9),
        )
        self.resume_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        browse_btn = tk.Button(
            resume_frame,
            text="Browse",
            command=self._browse_resume,
            bg="#2d2d2d",
            fg="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=5,
            font=("Segoe UI", 9),
        )
        browse_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Preview Button
        preview_btn = tk.Button(
            main_frame,
            text="Preview Email",
            command=self._preview_email,
            bg="#2d2d2d",
            fg="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 10),
            cursor="hand2",
        )
        preview_btn.grid(
            row=6, column=0, columnspan=2, pady=20, sticky=(tk.W, tk.E), ipady=8
        )

        # Send Button
        send_btn = tk.Button(
            main_frame,
            text="Send Email",
            command=self._send_email,
            bg="#0d7377",
            fg="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
        )
        send_btn.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), ipady=10)

        # Status Label
        self.status_label = tk.Label(
            main_frame, text="", bg="#1e1e1e", fg="#888888", font=("Segoe UI", 9)
        )
        self.status_label.grid(row=8, column=0, columnspan=2, pady=(10, 0))

    def _browse_resume(self):
        """Open file dialog to select resume PDF."""
        filename = filedialog.askopenfilename(
            title="Select Resume",
            initialdir="./resume",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if filename:
            self.resume_path = filename
            self.resume_label.config(text=Path(filename).name, fg="#00ff00")

    def _validate_inputs(self) -> bool:
        """Validate all required input fields.

        Returns:
            True if all inputs are valid, False otherwise.
        """
        if not self.sender_email or not self.sender_password:
            messagebox.showerror("Error", "Email credentials not found in .env file")
            return False

        if not self.hr_email_var.get().strip():
            messagebox.showerror("Error", "Please enter HR email")
            return False

        if not self.company_var.get().strip():
            messagebox.showerror("Error", "Please enter company name")
            return False

        if not self.position_var.get().strip():
            messagebox.showerror("Error", "Please enter position")
            return False

        return True

    def _preview_email(self):
        """Show preview of email content in a popup window."""
        if not self._validate_inputs():
            return

        body = get_template(
            self.template_var.get(),
            self.sender_name,
            self.position_var.get(),
            self.company_var.get(),
        )

        subject = f"Application {self.sender_name} - {self.position_var.get()}"

        preview_window = tk.Toplevel(self.root)
        preview_window.title("Email Preview")
        preview_window.geometry("500x600")
        preview_window.configure(bg="#1e1e1e")

        frame = ttk.Frame(preview_window, style="Dark.TFrame", padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Subject:", style="Dark.TLabel").pack(anchor=tk.W)
        subject_text = tk.Text(
            frame,
            height=2,
            bg="#2d2d2d",
            fg="#ffffff",
            relief=tk.FLAT,
            font=("Segoe UI", 10),
        )
        subject_text.pack(fill=tk.X, pady=(0, 10))
        subject_text.insert("1.0", subject)
        subject_text.config(state=tk.DISABLED)

        ttk.Label(frame, text="Body:", style="Dark.TLabel").pack(anchor=tk.W)
        body_text = tk.Text(
            frame, bg="#2d2d2d", fg="#ffffff", relief=tk.FLAT, font=("Segoe UI", 10)
        )
        body_text.pack(fill=tk.BOTH, expand=True)
        body_text.insert("1.0", body)
        body_text.config(state=tk.DISABLED)

    def _send_email(self):
        """Send email with current form data."""
        if not self._validate_inputs():
            return

        self.status_label.config(text="Sending email...", fg="#ffaa00")
        self.root.update()

        try:
            sender = EmailSender(self.sender_email, self.sender_password, self.sender_name)

            subject = f"Application {self.sender_name} - {self.position_var.get()}"

            body = get_template(
                self.template_var.get(),
                self.sender_name,
                self.position_var.get(),
                self.company_var.get(),
            )

            success = sender.send_email(
                self.hr_email_var.get(), subject, body, self.resume_path
            )

            if success:
                self.status_label.config(text="Email sent successfully!", fg="#00ff00")
                messagebox.showinfo(
                    "Success", f"Email sent to {self.hr_email_var.get()}"
                )
            else:
                self.status_label.config(text="Failed to send email", fg="#ff0000")
                messagebox.showerror(
                    "Error", "Failed to send email. Check credentials and try again."
                )

        except Exception:
            error_msg = "Failed to send email. Check credentials and network."
            self.status_label.config(text=error_msg, fg="#ff0000")
            messagebox.showerror("Error", error_msg)


def main():
    """Entry point for the application."""
    root = tk.Tk()
    EmailSenderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
