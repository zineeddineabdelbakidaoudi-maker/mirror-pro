"""Confirmation dialog for destructive actions."""
from PySide6.QtWidgets import QMessageBox, QWidget
from PySide6.QtCore import Qt


def confirm_action(parent: QWidget, title: str, message: str,
                   confirm_text: str = "Confirmer",
                   cancel_text: str = "Annuler") -> bool:
    """Show a confirmation dialog. Returns True if user confirms."""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Warning)
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setDefaultButton(QMessageBox.No)
    btn_yes = msg.button(QMessageBox.Yes)
    btn_yes.setText(confirm_text)
    btn_no = msg.button(QMessageBox.No)
    btn_no.setText(cancel_text)
    return msg.exec() == QMessageBox.Yes


def show_error(parent: QWidget, title: str, message: str):
    """Show an error message dialog."""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Critical)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.button(QMessageBox.Ok).setText("OK")
    msg.exec()


def show_info(parent: QWidget, title: str, message: str):
    """Show an info message dialog."""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Information)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.button(QMessageBox.Ok).setText("OK")
    msg.exec()


def show_success(parent: QWidget, title: str, message: str):
    """Show a success message."""
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Information)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.button(QMessageBox.Ok).setText("OK")
    msg.exec()
