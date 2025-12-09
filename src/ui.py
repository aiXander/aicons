"""
UI Module - Dark purple themed Tkinter UI components.

This module provides the visual components for the ElevenLabs Agent Controller
with a modern dark purple aesthetic.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from dataclasses import dataclass


# Modern dark theme with subtle purple hue
class Theme:
    """Dark purple theme color definitions - Modern React-inspired aesthetic."""
    # Primary backgrounds with purple undertone
    BG_PRIMARY = "#0d0d14"       # Deep dark purple-black
    BG_SECONDARY = "#13131f"     # Slightly lighter panel background
    BG_TERTIARY = "#1a1a2e"      # Accent/elevated surfaces
    BG_INPUT = "#0a0a12"         # Input fields - darkest
    BG_HOVER = "#1f1f35"         # Hover state background

    # Text colors - near white
    TEXT_PRIMARY = "#f0f0f5"     # Main text - slightly warm white
    TEXT_SECONDARY = "#a0a0b8"   # Secondary text with purple tint
    TEXT_MUTED = "#5a5a70"       # Muted text

    # Accent colors
    ACCENT_GREEN = "#22c55e"     # Success/Live - modern green
    ACCENT_BLUE = "#3b82f6"      # Info/Paused - vibrant blue
    ACCENT_ORANGE = "#f59e0b"    # Warning/Connecting
    ACCENT_RED = "#ef4444"       # Error/Stop
    ACCENT_PURPLE = "#8b5cf6"    # Primary accent - vibrant purple
    ACCENT_PURPLE_DIM = "#6d28d9"  # Darker purple for borders/subtle accents

    # UI elements
    BORDER = "#2a2a45"           # Border color with purple tint
    BORDER_FOCUS = "#8b5cf6"     # Focus border - matches accent purple
    BUTTON_BG = "#1e1e32"        # Button background
    BUTTON_HOVER = "#2a2a48"     # Button hover
    BUTTON_ACTIVE = "#353560"    # Button active/pressed

    # Shadows (for visual depth - used in styling)
    SHADOW = "#00000040"         # Subtle shadow


class TextHandler(logging.Handler):
    """Logging handler that outputs to a Tkinter Text widget."""

    def __init__(self, text_widget: tk.Text):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)

        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')

        # Schedule on main thread
        self.text_widget.after(0, append)


@dataclass
class UICallbacks:
    """Container for UI callback functions."""
    on_toggle_conversation: Callable[[], None]
    on_toggle_pause: Callable[[], None]
    on_close: Callable[[], None]


class AgentUI:
    """
    Modern dark purple themed UI for the ElevenLabs Agent Controller.

    Provides all visual components and handles user interactions,
    delegating business logic to callback functions.
    """

    def __init__(
        self,
        root: tk.Tk,
        window_title: str,
        config_info: Dict[str, str],
        callbacks: UICallbacks,
    ):
        """
        Initialize the UI.

        Args:
            root: Tkinter root window
            window_title: Title for the application window
            config_info: Dictionary of configuration info to display
            callbacks: Container with callback functions for user actions
        """
        self.root = root
        self.callbacks = callbacks
        self.config_info = config_info

        # Track debug panel visibility
        self.debug_visible = True

        # Track conversation state
        self.conversation_running = False

        # Configure window
        self.root.title(window_title)
        self._configure_window()

        # Configure theme
        self._configure_theme()

        # Build UI
        self._build_ui()

        # Setup window protocol
        self.root.protocol("WM_DELETE_WINDOW", self._handle_close)

        # Fix focus issues - ensure window captures events properly
        self._setup_focus_handling()

    def _configure_window(self) -> None:
        """Configure window size and behavior."""
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Set initial size
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")

        # Platform-specific maximization
        if sys.platform == 'win32':
            self.root.state('zoomed')
        elif sys.platform.startswith('linux'):
            try:
                self.root.attributes('-zoomed', True)
            except tk.TclError:
                pass
        elif sys.platform == 'darwin':
            # macOS - use large windowed mode instead of fullscreen
            self.root.attributes('-fullscreen', False)
            self.root.geometry(f"{screen_width}x{screen_height}+0+0")

        self.root.resizable(True, True)
        self.root.minsize(1024, 768)

    def _setup_focus_handling(self) -> None:
        """Setup proper focus handling to fix click registration issues."""
        # Force window to front and focus on startup
        self.root.lift()
        self.root.focus_force()

        # On macOS, additional handling to ensure clicks register
        if sys.platform == 'darwin':
            # Bind activation events to ensure focus
            self.root.bind('<Activate>', self._on_activate)
            self.root.bind('<FocusIn>', self._on_focus_in)

    def _on_activate(self, event=None) -> None:
        """Handle window activation."""
        self.root.focus_force()

    def _on_focus_in(self, event=None) -> None:
        """Handle focus in events."""
        pass  # Window already has focus

    def _create_styled_button(
        self,
        parent: tk.Frame,
        text: str,
        command: Callable,
        bg: str,
        hover_bg: str,
        fg: str = "#ffffff",
        font: tuple = ("SF Pro Display", 16, "bold"),
        pady: int = 20,
        padx: int = 20,
    ) -> tk.Frame:
        """
        Create a custom styled button using Frame+Label for consistent cross-platform appearance.

        On macOS, tk.Button ignores background color. This creates a Frame-based button
        that renders correctly on all platforms.
        """
        # Outer frame acts as the button
        btn_frame = tk.Frame(
            parent,
            bg=bg,
            cursor="hand2",
        )

        # Label inside for text
        btn_label = tk.Label(
            btn_frame,
            text=text,
            font=font,
            bg=bg,
            fg=fg,
            pady=pady,
            padx=padx,
        )
        btn_label.pack(fill=tk.BOTH, expand=True)

        # Store references for later updates
        btn_frame._label = btn_label
        btn_frame._bg = bg
        btn_frame._hover_bg = hover_bg
        btn_frame._fg = fg
        btn_frame._command = command

        # Bind click events to both frame and label
        def on_click(event=None):
            command()

        def on_enter(event=None):
            btn_frame.configure(bg=hover_bg)
            btn_label.configure(bg=hover_bg)

        def on_leave(event=None):
            current_bg = btn_frame._bg
            btn_frame.configure(bg=current_bg)
            btn_label.configure(bg=current_bg)

        def on_press(event=None):
            # Darken slightly on press
            btn_frame.configure(bg=hover_bg)
            btn_label.configure(bg=hover_bg)

        def on_release(event=None):
            btn_frame.configure(bg=btn_frame._bg)
            btn_label.configure(bg=btn_frame._bg)
            command()

        # Bind events to both frame and label
        for widget in (btn_frame, btn_label):
            widget.bind('<Enter>', on_enter)
            widget.bind('<Leave>', on_leave)
            widget.bind('<Button-1>', on_press)
            widget.bind('<ButtonRelease-1>', on_release)

        return btn_frame

    def _update_styled_button(
        self,
        btn_frame: tk.Frame,
        text: str = None,
        bg: str = None,
        hover_bg: str = None,
        fg: str = None,
    ) -> None:
        """Update a styled button's appearance."""
        if text is not None:
            btn_frame._label.configure(text=text)
        if bg is not None:
            btn_frame._bg = bg
            btn_frame.configure(bg=bg)
            btn_frame._label.configure(bg=bg)
        if hover_bg is not None:
            btn_frame._hover_bg = hover_bg
        if fg is not None:
            btn_frame._fg = fg
            btn_frame._label.configure(fg=fg)

    def _configure_theme(self) -> None:
        """Configure the dark purple theme for ttk widgets."""
        self.root.configure(bg=Theme.BG_PRIMARY)

        style = ttk.Style()
        style.theme_use('clam')

        # Configure frame styles
        style.configure(
            "Dark.TFrame",
            background=Theme.BG_PRIMARY,
        )
        style.configure(
            "Card.TFrame",
            background=Theme.BG_SECONDARY,
            relief="flat",
        )

        # Configure label styles
        style.configure(
            "Dark.TLabel",
            background=Theme.BG_PRIMARY,
            foreground=Theme.TEXT_PRIMARY,
            font=("SF Pro Display", 11),
        )
        style.configure(
            "Title.TLabel",
            background=Theme.BG_PRIMARY,
            foreground=Theme.TEXT_PRIMARY,
            font=("SF Pro Display", 24, "bold"),
        )
        style.configure(
            "Status.TLabel",
            background=Theme.BG_SECONDARY,
            foreground=Theme.TEXT_PRIMARY,
            font=("SF Pro Display", 32, "bold"),
        )
        style.configure(
            "Info.TLabel",
            background=Theme.BG_SECONDARY,
            foreground=Theme.TEXT_SECONDARY,
            font=("SF Mono", 10),
        )
        style.configure(
            "SectionTitle.TLabel",
            background=Theme.BG_PRIMARY,
            foreground=Theme.TEXT_PRIMARY,
            font=("SF Pro Display", 14, "bold"),
        )

        # Configure button styles
        style.configure(
            "Dark.TButton",
            background=Theme.BUTTON_BG,
            foreground=Theme.TEXT_PRIMARY,
            font=("SF Pro Display", 12, "bold"),
            padding=(20, 12),
            borderwidth=0,
        )
        style.map(
            "Dark.TButton",
            background=[("active", Theme.BUTTON_HOVER), ("disabled", Theme.BG_TERTIARY)],
            foreground=[("disabled", Theme.TEXT_MUTED)],
        )

    def _build_ui(self) -> None:
        """Build the user interface."""
        # Main container with dark background
        self.main_container = tk.Frame(self.root, bg=Theme.BG_PRIMARY)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

        # Header section
        self._build_header()

        # Content area (horizontal split: left controls, right logs)
        content_frame = tk.Frame(self.main_container, bg=Theme.BG_PRIMARY)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(24, 0))

        # Configure grid weights for responsive layout
        content_frame.grid_columnconfigure(0, weight=1, minsize=380)
        content_frame.grid_columnconfigure(1, weight=3, minsize=600)
        content_frame.grid_rowconfigure(0, weight=1)

        # Left panel - Controls
        self._build_control_panel(content_frame)

        # Right panel - Logs
        self._build_log_panel(content_frame)

    def _build_header(self) -> None:
        """Build the header section with title and status."""
        header_frame = tk.Frame(self.main_container, bg=Theme.BG_PRIMARY)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        # Title with subtle purple accent
        title_label = tk.Label(
            header_frame,
            text="AICONS Agent Controller",
            font=("SF Pro Display", 32, "bold"),
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_PRIMARY,
        )
        title_label.pack(side=tk.LEFT)

        # Status indicator (right side of header) - card style
        status_frame = tk.Frame(
            header_frame,
            bg=Theme.BG_SECONDARY,
            padx=24,
            pady=12,
            highlightbackground=Theme.BORDER,
            highlightthickness=1,
        )
        status_frame.pack(side=tk.RIGHT)

        # Status dot with glow effect (simulated with larger canvas)
        self.status_dot = tk.Canvas(
            status_frame,
            width=20,
            height=20,
            bg=Theme.BG_SECONDARY,
            highlightthickness=0
        )
        self.status_dot.pack(side=tk.LEFT, padx=(0, 12))
        # Draw outer glow
        self.status_dot.create_oval(2, 2, 18, 18, fill=Theme.TEXT_MUTED, outline="", tags="glow")
        # Draw inner dot
        self.status_dot.create_oval(5, 5, 15, 15, fill=Theme.TEXT_MUTED, outline="", tags="dot")

        self.status_label = tk.Label(
            status_frame,
            text="READY",
            font=("SF Pro Display", 20, "bold"),
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_MUTED,
        )
        self.status_label.pack(side=tk.LEFT)

    def _build_control_panel(self, parent: tk.Frame) -> None:
        """Build the left control panel."""
        # Outer frame with border effect
        control_outer = tk.Frame(
            parent,
            bg=Theme.BORDER,
            padx=1,
            pady=1,
        )
        control_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        control_frame = tk.Frame(control_outer, bg=Theme.BG_SECONDARY, padx=24, pady=24)
        control_frame.pack(fill=tk.BOTH, expand=True)

        # Section title
        tk.Label(
            control_frame,
            text="Controls",
            font=("SF Pro Display", 18, "bold"),
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
        ).pack(anchor=tk.W, pady=(0, 24))

        # Control buttons
        button_frame = tk.Frame(control_frame, bg=Theme.BG_SECONDARY)
        button_frame.pack(fill=tk.X, pady=(0, 24))

        # Main toggle button (Start/Stop) - Modern styled button
        self.toggle_btn = self._create_styled_button(
            button_frame,
            text="Start Conversation",
            command=self._handle_toggle_conversation,
            bg=Theme.ACCENT_GREEN,
            hover_bg="#16a34a",
            fg="#ffffff",
            font=("SF Pro Display", 16, "bold"),
            pady=20,
        )
        self.toggle_btn.pack(fill=tk.X, pady=(0, 12))

        # Pause button (only visible when running) - Modern styled button
        self.pause_btn = self._create_styled_button(
            button_frame,
            text="⏸",
            command=self._handle_toggle_pause,
            bg=Theme.ACCENT_BLUE,
            hover_bg="#2563eb",
            fg="#ffffff",
            font=("SF Pro Display", 20),
            pady=12,
        )
        # Initially hidden

        # Separator line with purple accent
        separator = tk.Frame(control_frame, bg=Theme.ACCENT_PURPLE_DIM, height=2)
        separator.pack(fill=tk.X, pady=24)

        # Info section title
        tk.Label(
            control_frame,
            text="Configuration",
            font=("SF Pro Display", 16, "bold"),
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
        ).pack(anchor=tk.W, pady=(0, 16))

        # Info card with border
        info_outer = tk.Frame(control_frame, bg=Theme.BORDER, padx=1, pady=1)
        info_outer.pack(fill=tk.X)

        info_frame = tk.Frame(info_outer, bg=Theme.BG_INPUT, padx=16, pady=16)
        info_frame.pack(fill=tk.X)

        # Display config info
        for label, value in self.config_info.items():
            self._create_info_row(info_frame, label, value)

        # Spacer
        tk.Frame(control_frame, bg=Theme.BG_SECONDARY).pack(fill=tk.BOTH, expand=True)

        # Show Debug Log button (only visible when debug panel is hidden)
        self.show_debug_btn = self._create_styled_button(
            control_frame,
            text="Show Debug Log",
            command=self._toggle_debug_panel,
            bg=Theme.BUTTON_BG,
            hover_bg=Theme.BUTTON_HOVER,
            fg=Theme.TEXT_SECONDARY,
            font=("SF Pro Display", 12),
            pady=10,
        )
        # Initially hidden

    def _create_info_row(self, parent: tk.Frame, label: str, value: str) -> None:
        """Create an info row with label and value."""
        row = tk.Frame(parent, bg=Theme.BG_INPUT)
        row.pack(fill=tk.X, pady=4)

        tk.Label(
            row,
            text=label,
            font=("SF Mono", 10),
            bg=Theme.BG_INPUT,
            fg=Theme.TEXT_MUTED,
            width=14,
            anchor=tk.W,
        ).pack(side=tk.LEFT)

        tk.Label(
            row,
            text=value,
            font=("SF Mono", 10),
            bg=Theme.BG_INPUT,
            fg=Theme.TEXT_PRIMARY,
            anchor=tk.W,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_log_panel(self, parent: tk.Frame) -> None:
        """Build the right log panel with conversation and debug logs."""
        self.log_frame = tk.Frame(parent, bg=Theme.BG_PRIMARY)
        self.log_frame.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        # Configure for vertical split
        self.log_frame.grid_rowconfigure(0, weight=2)
        self.log_frame.grid_rowconfigure(1, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)

        # Conversation log (top)
        self._build_conversation_log(self.log_frame)

        # Debug log (bottom)
        self._build_debug_log(self.log_frame)

    def _build_conversation_log(self, parent: tk.Frame) -> None:
        """Build the conversation log panel."""
        # Outer frame with border
        conv_outer = tk.Frame(parent, bg=Theme.BORDER, padx=1, pady=1)
        conv_outer.grid(row=0, column=0, sticky="nsew", pady=(0, 12))

        self.conv_frame = tk.Frame(conv_outer, bg=Theme.BG_SECONDARY)
        self.conv_frame.pack(fill=tk.BOTH, expand=True)
        conv_frame = self.conv_frame

        # Header
        header = tk.Frame(conv_frame, bg=Theme.BG_SECONDARY, pady=16, padx=20)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="Conversation",
            font=("SF Pro Display", 16, "bold"),
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
        ).pack(side=tk.LEFT)

        # Clear button - modern styled button
        clear_btn = self._create_styled_button(
            header,
            text="Clear",
            command=self._clear_conversation_log,
            bg=Theme.BUTTON_BG,
            hover_bg=Theme.BUTTON_HOVER,
            fg=Theme.TEXT_SECONDARY,
            font=("SF Pro Display", 11),
            pady=6,
            padx=16,
        )
        clear_btn.pack(side=tk.RIGHT)

        # Conversation text area with border
        text_outer = tk.Frame(conv_frame, bg=Theme.BORDER, padx=1, pady=1)
        text_outer.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        text_frame = tk.Frame(text_outer, bg=Theme.BG_INPUT)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.conversation_log = tk.Text(
            text_frame,
            font=("SF Mono", 12),
            bg=Theme.BG_INPUT,
            fg=Theme.TEXT_PRIMARY,
            relief="flat",
            wrap=tk.WORD,
            padx=16,
            pady=16,
            insertbackground=Theme.TEXT_PRIMARY,
            selectbackground=Theme.ACCENT_PURPLE,
            selectforeground=Theme.TEXT_PRIMARY,
            state='disabled',
            highlightthickness=0,
            borderwidth=0,
        )
        self.conversation_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Modern scrollbar
        conv_scrollbar = tk.Scrollbar(
            text_frame,
            command=self.conversation_log.yview,
            bg=Theme.BG_SECONDARY,
            troughcolor=Theme.BG_INPUT,
            activebackground=Theme.ACCENT_PURPLE,
            width=12,
            highlightthickness=0,
            borderwidth=0,
        )
        conv_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.conversation_log.config(yscrollcommand=conv_scrollbar.set)

        # Configure text tags for message styling
        self.conversation_log.tag_configure(
            "user",
            foreground=Theme.ACCENT_BLUE,
            font=("SF Mono", 12, "bold"),
        )
        self.conversation_log.tag_configure(
            "agent",
            foreground=Theme.ACCENT_PURPLE,
            font=("SF Mono", 12, "bold"),
        )
        self.conversation_log.tag_configure(
            "timestamp",
            foreground=Theme.TEXT_MUTED,
            font=("SF Mono", 10),
        )
        self.conversation_log.tag_configure(
            "message",
            foreground=Theme.TEXT_PRIMARY,
            font=("SF Mono", 12),
        )

    def _build_debug_log(self, parent: tk.Frame) -> None:
        """Build the debug log panel."""
        # Outer frame with border
        debug_outer = tk.Frame(parent, bg=Theme.BORDER, padx=1, pady=1)
        debug_outer.grid(row=1, column=0, sticky="nsew")
        self.debug_outer = debug_outer

        self.debug_frame = tk.Frame(debug_outer, bg=Theme.BG_SECONDARY)
        self.debug_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header = tk.Frame(self.debug_frame, bg=Theme.BG_SECONDARY, pady=16, padx=20)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="Debug Log",
            font=("SF Pro Display", 16, "bold"),
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
        ).pack(side=tk.LEFT)

        # Hide button
        self.debug_toggle_btn = self._create_styled_button(
            header,
            text="Hide",
            command=self._toggle_debug_panel,
            bg=Theme.BUTTON_BG,
            hover_bg=Theme.BUTTON_HOVER,
            fg=Theme.TEXT_SECONDARY,
            font=("SF Pro Display", 11),
            pady=6,
            padx=16,
        )
        self.debug_toggle_btn.pack(side=tk.RIGHT, padx=(8, 0))

        # Clear button
        clear_btn = self._create_styled_button(
            header,
            text="Clear",
            command=self._clear_debug_log,
            bg=Theme.BUTTON_BG,
            hover_bg=Theme.BUTTON_HOVER,
            fg=Theme.TEXT_SECONDARY,
            font=("SF Pro Display", 11),
            pady=6,
            padx=16,
        )
        clear_btn.pack(side=tk.RIGHT)

        # Debug text area with border
        text_outer = tk.Frame(self.debug_frame, bg=Theme.BORDER, padx=1, pady=1)
        text_outer.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        text_frame = tk.Frame(text_outer, bg=Theme.BG_INPUT)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.debug_log = tk.Text(
            text_frame,
            font=("SF Mono", 11),
            bg=Theme.BG_INPUT,
            fg=Theme.TEXT_SECONDARY,
            relief="flat",
            wrap=tk.WORD,
            padx=16,
            pady=16,
            insertbackground=Theme.TEXT_PRIMARY,
            selectbackground=Theme.ACCENT_PURPLE,
            selectforeground=Theme.TEXT_PRIMARY,
            state='disabled',
            highlightthickness=0,
            borderwidth=0,
        )
        self.debug_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar
        debug_scrollbar = tk.Scrollbar(
            text_frame,
            command=self.debug_log.yview,
            bg=Theme.BG_SECONDARY,
            troughcolor=Theme.BG_INPUT,
            activebackground=Theme.ACCENT_PURPLE,
            width=12,
            highlightthickness=0,
            borderwidth=0,
        )
        debug_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.debug_log.config(yscrollcommand=debug_scrollbar.set)

        # Configure text tags for log levels
        self.debug_log.tag_configure("DEBUG", foreground=Theme.TEXT_MUTED)
        self.debug_log.tag_configure("INFO", foreground=Theme.ACCENT_BLUE)
        self.debug_log.tag_configure("WARNING", foreground=Theme.ACCENT_ORANGE)
        self.debug_log.tag_configure("ERROR", foreground=Theme.ACCENT_RED)

    def _handle_toggle_conversation(self) -> None:
        """Handle toggle conversation button click with focus fix."""
        # Ensure window has focus before processing
        self.root.focus_force()
        self.callbacks.on_toggle_conversation()

    def _handle_toggle_pause(self) -> None:
        """Handle toggle pause button click with focus fix."""
        self.root.focus_force()
        self.callbacks.on_toggle_pause()

    def _handle_close(self) -> None:
        """Handle window close."""
        self.callbacks.on_close()

    def _toggle_debug_panel(self) -> None:
        """Toggle visibility of the debug panel."""
        if self.debug_visible:
            self.debug_outer.grid_remove()
            self.log_frame.grid_rowconfigure(1, weight=0)
            self.show_debug_btn.pack(fill=tk.X, pady=(24, 0))
            self.debug_visible = False
        else:
            self.debug_outer.grid()
            self.log_frame.grid_rowconfigure(1, weight=1)
            self.show_debug_btn.pack_forget()
            self.debug_visible = True

    def _clear_conversation_log(self) -> None:
        """Clear the conversation log."""
        self.conversation_log.configure(state='normal')
        self.conversation_log.delete(1.0, tk.END)
        self.conversation_log.configure(state='disabled')

    def _clear_debug_log(self) -> None:
        """Clear the debug log."""
        self.debug_log.configure(state='normal')
        self.debug_log.delete(1.0, tk.END)
        self.debug_log.configure(state='disabled')

    # Public methods for external control

    def add_conversation_message(self, role: str, message: str) -> None:
        """Add a message to the conversation log."""
        self.conversation_log.configure(state='normal')

        # Timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.conversation_log.insert(tk.END, f"[{timestamp}] ", "timestamp")

        # Role label
        if role == "user":
            self.conversation_log.insert(tk.END, "You: ", "user")
        else:
            self.conversation_log.insert(tk.END, "Agent: ", "agent")

        # Message content
        self.conversation_log.insert(tk.END, f"{message}\n\n", "message")

        # Scroll to bottom
        self.conversation_log.see(tk.END)
        self.conversation_log.configure(state='disabled')

    def update_status(self, text: str, state: str = "ready") -> None:
        """
        Update the status label and indicator.

        Args:
            text: Status text to display
            state: One of 'ready', 'connecting', 'live', 'paused', 'stopping', 'stopped', 'error'
        """
        color_map = {
            "ready": Theme.TEXT_MUTED,
            "connecting": Theme.ACCENT_ORANGE,
            "live": Theme.ACCENT_GREEN,
            "paused": Theme.ACCENT_BLUE,
            "stopping": Theme.ACCENT_ORANGE,
            "stopped": Theme.ACCENT_RED,
            "error": Theme.ACCENT_RED,
        }
        color = color_map.get(state, Theme.TEXT_MUTED)

        self.status_label.config(text=text, fg=color)

        # Update status dot with glow effect
        self.status_dot.delete("all")
        # Outer glow (slightly transparent)
        glow_color = color if state in ("live", "error") else Theme.BG_SECONDARY
        self.status_dot.create_oval(2, 2, 18, 18, fill=glow_color, outline="")
        # Inner dot
        self.status_dot.create_oval(5, 5, 15, 15, fill=color, outline="")

        self.root.update_idletasks()

    def set_conversation_running(self, running: bool) -> None:
        """Update UI state for conversation running/stopped."""
        self.conversation_running = running

        if running:
            self._update_styled_button(
                self.toggle_btn,
                text="Stop Conversation",
                bg=Theme.ACCENT_RED,
                hover_bg="#dc2626"
            )
            self.pause_btn.pack(fill=tk.X, pady=(0, 12))
        else:
            self._update_styled_button(
                self.toggle_btn,
                text="Start Conversation",
                bg=Theme.ACCENT_GREEN,
                hover_bg="#16a34a"
            )
            self.pause_btn.pack_forget()
            self._update_styled_button(self.pause_btn, text="⏸")

    def set_paused(self, paused: bool) -> None:
        """Update pause button state."""
        if paused:
            self._update_styled_button(self.pause_btn, text="▶")
        else:
            self._update_styled_button(self.pause_btn, text="⏸")

    def show_error(self, title: str, message: str) -> None:
        """Show an error dialog."""
        messagebox.showerror(title, message)

    def get_debug_log_widget(self) -> tk.Text:
        """Get the debug log text widget for logging handler."""
        return self.debug_log

    def destroy(self) -> None:
        """Destroy the root window."""
        self.root.destroy()
