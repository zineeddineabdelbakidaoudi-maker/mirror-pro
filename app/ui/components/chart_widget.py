"""Reusable Matplotlib chart widget for PySide6."""
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget, QVBoxLayout
from app.ui.theme import Theme

class ChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        
        self.ax = self.figure.add_subplot(111)
        self._apply_theme()

    def _apply_theme(self):
        theme = Theme.instance()
        bg_color = "#1A1B2E" if theme.is_dark else "#FFFFFF"
        text_color = "#F1F5F9" if theme.is_dark else "#1E293B"
        grid_color = "#2D2E4A" if theme.is_dark else "#E2E8F0"
        
        self.figure.patch.set_facecolor(bg_color)
        self.ax.set_facecolor(bg_color)
        
        self.ax.tick_params(colors=text_color)
        for spine in self.ax.spines.values():
            spine.set_color(grid_color)
            
        self.ax.yaxis.grid(True, linestyle='--', color=grid_color, alpha=0.7)
        self.ax.xaxis.grid(False)

    def plot_bar_chart(self, labels, values, title="", color="#6366F1"):
        self.ax.clear()
        self._apply_theme()
        
        self.ax.bar(labels, values, color=color, width=0.5, zorder=3)
        
        if title:
            theme = Theme.instance()
            text_color = "#F1F5F9" if theme.is_dark else "#1E293B"
            self.ax.set_title(title, color=text_color, pad=15)
            
        # Format y-axis to not use scientific notation
        self.ax.get_yaxis().set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ','))
        )
        
        self.figure.tight_layout()
        self.canvas.draw()
