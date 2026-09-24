"""
KasirKu Cash Drawer Service
Layanan untuk membuka laci uang (cash drawer)
"""

import traceback
from datetime import datetime

import config


class DrawerService:
    """Service untuk kontrol cash drawer"""

    ESC_P = b"\x1b\x70\x00\x19\xfa"  # ESC/POS command buka drawer

    def open_drawer(self, user_id: int = None, keterangan: str = "auto") -> bool:
        """Buka cash drawer"""
        try:
            printer = self._get_printer()
            if printer:
                printer.cashdraw(2)  # Pin 2 atau 5
                self._log_activity(user_id, "auto", keterangan)
                return True
            else:
                # Fallback: kirim command langsung ke port
                self._open_via_raw_command(user_id, keterangan)
                return True
        except Exception as e:
            print(f"[DrawerService] Error buka drawer: {e}")
            return False

    def _get_printer(self):
        """Dapatkan printer untuk kirim command drawer"""
        try:
            from database.db import db
            printer_type = db.get_setting("printer_type", config.PRINTER_TYPE)

            if printer_type == "usb":
                from escpos.printer import Usb
                if config.PRINTER_VENDOR_ID and config.PRINTER_PRODUCT_ID:
                    return Usb(config.PRINTER_VENDOR_ID, config.PRINTER_PRODUCT_ID)

            elif printer_type == "serial":
                from escpos.printer import Serial
                from database.db import db
                port = db.get_setting("printer_port", config.PRINTER_SERIAL_PORT)
                return Serial(port, baudrate=config.PRINTER_BAUD_RATE)

            elif printer_type == "network":
                from escpos.printer import Network
                from database.db import db
                host = db.get_setting("printer_host", config.PRINTER_NETWORK_HOST)
                port = int(db.get_setting("printer_network_port",
                                          str(config.PRINTER_NETWORK_PORT)))
                return Network(host, port)

        except Exception:
            pass
        return None

    def _open_via_raw_command(self, user_id: int, keterangan: str):
        """Kirim command ESC/POS langsung via serial"""
        try:
            import serial
            from database.db import db
            port = db.get_setting("printer_port", config.PRINTER_SERIAL_PORT)
            with serial.Serial(port, baudrate=config.PRINTER_BAUD_RATE, timeout=1) as ser:
                ser.write(self.ESC_P)
            self._log_activity(user_id, "manual", keterangan)
        except Exception as e:
            print(f"[DrawerService] Serial command error: {e}")
            # Simulasi untuk development
            print("[DrawerService] SIMULASI: Cash drawer dibuka!")
            self._log_activity(user_id, "simulated", keterangan)

    def _log_activity(self, user_id: int, aksi: str, keterangan: str = ""):
        """Catat log aktivitas drawer"""
        try:
            from database.db import db
            from database.models import LogDrawer
            with db.get_session() as session:
                log = LogDrawer(
                    user_id=user_id,
                    aksi=aksi,
                    keterangan=keterangan
                )
                session.add(log)
                session.commit()
        except Exception as e:
            print(f"[DrawerService] Log error: {e}")

    def manual_open(self, user_id: int = None) -> bool:
        """Buka drawer secara manual"""
        return self.open_drawer(user_id=user_id, keterangan="manual open")
