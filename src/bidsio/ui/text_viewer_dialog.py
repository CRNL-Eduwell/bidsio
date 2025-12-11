"""
Text viewer dialog.

This module provides a dialog for displaying text and markdown files.
"""

from pathlib import Path

from PySide6.QtWidgets import QDialog, QVBoxLayout, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette

from bidsio.infrastructure.logging_config import get_logger
from bidsio.config.settings import get_settings

# Try to import QtWebEngineWidgets for better HTML rendering
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineProfile
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False
    from PySide6.QtWidgets import QTextBrowser

# Try to import markdown library
try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False


logger = get_logger(__name__)


class TextViewerDialog(QDialog):
    """
    Dialog for viewing text and markdown files.
    
    Uses QtWebEngine if available for perfect rendering, falls back to QTextBrowser.
    """
    
    def __init__(self, file_path: Path, parent=None):
        """
        Initialize the text viewer dialog.
        
        Args:
            file_path: Path to the text/markdown file to display.
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self._file_path = file_path
        
        self._setup_ui()
        self._load_text()
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create web view or text browser
        if HAS_WEBENGINE:
            self._viewer = QWebEngineView(self)
            self._is_webengine = True
            logger.debug("Using QWebEngineView for text display")
        else:
            self._viewer = QTextBrowser(self)
            self._viewer.setOpenExternalLinks(True)
            self._is_webengine = False
            logger.debug("Using QTextBrowser for text display (WebEngine not available)")
        
        layout.addWidget(self._viewer)
        
        # Set window properties
        self.setWindowTitle(f"File: {self._file_path.name}")
        self.resize(900, 700)
        
        # Ensure dialog is deleted when closed (not just hidden)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    
    def closeEvent(self, event):
        """Handle dialog close event to ensure proper cleanup."""
        # Clean up web engine view if present
        if self._is_webengine and hasattr(self, '_viewer'):
            try:
                # Import here to avoid type checking issues
                from PySide6.QtWebEngineWidgets import QWebEngineView
                if isinstance(self._viewer, QWebEngineView):
                    # Clear content first
                    self._viewer.setHtml("")
                    # Stop any loading
                    self._viewer.stop()
                    # Get and delete the page
                    page = self._viewer.page()
                    if page:
                        page.deleteLater()
            except Exception as e:
                logger.warning(f"Error during web view cleanup: {e}")
        
        # Accept the close event
        event.accept()
        super().closeEvent(event)
    
    def _load_text(self):
        """Load and display the text file."""
        try:
            # Read file content
            content = None
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(self._file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                with open(self._file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            
            # Check if markdown
            is_markdown = (
                self._file_path.suffix.lower() in ['.md', '.markdown'] or
                self._file_path.name.upper() in ['README', 'CHANGES']
            )
            
            if is_markdown and HAS_MARKDOWN:
                # Convert to HTML with proper styling
                html_content = self._render_markdown(content)
                # Both viewers support setHtml
                self._viewer.setHtml(html_content)
            else:
                # Display as plain text
                if self._is_webengine:
                    # Wrap plain text in <pre> tags for WebEngine
                    plain_html = f"<html><body style='padding:20px;'><pre style='font-family:monospace;white-space:pre-wrap;'>{content}</pre></body></html>"
                    self._viewer.setHtml(plain_html)
                else:
                    from PySide6.QtWidgets import QTextBrowser
                    if isinstance(self._viewer, QTextBrowser):
                        self._viewer.setPlainText(content)
            
            logger.debug(f"Loaded text file: {self._file_path}")
            
        except Exception as e:
            logger.error(f"Failed to load text file: {e}", exc_info=True)
            error_msg = f"Error loading file:\n{str(e)}"
            error_html = f"<html><body style='padding:20px;'><pre style='color:red;'>{error_msg}</pre></body></html>"
            if self._is_webengine:
                self._viewer.setHtml(error_html)
            else:
                from PySide6.QtWidgets import QTextBrowser
                if isinstance(self._viewer, QTextBrowser):
                    self._viewer.setPlainText(error_msg)
    
    def _is_dark_theme(self) -> bool:
        """Detect if the application is using a dark theme."""
        try:
            settings = get_settings()
            # Theme names starting with "dark" are dark themes
            return settings.theme.startswith('dark')
        except Exception as e:
            logger.debug(f"Failed to detect theme from settings: {e}")
            # Fallback to palette detection
            try:
                app = QApplication.instance()
                if app and isinstance(app, QApplication):
                    palette = app.palette()
                    bg_color = palette.color(QPalette.ColorRole.Window)
                    bg_luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()) / 255
                    return bg_luminance < 0.5
            except Exception:
                pass
        return False
    
    def _render_markdown(self, content: str) -> str:
        """
        Render markdown to styled HTML.
        
        Args:
            content: Markdown content.
            
        Returns:
            Styled HTML string.
        """
        # Convert markdown to HTML
        html_body = markdown.markdown(
            content,
            extensions=['extra', 'tables', 'fenced_code', 'nl2br', 'sane_lists']
        )
        
        # Detect theme and choose appropriate colors
        is_dark = self._is_dark_theme()
        
        if is_dark:
            # Dark theme colors (GitHub dark)
            colors = {
                'bg': '#0d1117',
                'text': '#c9d1d9',
                'border': '#30363d',
                'code_bg': '#161b22',
                'code_inline_bg': 'rgba(110,118,129,0.4)',
                'link': '#58a6ff',
                'quote': '#8b949e',
                'table_row_alt': '#161b22',
            }
        else:
            # Light theme colors (GitHub light)
            colors = {
                'bg': '#ffffff',
                'text': '#24292e',
                'border': '#eaecef',
                'code_bg': '#f6f8fa',
                'code_inline_bg': 'rgba(27,31,35,0.05)',
                'link': '#0366d6',
                'quote': '#6a737d',
                'table_row_alt': '#f6f8fa',
            }
        
        # GitHub-style CSS with theme support
        css = f"""
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                font-size: 14px;
                line-height: 1.6;
                color: {colors['text']};
                background-color: {colors['bg']};
                padding: 30px;
                max-width: 980px;
                margin: 0 auto;
            }}
            h1, h2 {{ border-bottom: 1px solid {colors['border']}; padding-bottom: 0.3em; }}
            h1 {{ font-size: 2em; margin-top: 24px; margin-bottom: 16px; font-weight: 600; }}
            h2 {{ font-size: 1.5em; margin-top: 24px; margin-bottom: 16px; font-weight: 600; }}
            h3 {{ font-size: 1.25em; margin-top: 24px; margin-bottom: 16px; font-weight: 600; }}
            h4 {{ font-size: 1em; margin-top: 16px; margin-bottom: 8px; font-weight: 600; }}
            p {{ margin-top: 0; margin-bottom: 16px; }}
            ul, ol {{ padding-left: 2em; margin-top: 0; margin-bottom: 16px; }}
            li {{ margin-top: 0.25em; word-wrap: break-all; }}
            li > p {{ margin-bottom: 0; }}
            code {{ padding: 0.2em 0.4em; margin: 0; font-size: 85%; background-color: {colors['code_inline_bg']}; border-radius: 3px; }}
            pre {{ padding: 16px; overflow: auto; font-size: 85%; line-height: 1.45; background-color: {colors['code_bg']}; border-radius: 6px; }}
            pre code {{ background: transparent; padding: 0; }}
            blockquote {{ padding: 0 1em; color: {colors['quote']}; border-left: 0.25em solid {colors['border']}; margin: 0 0 16px 0; }}
            table {{ border-spacing: 0; border-collapse: collapse; width: 100%; margin-bottom: 16px; }}
            table th {{ font-weight: 600; padding: 6px 13px; border: 1px solid {colors['border']}; }}
            table td {{ padding: 6px 13px; border: 1px solid {colors['border']}; }}
            table tr {{ background-color: {colors['bg']}; border-top: 1px solid {colors['border']}; }}
            table tr:nth-child(2n) {{ background-color: {colors['table_row_alt']}; }}
            hr {{ height: 0.25em; margin: 24px 0; background-color: {colors['border']}; border: 0; }}
            strong {{ font-weight: 600; }}
            a {{ color: {colors['link']}; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
        """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            {css}
        </head>
        <body>
            {html_body}
        </body>
        </html>
        """
