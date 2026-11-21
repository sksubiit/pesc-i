"""Provider settings: persist preferences, never credentials."""

import json
import os
from pathlib import Path
import threading

from src.voice.providers import ModelConfig, PROVIDERS, discover_models

SETTINGS_PATH = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "pesc-i/settings.json"
)


class Settings:
    def draft_config(self):
        backend = PROVIDERS[self.provider.get()][0]
        return ModelConfig(
            backend,
            self.url.get().strip(),
            self.model.get().strip(),
            self.key.get().strip()
            or (os.environ.get("PESC_I_API_KEY", "") if backend == "remote" else ""),
            float(self.timeout.get()),
        )

    def provider_changed(self, _=None):
        self.discovery_cancelled.set()
        backend, url = PROVIDERS[self.provider.get()]
        self.url.set(url)
        self.model.set("")
        self.key.set("")
        self.model_combo.configure(values=())
        offline = backend == "template"
        self.url_entry.configure(state="disabled" if offline else "normal")
        self.key_entry.configure(state="disabled" if offline else "normal")
        self.connection.set(
            "Offline notes use verified move facts."
            if offline
            else "Checking server…"
            if backend != "remote"
            else "Enter your endpoint and key, then find models or type an ID."
        )
        if backend in ("lmstudio", "ollama"):
            self.refresh_models()

    def refresh_models(self):
        self.discovery_cancelled.set()
        self.discovery_cancelled = threading.Event()
        try:
            config = self.draft_config()
        except ValueError:
            self.connection.set("Enter a valid timeout before connecting.")
            return
        if config.backend == "template":
            self.connection.set("No server needed for engine notes.")
            return
        snapshot = (self.provider.get(), self.url.get(), self.key.get())
        self.connection.set("Looking for models…")

        def current():
            return snapshot == (self.provider.get(), self.url.get(), self.key.get())

        def loaded(models):
            if not current():
                return
            self.model_combo.configure(values=models)
            if self.model.get() not in models:
                self.model.set(models[0] if models else "")
            self.connection.set(
                f"Found {len(models)} models. Choose one, then Apply."
                if models
                else "Server reached; no chat models listed. Load or pull a model first."
            )

        def failed(exc):
            if current():
                self.connection.set(f"{exc} You can also enter a model ID manually.")

        self.discovery_worker.submit(
            lambda: discover_models(config), loaded, failed, self.discovery_cancelled
        )

    def apply_settings(self):
        try:
            config = self.draft_config()
            if not 5 <= config.timeout <= 180:
                raise ValueError("Timeout must be between 5 and 180 seconds.")
            if not 0.1 <= float(self.think_time.get()) <= 5:
                raise ValueError("Engine time must be between 0.1 and 5 seconds.")
            if config.backend != "template":
                config.endpoint("")
                if not config.model:
                    raise ValueError("Choose a model or type its exact ID.")
        except (ValueError, RuntimeError) as exc:
            self.connection.set(str(exc))
            return
        self.config = config
        self.active_text.set(
            f"Active: {self.provider.get()}" + (f" / {config.model}" if config.model else "")
        )
        self.connection.set("Applied. The next move uses these settings.")
        data = {
            "provider": self.provider.get(),
            "url": config.base_url,
            "model": config.model,
            "verbosity": self.verbosity.get(),
            "timeout": config.timeout,
            "engine_time": self.think_time.get(),
        }
        try:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS_PATH.write_text(json.dumps(data, indent=2) + "\n")
        except OSError:
            self.connection.set("Applied for this session; could not save settings.")

    def load_settings(self):
        try:
            data = json.loads(SETTINGS_PATH.read_text())
            if data.get("provider") in PROVIDERS:
                self.provider.set(data["provider"])
                self.url.set(data.get("url", ""))
                self.model.set(data.get("model", ""))
                self.verbosity.set(data.get("verbosity", "Brief"))
                self.timeout.set(str(data.get("timeout", 45)))
                self.think_time.set(str(data.get("engine_time", "0.4")))
                # Restore the draft; Apply is required before sending moves to a server.
                self.connection.set("Previous settings restored. Apply to enable commentary.")
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def limit(self):
        try:
            return min(5, max(0.1, float(self.think_time.get())))
        except ValueError:
            return 0.4
