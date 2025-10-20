# SPDX-FileCopyrightText: Copyright (C) 2025 ARDUINO SA <http://www.arduino.cc>
#
# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations
from typing import List, Dict, Optional
import threading, os, json, re

# ---------------- Framebuffer core ----------------
class MatrixCore:
    def __init__(self, w: int, h: int):
        self.W, self.H = int(w), int(h)
        self.N = self.W * self.H
        self._lock = threading.Lock()
        self._frame: List[int] = [0] * self.N

    # --- read ---
    def state(self) -> Dict:
        with self._lock:
            return {"w": self.W, "h": self.H, "frame": self._frame.copy()}

    def raw_frame(self) -> List[int]:
        with self._lock:
            return self._frame.copy()

    def csv_gs3(self) -> str:
        with self._lock:
            return ",".join("7" if v else "0" for v in self._frame)

    # --- write ---
    def _idx(self, x: int, y: int) -> int:
        return y * self.W + x

    def set_xy(self, x: int, y: int, v: int) -> None:
        if not (0 <= x < self.W and 0 <= y < self.H): return
        i = self._idx(x, y)
        with self._lock: self._frame[i] = 1 if int(v) else 0

    def toggle_xy(self, x: int, y: int) -> None:
        if not (0 <= x < self.W and 0 <= y < self.H): return
        i = self._idx(x, y)
        with self._lock: self._frame[i] = 0 if self._frame[i] else 1

    def set_frame(self, arr: List[int]) -> None:
        if not isinstance(arr, list) or len(arr) != self.N: return
        with self._lock: self._frame[:] = [1 if int(v) else 0 for v in arr]

    def clear(self) -> None:
        with self._lock:
            for i in range(self.N): self._frame[i] = 0

    def fill(self) -> None:
        with self._lock:
            for i in range(self.N): self._frame[i] = 1


# ---------------- Simple JSON icon store ----------------
class IconStore:
    def __init__(self, w: int, h: int, filename: str = "icons.json"):
        self.W, self.H = int(w), int(h)
        self.N = self.W * self.H
        self.path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        self._icons: Dict[str, List[int]] = {}
        self._load()

    def list_payload(self) -> List[Dict]:
        return [{"name": k, "frame": v} for k, v in sorted(self._icons.items())]

    def save(self, name: Optional[str], frame: Optional[List[int]]) -> str:
        nm = self._safe_name(name or "icon")
        fr = self._normalize_frame(frame) if frame is not None else None
        if fr is None:
            return nm
        if nm in self._icons:
            base, i = nm, 2
            while f"{base} ({i})" in self._icons: i += 1
            nm = f"{base} ({i})"
        self._icons[nm] = fr
        self._flush()
        return nm

    def load(self, name: Optional[str]) -> Optional[List[int]]:
        return self._icons.get(self._safe_name(name or ""))

    def delete(self, name: Optional[str]) -> bool:
        nm = self._safe_name(name or "")
        if nm in self._icons:
            del self._icons[nm]
            self._flush()
            return True
        return False

    def _normalize_frame(self, arr: List[int]) -> Optional[List[int]]:
        if not isinstance(arr, list) or len(arr) != self.N: return None
        return [1 if int(v) else 0 for v in arr]

    @staticmethod
    def _safe_name(name: str) -> str:
        name = (name or "").strip()
        name = re.sub(r"[^A-Za-z0-9 _.-]", "_", name)
        return name[:64] or "icon"

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._icons = {
                k: self._normalize_frame(v) or [0]*self.N
                for k, v in data.items()
                if isinstance(k, str) and isinstance(v, list)
            }
        except FileNotFoundError:
            self._icons = {}
        except Exception as e:
            print("[icons] load error:", e)
            self._icons = {}

    def _flush(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._icons, f, indent=2)
        except Exception as e:
            print("[icons] save error:", e)


# ---------------- WebUI wiring (handlers live here) ----------------
def wire_webui(ui, core: MatrixCore, icons: IconStore) -> None:
    """
    Register all socket handlers on the passed `ui` instance.
    Keeps `main.py` clean: it just calls wire_webui(ui, core, icons).
    """
    import json as _json  # local import; no Arduino deps here

    def _payload(data):
        if isinstance(data, dict): return data
        if isinstance(data, str):
            try: return _json.loads(data) if data.strip() else {}
            except Exception: return {}
        return {}

    def _send_state(to_client=None):
        ui.send_message("state_update", core.state(), to_client)

    def on_get_initial_state(client, data):
        _send_state(client)
        ui.send_message("icons_list", icons.list_payload(), client)

    def on_get_icons(client, data):
        ui.send_message("icons_list", icons.list_payload(), client)

    def on_set_xy(client, data):
        d = _payload(data)
        try:
            x = int(d.get("x", -1)); y = int(d.get("y", -1))
        except Exception:
            return
        if not (0 <= x < core.W and 0 <= y < core.H): return

        if "value" in d:
            v = 1 if int(d["value"]) else 0
            core.set_xy(x, y, v)
        elif d.get("toggle", False):
            core.toggle_xy(x, y)
        else:
            core.set_xy(x, y, 1)
        _send_state()

    def on_set_frame(client, data):
        d = _payload(data)
        arr = d.get("frame")
        if not isinstance(arr, list) or len(arr) != core.N:
            print("[set_frame] rejected: missing or wrong-length frame")
            return
        core.set_frame(arr)
        _send_state()

    def on_clear(client, data):
        core.clear()
        _send_state()

    def on_fill(client, data):
        core.fill()
        _send_state()

    def on_save_icon(client, data):
        d = _payload(data)
        name = icons.save(d.get("name"), d.get("frame") or core.raw_frame())
        print(f"[icon] saved '{name}'")
        ui.send_message("icons_list", icons.list_payload())

    def on_load_icon(client, data):
        d = _payload(data)
        fr = icons.load(d.get("name"))
        if fr is None:
            print("[icon] load failed"); return
        core.set_frame(fr)
        _send_state()

    def on_delete_icon(client, data):
        d = _payload(data)
        if icons.delete(d.get("name")):
            ui.send_message("icons_list", icons.list_payload())

    # register
    ui.on_message("get_initial_state", on_get_initial_state)
    ui.on_message("get_icons",         on_get_icons)
    ui.on_message("set_xy",            on_set_xy)
    ui.on_message("set_frame",         on_set_frame)
    ui.on_message("clear",             on_clear)
    ui.on_message("fill",              on_fill)
    ui.on_message("save_icon",         on_save_icon)
    ui.on_message("load_icon",         on_load_icon)
    ui.on_message("delete_icon",       on_delete_icon)