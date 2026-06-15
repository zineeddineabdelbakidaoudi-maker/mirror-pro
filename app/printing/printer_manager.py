"""Printer Manager for ESC/POS hardware printing with PDF fallback."""
import logging
import os
from typing import Dict, Any, Optional

try:
    from escpos.printer import Win32Raw
    from escpos.exceptions import Error as EscposError
    ESCPOS_AVAILABLE = True
except ImportError:
    ESCPOS_AVAILABLE = False
    logging.warning("python-escpos not installed. Hardware printing disabled.")

import win32print
import win32api
import time

from app.services.settings_service import SettingsService
from app.printing.pdf_fallback import generate_internal_ticket_pdf, generate_customer_receipt_pdf

logger = logging.getLogger(__name__)

class PrinterManager:
    """Manages connection to ESC/POS thermal printers."""
    
    def __init__(self, session):
        self.session = session
        self.settings_svc = SettingsService(session)
        self.printer = None
        
    def _connect(self) -> bool:
        """Attempt to connect to the configured ESC/POS printer using Win32Raw."""
        if not ESCPOS_AVAILABLE:
            return False
            
        p_type = self.settings_svc.get("printer_type", "thermique")
        if p_type != "thermique":
            return False
            
        printer_name = self.settings_svc.get("printer_name", "")
        if not printer_name:
            try:
                printer_name = win32print.GetDefaultPrinter()
            except Exception:
                pass
                
        if not printer_name:
            logger.error("No Windows printer available for Win32Raw.")
            return False
            
        try:
            self.printer = Win32Raw(printer_name)
            return True
        except Exception as e:
            logger.error(f"Printer connection failed: {e}")
            self.printer = None
            return False

    def print_internal_ticket(self, order_data: Dict[str, Any], company_data: Dict[str, str]) -> str:
        """
        Print the internal ticket to ESC/POS if configured, otherwise generate PDF and route it.
        Returns empty string if handled silently, or PDF path if user needs to handle it.
        """
        if self._connect():
            try:
                self._escpos_print_internal(order_data, company_data)
                return ""
            except Exception as e:
                logger.error(f"Hardware printing failed, falling back to PDF: {e}")
            finally:
                if self.printer:
                    try:
                        self.printer.close()
                    except: pass
                
        # Standard A4 / Fallback
        pdf_path = generate_internal_ticket_pdf(order_data, company_data)
        return self._route_pdf(pdf_path)
        
    def print_customer_receipt(self, order_data: Dict[str, Any], company_data: Dict[str, str]) -> str:
        """
        Print the customer receipt to ESC/POS if configured, otherwise generate PDF and route it.
        Returns empty string if handled silently, or PDF path if user needs to handle it.
        """
        if self._connect():
            try:
                self._escpos_print_customer(order_data, company_data)
                return ""
            except Exception as e:
                logger.error(f"Hardware printing failed, falling back to PDF: {e}")
            finally:
                if self.printer:
                    try:
                        self.printer.close()
                    except: pass
                
        # Standard A4 / Fallback
        pdf_path = generate_customer_receipt_pdf(order_data, company_data)
        return self._route_pdf(pdf_path)

    def _route_pdf(self, pdf_path: str) -> str:
        """Send PDF to the selected standard printer natively via win32api."""
        p_type = self.settings_svc.get("printer_type", "thermique")
        if p_type == "standard":
            printer_name = self.settings_svc.get("printer_name", "")
            if not printer_name:
                try:
                    printer_name = win32print.GetDefaultPrinter()
                except Exception:
                    pass
            
            if printer_name:
                try:
                    # Method 1: Use printto
                    result = win32api.ShellExecute(0, "printto", pdf_path, f'"{printer_name}"', ".", 0)
                    if result > 32:
                        return ""  # Success silently
                except Exception as e:
                    logger.warning(f"ShellExecute printto failed: {e}")
                
                # Fallback to default print if printto fails
                try:
                    old_default = win32print.GetDefaultPrinter()
                    win32print.SetDefaultPrinter(printer_name)
                    win32api.ShellExecute(0, "print", pdf_path, None, ".", 0)
                    time.sleep(2)  # Give spooler time before restoring default
                    win32print.SetDefaultPrinter(old_default)
                    return ""
                except Exception as e:
                    logger.error(f"Failed to route PDF to printer: {e}")
        
        return pdf_path

    def _escpos_print_internal(self, order_data: Dict[str, Any], company_data: Dict[str, str]):
        """Format and print internal ticket using ESC/POS."""
        if not self.printer:
            raise RuntimeError("Printer not connected")
            
        p = self.printer
        
        # Init
        p.set(align='center', font='a', width=2, height=2)
        p.text("TICKET INTERNE\n")
        p.set(align='center', font='a', width=1, height=1)
        p.text("--------------------------------\n")
        
        p.set(align='left')
        p.text(f"Ref: {order_data.get('reference')}\n")
        p.text(f"Client: {order_data.get('customer')}\n")
        p.text(f"Date: {order_data.get('date', '')}\n")
        p.text("--------------------------------\n\n")
        
        # Items
        p.set(align='left', font='a', width=1, height=1, bold=True)
        p.text("ARTICLES & MATIERES\n")
        p.set(bold=False)
        
        for item in order_data.get('items', []):
            qty = item.get('quantity', 1)
            name = item.get('product_name', '')
            dim = item.get('dimensions') or ''
            price = item.get('selling_price') or 0
            
            dim_str = f" [{dim}]" if dim else ""
            p.text(f"\n[ ] {name} (x{qty}){dim_str}\n")
            if price > 0:
                p.text(f"    Prix: {price:,.0f} DA\n")
                
            for mat in item.get('materials', []):
                p.text(f"    - {mat.get('material_name')}: {mat.get('quantity')} {mat.get('unit')}\n")
                
        p.text("\n--------------------------------\n")
        
        # Totals
        p.set(align='right', bold=True)
        total = order_data.get('final_selling_price') or order_data.get('estimated_cost', 0)
        p.text(f"TOTAL: {total:,.0f} DA\n")
        
        paid = order_data.get('total_payments', 0)
        rem = order_data.get('remaining_balance', 0)
        
        p.set(align='right', bold=False)
        p.text(f"Versment: {paid:,.0f} DA\n")
        p.text(f"Reste: {rem:,.0f} DA\n")
            
        p.set(align='left')
        notes = order_data.get('notes')
        if notes:
            p.text(f"\nNOTES:\n{notes}\n")
        
        p.text("--------------------------------\n")
        p.text("   [ ] DECOUPE\n")
        p.text("   [ ] ASSEMBLAGE\n")
        p.text("   [ ] FINITION\n")
        p.text("   [ ] CONTROLE\n")
        p.text("--------------------------------\n\n")
        p.cut()

    def _escpos_print_customer(self, order_data: Dict[str, Any], company_data: Dict[str, str]):
        """Format and print customer receipt using ESC/POS."""
        if not self.printer:
            raise RuntimeError("Printer not connected")
            
        p = self.printer
        
        # Header
        p.set(align='center', font='a', width=2, height=2)
        p.text(f"{company_data.get('name', 'MIROIR PRO')}\n")
        p.set(align='center', font='a', width=1, height=1)
        p.text(f"{company_data.get('address', '')}\n")
        p.text(f"Tel: {company_data.get('phone', '')}\n")
        p.text("--------------------------------\n")
        
        # Order Info
        p.set(align='left')
        p.text(f"Date: {order_data.get('date', '')}\n")
        p.text(f"Ticket: {order_data.get('reference')}\n")
        p.text(f"Client: {order_data.get('customer')}\n")
        p.text("--------------------------------\n")
        
        # Items
        for item in order_data.get('items', []):
            qty = item.get('quantity', 1)
            name = item.get('product_name', '')
            p.text(f"{qty}x {name}\n")
            
            for mat in item.get('materials', []):
                p.text(f"  - {mat.get('material_name')}: {mat.get('quantity')} {mat.get('unit')}\n")
            
        p.text("--------------------------------\n")
        
        # Totals
        p.set(align='right', bold=True)
        total = order_data.get('final_selling_price') or order_data.get('estimated_cost', 0)
        p.text(f"TOTAL: {total:,.0f} DA\n")
        
        paid = order_data.get('total_payments', 0)
        rem = order_data.get('remaining_balance', 0)
        
        p.set(align='right', bold=False)
        p.text(f"Versment: {paid:,.0f} DA\n")
        if rem > 0:
            p.text(f"Reste: {rem:,.0f} DA\n")
            
        p.set(align='left')
        notes = order_data.get('notes')
        if notes:
            p.text(f"\nNOTES:\n{notes}\n")

        p.set(align='center')
        p.text("--------------------------------\n")
        p.text(f"{company_data.get('footer', 'Merci de votre visite !')}\n\n\n")
        p.cut()
