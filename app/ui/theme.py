"""Theme manager with dark and light mode support."""


class ThemeColors:
    """Color tokens for the current theme."""
    def __init__(self, is_dark: bool = True):
        if is_dark:
            self.bg_primary = "#1a1b2e"
            self.bg_secondary = "#232440"
            self.bg_tertiary = "#2d2e4a"
            self.bg_input = "#2d2e4a"
            self.bg_hover = "#363758"
            self.bg_card = "#272845"
            self.border = "#3a3b5c"
            self.border_light = "#44456a"
            self.text_primary = "#f1f5f9"
            self.text_secondary = "#94a3b8"
            self.text_muted = "#64748b"
            self.accent = "#818cf8"
            self.accent_hover = "#6366f1"
            self.accent_bg = "#6366f120"
            self.success = "#34d399"
            self.success_bg = "#34d39920"
            self.warning = "#fbbf24"
            self.warning_bg = "#fbbf2420"
            self.danger = "#f87171"
            self.danger_bg = "#f8717120"
            self.info = "#60a5fa"
            self.info_bg = "#60a5fa20"
            self.sidebar_bg = "#16172b"
            self.sidebar_hover = "#232440"
            self.sidebar_active = "#6366f130"
            self.header_bg = "#1e1f38"
            self.scrollbar = "#3a3b5c"
            self.scrollbar_hover = "#44456a"
            self.shadow = "rgba(0,0,0,0.3)"
        else:
            self.bg_primary = "#f8f9fc"
            self.bg_secondary = "#ffffff"
            self.bg_tertiary = "#eef0f6"
            self.bg_input = "#ffffff"
            self.bg_hover = "#e8eaf2"
            self.bg_card = "#ffffff"
            self.border = "#d1d5db"
            self.border_light = "#e5e7eb"
            self.text_primary = "#1e293b"
            self.text_secondary = "#64748b"
            self.text_muted = "#94a3b8"
            self.accent = "#6366f1"
            self.accent_hover = "#4f46e5"
            self.accent_bg = "#6366f115"
            self.success = "#10b981"
            self.success_bg = "#10b98115"
            self.warning = "#f59e0b"
            self.warning_bg = "#f59e0b15"
            self.danger = "#ef4444"
            self.danger_bg = "#ef444415"
            self.info = "#3b82f6"
            self.info_bg = "#3b82f615"
            self.sidebar_bg = "#1e293b"
            self.sidebar_hover = "#334155"
            self.sidebar_active = "#6366f130"
            self.header_bg = "#ffffff"
            self.scrollbar = "#d1d5db"
            self.scrollbar_hover = "#94a3b8"
            self.shadow = "rgba(0,0,0,0.08)"


class Theme:
    _instance = None
    _is_dark = True
    _colors = None

    @classmethod
    def instance(cls) -> "Theme":
        if cls._instance is None:
            cls._instance = Theme()
        return cls._instance

    @property
    def is_dark(self) -> bool:
        return self._is_dark

    @property
    def colors(self) -> ThemeColors:
        if self._colors is None:
            self._colors = ThemeColors(self._is_dark)
        return self._colors

    def toggle(self):
        self._is_dark = not self._is_dark
        self._colors = ThemeColors(self._is_dark)

    def set_dark(self, dark: bool):
        self._is_dark = dark
        self._colors = ThemeColors(dark)
