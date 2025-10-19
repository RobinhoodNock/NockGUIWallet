global nock_to_usd, change_24h
import os
import sys
import webbrowser
import tkinter as tk
from tkinter import ttk, Toplevel, messagebox, filedialog, simpledialog
import threading
import subprocess
import queue
import re
import json
import csv
import requests
from datetime import datetime
from tkinter import font
import queue
balance_queue = queue.Queue()

nock_to_usd = 0.0
change_24h = 0.0

# --- Node Status Check ---

def is_nockchain_running():
    try:
        if sys.platform.startswith("win"):
            # Tasklist output
            output = subprocess.check_output("tasklist", shell=True).decode().lower()
            return "nockchain.exe" in output
        else:
            # ps aux output
            output = subprocess.check_output(["ps", "aux"]).decode().lower()
            return "nockchain" in output
    except Exception as e:
        print("Error checking processes:", e)
        return False

# --- Enhanced Visual Components ---

class ModernButton(tk.Frame):
    def __init__(self, parent, text, command=None, style="primary", **kwargs):
        super().__init__(parent, **kwargs)
        
        self.command = command
        self.style = style
        self.enabled = True
        
        # Style definitions
        styles = {
            "primary": {"bg": "#4F46E5", "fg": "white", "hover": "#4338CA"},
            "secondary": {"bg": "#6B7280", "fg": "white", "hover": "#4B5563"},
            "success": {"bg": "#059669", "fg": "white", "hover": "#047857"},
            "danger": {"bg": "#DC2626", "fg": "white", "hover": "#B91C1C"}
        }
        
        self.colors = styles.get(style, styles["primary"])
        
        self.button = tk.Label(
            self, 
            text=text,
            bg=self.colors["bg"],
            fg=self.colors["fg"],
            padx=20,
            pady=10,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2"
        )
        self.button.pack(fill="both", expand=True)
        
        # Hover effects
        self.button.bind("<Enter>", self.on_enter)
        self.button.bind("<Leave>", self.on_leave)
        self.button.bind("<Button-1>", self.on_click)
        
    def on_enter(self, e):
        if self.enabled:
            self.button.config(bg=self.colors["hover"])
        
    def on_leave(self, e):
        if self.enabled:
            self.button.config(bg=self.colors["bg"])
        
    def on_click(self, e):
        if self.command and self.enabled:
            self.command()
            
    def set_enabled(self, enabled):
        self.enabled = enabled
        if enabled:
            self.button.config(cursor="hand2", bg=self.colors["bg"])
        else:
            self.button.config(cursor="arrow", bg="#9CA3AF")

class ModernFrame(tk.Frame):
    def __init__(self, parent, title=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.config(bg="#FFFFFF", relief="flat", bd=0)
        
        if title:
            title_frame = tk.Frame(self, bg="#f8fafc", height=40)
            title_frame.pack(fill="x", pady=(0, 10))
            title_frame.pack_propagate(False)
            
            title_label = tk.Label(
                title_frame,
                text=title,
                font=("Segoe UI", 12, "bold"),
                bg="#f8fafc",
                fg="#1F2937"
            )
            title_label.pack(pady=10)

class ModernEntry(tk.Frame):
    def __init__(self, parent, placeholder="", **kwargs):
        super().__init__(parent, **kwargs)
        self.config(bg="white")
        
        self.entry = tk.Entry(
            self,
            font=("Segoe UI", 10),
            bg="white",
            fg="#374151",
            relief="flat",
            bd=0,
            insertbackground="#4F46E5"
        )
        self.entry.pack(fill="both", expand=True, padx=12, pady=8)
        
        # Border frame
        self.border = tk.Frame(self, height=1, bg="#D1D5DB")
        self.border.pack(fill="x", side="bottom")
        
        # Placeholder functionality
        self.placeholder = placeholder
        if placeholder:
            self.show_placeholder()
            self.entry.bind("<FocusIn>", self.hide_placeholder)
            self.entry.bind("<FocusOut>", self.show_placeholder)
    
    def show_placeholder(self, event=None):
        if not self.entry.get():
            self.entry.insert(0, self.placeholder)
            self.entry.config(fg="#9CA3AF")
    
    def hide_placeholder(self, event=None):
        if self.entry.get() == self.placeholder:
            self.entry.delete(0, tk.END)
            self.entry.config(fg="#374151")
    
    def get(self):
        value = self.entry.get()
        return "" if value == self.placeholder else value

class StatusBar(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.config(bg="#1F2937", height=30)
        self.pack_propagate(False)
        
        # Price info
        self.price_frame = tk.Frame(self, bg="#1F2937")
        self.price_frame.pack(side="left", padx=20)
        
        self.price_label = tk.Label(
            self.price_frame,
            text="NOCK: $0.000000",
            font=("Segoe UI", 9),
            bg="#1F2937",
            fg="#10B981"
        )
        self.price_label.pack(side="left")
        
        self.change_label = tk.Label(
            self.price_frame,
            text="▲ 0.00%",
            font=("Segoe UI", 9),
            bg="#1F2937",
            fg="#10B981"
        )
        self.change_label.pack(side="left", padx=(10, 0))
        
        # Node Status
        self.node_label = tk.Label(
            self,
            text="Node: Checking...",
            font=("Segoe UI", 9),
            bg="#1F2937",
            fg="#F59E0B"
        )
        self.node_label.pack(side="left", padx=20)
        
        # Connection status
        self.connection_label = tk.Label(
            self,
            text="API: https://nockchain-api.zorp.io ✅",
            font=("Segoe UI", 9),
            bg="#1F2937",
            fg="#10B981"
        )
        self.connection_label.pack(side="left", padx=20)
        
        # Time
        self.time_label = tk.Label(
            self,
            text="",
            font=("Segoe UI", 9),
            bg="#1F2937",
            fg="#9CA3AF"
        )
        self.time_label.pack(side="right", padx=20)
        
        self.update_time()
        self.update_price()
        self.update_node_status()
    
    def update_node_status(self):
        """Update node status every 30 seconds"""
        def check_status():
            try:
                if is_nockchain_running():
                    self.node_label.config(text="Node: Running ✅", fg="#10B981")
                else:
                    self.node_label.config(text="Node: Not Running 💢", fg="#EF4444")
            except Exception:
                self.node_label.config(text="Node: Error", fg="#EF4444")
        
        # Run in background thread to avoid blocking UI
        threading.Thread(target=check_status, daemon=True).start()
        
        # Schedule next update
        self.after(30000, self.update_node_status)  # Check every 30 seconds
    
    def update_time(self):
        now = datetime.now()
        self.time_label.config(text=now.strftime("%b %d %H:%M:%S"))
        self.after(1000, self.update_time)
    
    def update_price(self):
        # Mock price update - replace with actual API call
        price, change = get_price()
        if price:
            self.price_label.config(text=f"NOCK: ${price:.6f}")
            color = "#10B981" if change >= 0 else "#EF4444"
            symbol = "▲" if change >= 0 else "▼"
            self.change_label.config(text=f"{symbol} {abs(change):.2f}%", fg=color)
        
        self.after(60000, self.update_price)  # Update every minute

# --- Updated gRPC Configuration ---
GRPC_ARGS = ["--client", "public", "--public-grpc-server-addr", "https://nockchain-api.zorp.io"]

def create_modern_window(title, width, height):
    """Helper function to create modern styled windows"""
    win = tk.Toplevel(root)
    win.title(title)
    win.geometry(f"{width}x{height}")
    win.configure(bg="#F9FAFB")
    return win

def print_to_output(text):
    output_text.config(state='normal')
    output_text.insert(tk.END, text + "\n")
    output_text.see(tk.END)
    output_text.config(state='disabled')

def update_output_text(output_text_widget, output_queue):
    try:
        while True:
            item = output_queue.get_nowait()
            if item is None:
                return
            output_text_widget.config(state='normal')
            output_text_widget.insert(tk.END, item)
            output_text_widget.see(tk.END)
            output_text_widget.config(state='disabled')
    except queue.Empty:
        pass
    output_text_widget.after(100, update_output_text, output_text_widget, output_queue)

def truncate_pubkey(pk, front=8, back=8):
    if len(pk) <= front + back + 3:
        return pk
    return f"{pk[:front]}...{pk[-back:]}"

# Price API
API_URL = "https://api.coinpaprika.com/v1/tickers/nock-nockchain"

def get_price():
    try:
        response = requests.get(API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()
        price = data["quotes"]["USD"]["price"]
        change_24h = data["quotes"]["USD"]["percent_change_24h"]
        return price, change_24h
    except Exception:
        return 0.000123, 2.45  # Mock data

# Manual node status check function
def on_check_node_status():
    """Manually check and display node status"""
    def check():
        try:
            if is_nockchain_running():
                print_to_output("Node Status: Nockchain process is running")
                status_bar.node_label.config(text="Node: Running", fg="#10B981")
            else:
                print_to_output("Node Status: Nockchain process not found")
                status_bar.node_label.config(text="Node: Not Running", fg="#EF4444")
        except Exception as e:
            print_to_output(f"Error checking node status: {e}")
    
    threading.Thread(target=check, daemon=True).start()
        
# --- Create Wallet ---

def on_create_wallet():
    # Ask user before overwriting wallet
    confirm = messagebox.askyesno(
        "Confirm Wallet Creation",
        "Are you sure you want to create a new wallet?\nYour current wallet will be deleted."
    )
    if not confirm:
        print_to_output("Wallet creation canceled by user.")
        return

    # Clear old logs
    output_text.config(state='normal')
    output_text.delete('1.0', tk.END)
    output_text.config(state='disabled')

    print_to_output("Creating new wallet...")

    # Start background worker
    threading.Thread(target=worker, daemon=True).start()

def worker():
    try:
        proc = subprocess.Popen(
            ["nockchain-wallet"] + GRPC_ARGS + ["keygen"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        capture_next = False  # track if we should capture the next line

        for line in proc.stdout:
            clean_line = ANSI_ESCAPE.sub("", line).strip()
            if not clean_line:
                continue

            # filter out noisy logs
            if "kernel::boot" in clean_line or "Tracy" in clean_line:
                continue

            # if line is a key label -> print it and capture next line
            if any(k in clean_line for k in [
                "Public Key", "Private Key", "Chain Code",
                "Import Private Key", "Import Public Key", "Seed Phrase"
            ]):
                root.after(0, print_to_output, clean_line)
                capture_next = True
                continue

            # if last line was a label, this is its value
            if capture_next:
                root.after(0, print_to_output, clean_line)
                capture_next = False
                continue

        proc.stdout.close()
        proc.wait()
        root.after(0, print_to_output, "✅ Wallet created successfully!")
        root.after(0, lambda: messagebox.showinfo("Wallet Created", "Wallet created successfully."))

    except Exception as e:
        root.after(0, print_to_output, f"❌ Error creating wallet: {e}")
        root.after(0, lambda: messagebox.showerror("Error", f"Failed to create wallet:\n{e}"))

# -------------------- Helper Functions -------------------- #
def extract_pubkey_from_output(output):
    """Extract public key from derive-child command output"""
    if not output:
        return None

    # Look for base58-like strings (length > 30 chars)
    for line in output.splitlines():
        line = line.strip()
        # Remove leading label like "Public Key:" or "- Public Key:"
        line = re.sub(r'^(?:-?\s*)?Public Key:\s*', '', line, flags=re.IGNORECASE)
        # Remove quotes
        if line.startswith("'") and line.endswith("'"):
            line = line[1:-1]

        # Only accept long alphanumeric strings (typical base58)
        if len(line) > 30 and all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in line):
            return line

    return None

def export_derived_children_csv(derived_children, output_text):
    """Export derived children indexes and pubkeys to CSV"""
    if not derived_children:
        output_text.after(0, lambda: output_text.insert(tk.END, "⚠️ No derived children found.\n"))
        return

    filename = os.path.join(os.getcwd(), "childrenindexes.csv")
    try:
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['index', 'pubkey'])
            for child in derived_children:
                writer.writerow([child['index'], child.get('pubkey') or ''])

        output_text.after(0, lambda: output_text.insert(tk.END, f"📊 Derived children CSV exported: {filename}\n"))
    except Exception as e:
        output_text.after(0, lambda: output_text.insert(tk.END, f"⚠️ Could not export CSV: {str(e)}\n"))

def save_derived_children(children_list):
    """Save derived children information to a JSON file"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"derived_children_{timestamp}.json"
        save_data = {
            'derivation_session': timestamp,
            'total_children': len(children_list),
            'children': children_list
        }
        with open(filename, 'w') as f:
            json.dump(save_data, f, indent=2)

        output_text.after(0, lambda: output_text.insert(tk.END, f"📁 Child indices saved to: {filename}\n"))
    except Exception as e:
        output_text.after(0, lambda: output_text.insert(tk.END, f"⚠️ Warning: Could not save indices: {str(e)}\n"))

# -------------------- Main Function -------------------- #
def on_derive_children():
    num_children = simpledialog.askinteger(
        "Derive Child Keys",
        "How many child keys would you like to derive?",
        minvalue=1, maxvalue=100
    )
    if not num_children:
        output_text.config(state='normal')
        output_text.insert(tk.END, "Child key derivation canceled.\n")
        output_text.config(state='disabled')
        return

    # Clear previous log
    output_text.config(state='normal')
    output_text.delete('1.0', tk.END)
    output_text.insert(tk.END, f"🧬 Deriving {num_children} child key(s)...\n\n")
    output_text.config(state='disabled')

    derived_children = []

    def log_message(msg):
        output_text.after(0, lambda: _log(msg))

    def _log(msg):
        output_text.config(state='normal')
        output_text.insert(tk.END, msg + "\n")
        output_text.see(tk.END)
        output_text.config(state='disabled')

    def worker():
        for i in range(num_children):
            log_message(f"➡️ Deriving child key {i}...")
            try:
                result = subprocess.run(
                    ["nockchain-wallet"] + GRPC_ARGS + ["derive-child", str(i)],
                    capture_output=True, text=True, check=True
                )

                pubkey = extract_pubkey_from_output(result.stdout)
                child_info = {
                    'index': i,
                    'pubkey': pubkey,
                    'timestamp': datetime.now().isoformat(),
                    'derive_output': result.stdout.strip() if result.stdout else None
                }
                derived_children.append(child_info)

                log_message(f"✅ Child key {i} derived successfully")
                if pubkey:
                    preview = f"{pubkey[:16]}...{pubkey[-8:]}" if len(pubkey) > 24 else pubkey
                    log_message(f"   📋 Pubkey: {preview}")

            except subprocess.CalledProcessError as e:
                log_message(f"❌ Error deriving child {i}: {e.stderr}")
                child_info = {
                    'index': i,
                    'pubkey': None,
                    'timestamp': datetime.now().isoformat(),
                    'error': e.stderr.strip() if e.stderr else str(e)
                }
                derived_children.append(child_info)

        # After all children
        log_message(f"\n✅ {len(derived_children)} children processed!")
        log_message("Exporting CSV and saving JSON...")
        export_derived_children_csv(derived_children, output_text)
        save_derived_children(derived_children)
        log_message("🔹 Derivation session complete!")

    threading.Thread(target=worker, daemon=True).start()

        
# --- Export Keys ---

def on_export_keys():
    # Clear previous logs
    output_text.config(state='normal')
    output_text.delete('1.0', tk.END)
    output_text.insert(tk.END, "✨ Exporting wallet keys...\n")
    output_text.config(state='disabled')

    def worker():
        try:
            proc = subprocess.Popen(
                ["nockchain-wallet"] + GRPC_ARGS + ["export-keys"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            export_path = "keys.export"  # fallback default

            for raw_line in proc.stdout:
                line = ANSI_ESCAPE.sub("", raw_line).strip()
                if not line:
                    continue

                # Ignore kernel boot messages
                if "kernel::boot" in line or "Tracy tracing" in line:
                    continue

                # Extract export path
                if "Path:" in line:
                    export_path = line.split("Path:")[-1].strip(" '")
                    root.after(0, print_to_output, f"📂 Keys exported to: {export_path}")
                    continue

            proc.stdout.close()
            proc.wait()

            # Final success message
            root.after(0, print_to_output, "✅ Wallet keys exported successfully!")
            root.after(0, lambda: messagebox.showinfo(
                "Keys Exported", 
                f"Wallet keys exported successfully to:\n{export_path}"
            ))

        except Exception as e:
            root.after(0, print_to_output, f"❌ Error exporting keys: {e}")
            root.after(0, lambda: messagebox.showerror("Error", f"Failed to export keys:\n{e}"))

    threading.Thread(target=worker, daemon=True).start()
    
# --- Import Keys ---

# ANSI escape code remover
ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

def on_import_keys():
    file_path = filedialog.askopenfilename(
        title="Select Keys File",
        filetypes=[("Export Files", "*.export")]
    )

    if not file_path:
        return

    # Clear previous logs and show starting message
    output_text.config(state='normal')
    output_text.delete('1.0', tk.END)
    output_text.insert(tk.END, f"📂 Loading Wallet from:\n{file_path}\n\n")
    output_text.insert(tk.END, "⏳ Importing keys, please wait...\n")
    output_text.config(state='disabled')

    def worker():
        try:
            process = subprocess.Popen(
                ["nockchain-wallet"] + GRPC_ARGS + ["import-keys", "--file", file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Stream stdout
            for line in process.stdout:
                clean_line = ansi_escape.sub('', line.strip())
                if clean_line:
                    # Ignore kernel boot messages
                    if clean_line.startswith("I [") and "kernel::boot" in clean_line:
                        continue
                    root.after(0, print_to_output, clean_line)

            # Stream stderr
            for line in process.stderr:
                clean_line = ansi_escape.sub('', line.strip())
                if clean_line:
                    root.after(0, print_to_output, clean_line)

            return_code = process.wait()

            # Check return code for success
            if return_code == 0:
                root.after(0, print_to_output, "\n✅ Keys imported successfully!")
                root.after(0, lambda: messagebox.showinfo("Success", "Keys imported successfully!"))
            else:
                root.after(0, print_to_output, "\n❌ Failed to import keys. See log above.")
                root.after(0, lambda: messagebox.showerror("Error", "Failed to import keys."))

        except Exception as e:
            root.after(0, print_to_output, f"\n❌ Error importing keys: {e}")
            root.after(0, lambda: messagebox.showerror("Error", f"An error occurred:\n{e}"))

    threading.Thread(target=worker, daemon=True).start()

# Remove ANSI escape sequences
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# -------------------- PUBKEY PARSER -------------------- #
def get_pubkeys():
    try:
        proc = subprocess.Popen(
            ["nockchain-wallet"] + GRPC_ARGS + ["list-master-addresses"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        addresses = []
        collecting_key = False
        current_key_lines = []

        for raw_line in proc.stdout:
            line = ANSI_ESCAPE.sub('', raw_line).strip()
            if not line:
                continue

            if line.startswith("- Address:"):
                key_part = line[len("- Address:"):].strip().strip("'").strip("(active)")
                if key_part:
                    # Single-line key
                    addresses.append(key_part.replace(" ", ""))
                    collecting_key = False
                    current_key_lines = []
                else:
                    # Multi-line key
                    collecting_key = True
                    current_key_lines = []
                continue

            if collecting_key and line.startswith("- Chain Code:"):
                key = ''.join(current_key_lines).replace(" ", "").strip("'")
                if key:
                    addresses.append(key)
                collecting_key = False
                current_key_lines = []
                continue

            if collecting_key:
                current_key_lines.append(line.strip("'").strip())

        # In case the last key was not followed by a chain code
        if collecting_key and current_key_lines:
            key = ''.join(current_key_lines).replace(" ", "").strip("'")
            if key:
                addresses.append(key)

        proc.wait()
        return addresses

    except Exception as e:
        print(f"Error while getting addresses: {e}")
        return []
        
def copy_to_clipboard(pubkey):
    root.clipboard_clear()
    root.clipboard_append(pubkey)
    # Show modern notification
    show_notification("Copied!", f"Pubkey copied to clipboard")

def show_notification(title, message):
    notification = tk.Toplevel(root)
    notification.title("")
    notification.geometry("300x80+{}+{}".format(
        root.winfo_x() + root.winfo_width() - 320,
        root.winfo_y() + 50
    ))
    notification.configure(bg="#10B981")
    notification.overrideredirect(True)
    notification.attributes("-topmost", True)
    
    tk.Label(
        notification,
        text="✅ " + title,
        font=("Segoe UI", 10, "bold"),
        bg="#10B981",
        fg="white"
    ).pack(pady=5)
    
    tk.Label(
        notification,
        text=message,
        font=("Segoe UI", 9),
        bg="#10B981",
        fg="white"
    ).pack()
    
    # Auto close after 2 seconds
    notification.after(2000, notification.destroy)
    
# -------------------- Helper Functions -------------------- #
def truncate_pubkey(key, start_chars=32, end_chars=32):
    if len(key) <= start_chars + end_chars + 3:
        return key
    return f"{key[:start_chars]}...{key[-end_chars:]}"
    
    # ---------------- Thread-safe logging ---------------- #
def log_message(msg):
    output_text.after(0, lambda: _append_text(msg))

def _append_text(msg):
    output_text.config(state='normal')
    output_text.insert(tk.END, msg + "\n")
    output_text.see(tk.END)
    output_text.config(state='disabled')

# ---------------- CSV Parsing ---------------- #
CSV_FOLDER = os.path.expanduser("~/nockchain")  # adjust if needed
def auto_check_balance(pubkey, balance_main_label=None, balance_details_label=None):
    # Clear the output log before starting
    output_text.config(state='normal')
    output_text.delete("1.0", tk.END)
    output_text.config(state='disabled')

    balance_queue = queue.Queue()

    def run_balance_check():
        try:
            log_message(f"🔹 Checking balance for {truncate_pubkey(pubkey)}...")

            # Run CSV command; wallet creates CSV automatically
            subprocess.run(
                ["nockchain-wallet"] + GRPC_ARGS + ["list-notes-by-pubkey-csv", pubkey],
                check=True,
                cwd=CSV_FOLDER
            )
            log_message("✅ Balance CSV generated successfully!")

            # Set active master address
            log_message(f"🔹 Setting active master address...")
            subprocess.run(
                ["nockchain-wallet"] + GRPC_ARGS + ["set-active-master-address", pubkey],
                check=True,
                cwd=CSV_FOLDER
            )
            log_message("✅ Set active successfully!")


            # Parse CSV for summary
            total_assets, nocks = parse_balance_csv(pubkey)
            if balance_main_label and balance_details_label:
                root.after(0, lambda: balance_main_label.config(
                    text=f"{nocks:,.4f} NOCK",
                    fg="#10b93d" if total_assets > 0 else "#FF0000"
                ))
                root.after(0, lambda: balance_details_label.config(
                    text=f"{total_assets:,} Nicks\n${nocks * nock_to_usd:,.2f} USD",
                    fg="#6B7280"
                ))

        except subprocess.CalledProcessError as e:
            log_message(f"❌ Error running balance command: {e}")
        except Exception as e:
            log_message(f"❌ Unexpected error: {e}")
        finally:
            balance_queue.put(None)

    threading.Thread(target=run_balance_check, daemon=True).start()
    update_output_text(output_text, balance_queue)

def parse_balance_csv(pubkey):
    # Look for CSV files starting with 'notes-' + pubkey
    csv_files = [f for f in os.listdir(CSV_FOLDER)
                 if f.startswith(f"notes-{pubkey}")]
    
    if not csv_files:
        log_message("⚠️ No balance CSV found for this pubkey.")
        return 0, 0

    # If multiple, pick the latest by modification time
    csv_files.sort(key=lambda f: os.path.getmtime(os.path.join(CSV_FOLDER, f)), reverse=True)
    latest_csv = csv_files[0]
    csv_path = os.path.join(CSV_FOLDER, latest_csv)
    log_message(f"📄 Reading CSV: {latest_csv}")

    total_assets = 0
    with open(csv_path, newline='') as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        for row in reader:
            if len(row) > 2 and row[2].isdigit():
                total_assets += int(row[2])

    nocks = total_assets / 65536
    usd_balance = nocks * nock_to_usd
    log_message(f"💰 Total Assets: {total_assets} Nicks (~{nocks:.4f} NOCK, ${usd_balance:.2f} USD)")
    return total_assets, nocks

def display_pubkeys(pubkeys):
    for widget in pubkeys_content.winfo_children():
        widget.destroy()

    if not pubkeys:
        tk.Label(pubkeys_content, text="🔑 No public keys found",
                 font=("Segoe UI", 12), bg="white", fg="#6B7280").pack(pady=20)
        return
    
    # State variables
    selected_index = tk.IntVar(value=0)
    dropdown_open = tk.BooleanVar(value=False)

    # Frame for dropdown
    dropdown_frame = tk.Frame(pubkeys_content, bg="white", bd=1, relief="solid")
    dropdown_frame.pack(fill="x", padx=10, pady=10)

    # Button to toggle dropdown
    selected_btn = tk.Button(
        dropdown_frame,
        text=f"Key 1: {truncate_pubkey(pubkeys[0])} ▼",
        font=("Consolas", 10),
        bg="white",
        fg="#374151",
        bd=0,
        anchor="w",
        command=lambda: toggle_dropdown()
    )
    selected_btn.pack(fill="x", padx=10, pady=5)

    # --- Scrollable dropdown (Canvas + Scrollbar) ---
    dropdown_canvas = tk.Canvas(dropdown_frame, bg="white", highlightthickness=0, height=300)
    scrollbar = tk.Scrollbar(dropdown_frame, orient="vertical", command=dropdown_canvas.yview)
    options_frame = tk.Frame(dropdown_canvas, bg="white")

    options_frame.bind(
        "<Configure>",
        lambda e: dropdown_canvas.configure(scrollregion=dropdown_canvas.bbox("all"))
    )

    window_id = dropdown_canvas.create_window((0, 0), window=options_frame, anchor="nw")
    dropdown_canvas.configure(yscrollcommand=scrollbar.set)

    # Hide initially
    dropdown_canvas.pack_forget()
    scrollbar.pack_forget()

    # Copy button + display label
    info_frame = tk.Frame(pubkeys_content, bg="white")
    info_frame.pack(fill="x", padx=10, pady=(0, 10))

    key_label = tk.Label(
        info_frame,
        text=truncate_pubkey(pubkeys[0]),
        font=("Consolas", 10),
        bg="white",
        fg="#374151"
    )
    key_label.pack(side="left", padx=(0, 10))

    copy_btn = ModernButton(
        info_frame,
        text="📋 Copy",
        style="secondary",
        command=lambda: copy_to_clipboard(pubkeys[selected_index.get()])
    )
    copy_btn.pack(side="right")
    copy_btn.config(width=80, height=35)

    # Toggle dropdown
    def toggle_dropdown():
        if dropdown_open.get():
            dropdown_canvas.pack_forget()
            scrollbar.pack_forget()
        else:
            dropdown_canvas.pack(side="left", fill="both", expand=True, padx=0, pady=5)
            scrollbar.pack(side="right", fill="y")
        dropdown_open.set(not dropdown_open.get())

    # Populate options
    for i, pk in enumerate(pubkeys):
        def select_key(idx=i):
            selected_index.set(idx)
            selected_btn.config(text=f"Key {idx+1}: {truncate_pubkey(pubkeys[idx])} ▼")
            key_label.config(text=truncate_pubkey(pubkeys[idx]))
            toggle_dropdown()
            auto_check_balance(pubkeys[idx], balance_main, balance_details)

        btn = tk.Button(
            options_frame,
            text=f"Key {i+1}: {truncate_pubkey(pk)}",
            font=("Consolas", 10),
            bg="white",
            fg="#374151",
            bd=0,
            anchor="w",
            command=select_key
        )
        btn.pack(fill="x", pady=2)

        # Hover effect
        btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#F3F4F6"))
        btn.bind("<Leave>", lambda e, b=btn: b.config(bg="white"))
        
# --- Nocknames API Calls ---

def resolve_nockname(address):
    try:
        url = f"https://api.nocknames.com/resolve?address={address}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            name = data.get("name")
            if name:
                return name
            else:
                return None
        else:
            return None
    except Exception:
        return None

def resolve_nockaddress(name):
    try:
        url = f"https://api.nocknames.com/resolve?name={name}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            address = data.get("address")
            if address:
                return address
            else:
                return None
        else:
            return None
    except Exception:
        return None

def open_nocknames_window():
    win = create_modern_window("Nocknames", 800, 600)
    
    # Header
    header_frame = tk.Frame(win, bg="#1F2937", height=60)
    header_frame.pack(fill="x")
    header_frame.pack_propagate(False)
    
    header_content = tk.Frame(header_frame, bg="#1F2937")
    header_content.pack(fill="both", expand=True, padx=20, pady=15)
    
    tk.Label(
        header_content,
        text="👨 Nocknames Resolution Service",
        font=("Segoe UI", 14, "bold"),
        bg="#1F2937",
        fg="white"
    ).pack(side="left")
    
    register_btn = ModernButton(
        header_content, 
        text="Register New",
        command=lambda: webbrowser.open_new_tab("https://nocknames.com"),
        style="success"
    )
    register_btn.pack(side="right")
    
    # Main content
    main_frame = tk.Frame(win, bg="#F9FAFB")
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Address to Name section
    addr_frame = ModernFrame(main_frame, title="Resolve Name from Address")
    addr_frame.pack(fill="x", pady=(0, 15))
    
    tk.Label(addr_frame, text="Wallet Address", font=("Segoe UI", 10, "bold"), bg="white", fg="#374151").pack(anchor="w", padx=20, pady=(15, 5))
    
    addr_input_frame = tk.Frame(addr_frame, bg="white")
    addr_input_frame.pack(fill="x", padx=20, pady=(0, 15))
    
    address_entry = ModernEntry(addr_input_frame, placeholder="Enter wallet address...")
    address_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
    
    addr_result = tk.Text(addr_frame, height=2, bg="#F8FAFC", fg="#374151", font=("Consolas", 9), state='disabled', relief="flat", bd=0)
    addr_result.pack(fill="x", padx=20, pady=(0, 15))
    
    def resolve_address():
        address = address_entry.get().strip()
        if not address:
            messagebox.showerror("Input Error", "Address field is empty.")
            return
        addr_result.config(state='normal')
        addr_result.delete('1.0', tk.END)
        addr_result.insert(tk.END, "Resolving...")
        addr_result.config(state='disabled')

        def worker():
            name = resolve_nockname(address)
            result = name if name else "(No name found for this address)"
            def update_ui():
                addr_result.config(state='normal')
                addr_result.delete('1.0', tk.END)
                addr_result.insert(tk.END, result)
                addr_result.config(state='disabled')
            win.after(0, update_ui)

        threading.Thread(target=worker, daemon=True).start()
    
    resolve_addr_btn = ModernButton(addr_input_frame, text="Resolve", command=resolve_address, style="secondary")
    resolve_addr_btn.pack(side="right")
    
    # Name to Address section
    name_frame = ModernFrame(main_frame, title="Resolve Address from Name")
    name_frame.pack(fill="x")
    
    tk.Label(name_frame, text="Nockname", font=("Segoe UI", 10, "bold"), bg="white", fg="#374151").pack(anchor="w", padx=20, pady=(15, 5))
    
    name_input_frame = tk.Frame(name_frame, bg="white")
    name_input_frame.pack(fill="x", padx=20, pady=(0, 15))
    
    name_entry = ModernEntry(name_input_frame, placeholder="Enter nockname...")
    name_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
    
    name_result = tk.Text(name_frame, height=2, bg="#F8FAFC", fg="#374151", font=("Consolas", 9), state='disabled', relief="flat", bd=0)
    name_result.pack(fill="x", padx=20, pady=(0, 15))
    
    def resolve_name():
        name = name_entry.get().strip()
        if not name:
            messagebox.showerror("Input Error", "Name field is empty.")
            return
        name_result.config(state='normal')
        name_result.delete('1.0', tk.END)
        name_result.insert(tk.END, "Resolving...")
        name_result.config(state='disabled')

        def worker():
            address = resolve_nockaddress(name)
            result = address if address else "(No address found for this name)"
            def update_ui():
                name_result.config(state='normal')
                name_result.delete('1.0', tk.END)
                name_result.insert(tk.END, result)
                name_result.config(state='disabled')
            win.after(0, update_ui)

        threading.Thread(target=worker, daemon=True).start()
    
    resolve_name_btn = ModernButton(name_input_frame, text="Resolve", command=resolve_name, style="secondary")
    resolve_name_btn.pack(side="right")

def open_sign_message_window():
    win = create_modern_window("Sign Message", 600, 350)
    win.attributes("-topmost", True)  # keep window on top

    # Header
    header_frame = tk.Frame(win, bg="#1F2937", height=60)
    header_frame.pack(fill="x")
    header_frame.pack_propagate(False)
    tk.Label(
        header_frame,
        text="📝 Digital Message Signing",
        font=("Segoe UI", 14, "bold"),
        bg="#1F2937",
        fg="white"
    ).pack(pady=15)

    # Content
    content = ModernFrame(win)
    content.pack(fill="both", expand=True, padx=20, pady=20)

    tk.Label(content, text="Message to Sign", font=("Segoe UI", 11, "bold"),
             bg="white", fg="#374151").pack(anchor="w", padx=20, pady=(15, 5))

    message_frame = tk.Frame(content, bg="white")
    message_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    message_text = tk.Text(message_frame, height=6, bg="white", fg="#374151",
                           font=("Segoe UI", 10), relief="flat", bd=1,
                           highlightbackground="#E5E7EB", highlightthickness=1, wrap="word")
    message_text.pack(fill="both", expand=True)

    def sign_message():
        message = message_text.get("1.0", tk.END).strip()
        if not message:
            messagebox.showerror("Error", "Please enter a message to sign.")
            return

        # Clear main output
        output_text.config(state='normal')
        output_text.delete("1.0", tk.END)
        output_text.insert(tk.END, f"--- Signing Message ---\n")
        output_text.insert(tk.END, f"Message: {message[:100]}{'...' if len(message) > 100 else ''}\n")
        output_text.insert(tk.END, "Processing digital signature...\n")
        output_text.config(state='disabled')

        q = queue.Queue()

        def run_sign():
            try:
                proc = subprocess.Popen(
                    ["nockchain-wallet"] + GRPC_ARGS + ["sign-message", "-m", message],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
                )

                for line in proc.stdout:
                    clean_line = ANSI_ESCAPE.sub('', line).strip()
                    if not clean_line:
                        continue

                    # Remove timestamp/metadata like I (12:20:24) [no]
                    if clean_line.startswith(("I (", "E (")):
                        idx = clean_line.find("]")
                        if idx != -1:
                            clean_line = clean_line[idx+1:].strip()
                        else:
                            idx = clean_line.find(")")
                            if idx != -1:
                                clean_line = clean_line[idx+1:].strip()

                    lower_line = clean_line.lower()
                    # Skip kernel/system logs
                    if any(term in lower_line for term in ["kernel::boot", "nockchain_npc.sock", "nockapp"]):
                        continue

                    # Result formatting
                    if "signed" in lower_line or "success" in lower_line:
                        q.put(f"✅ Success: {clean_line}\n")
                    elif "error" in lower_line or "failed" in lower_line:
                        q.put(f"Error: {clean_line}\n")
                    # ignore other info lines

                proc.stdout.close()
                proc.wait()
            except Exception as e:
                q.put(f"Error signing message: {e}\n")
            finally:
                q.put(None)

        threading.Thread(target=run_sign, daemon=True).start()
        update_output_text(output_text, q)
        win.destroy()

    ModernButton(content, text="Sign Message", command=sign_message).pack(padx=20, pady=10)


def open_verify_message_window():
    win = create_modern_window("Verify Message", 700, 500)
    win.attributes("-topmost", True)

    # Header
    header_frame = tk.Frame(win, bg="#1F2937", height=60)
    header_frame.pack(fill="x")
    header_frame.pack_propagate(False)
    tk.Label(
        header_frame,
        text="🔏 Digital Signature Verification",
        font=("Segoe UI", 14, "bold"),
        bg="#1F2937",
        fg="white"
    ).pack(pady=15)

    # Content
    content = ModernFrame(win)
    content.pack(fill="both", expand=True, padx=20, pady=20)

    tk.Label(content, text="Original Message", font=("Segoe UI", 10, "bold"),
             bg="white", fg="#374151").pack(anchor="w", padx=20, pady=(15, 5))
    message_entry = ModernEntry(content, placeholder="Enter the original message...")
    message_entry.pack(fill="x", padx=20, pady=(0, 15))

    tk.Label(content, text="Signature File Location", font=("Segoe UI", 10, "bold"),
             bg="white", fg="#374151").pack(anchor="w", padx=20, pady=(0, 5))
    folder_var = tk.StringVar()
    folder_entry = ModernEntry(content, placeholder="Select folder containing signature file...")
    folder_entry.pack(fill="x", padx=20, pady=(0, 10))

    def browse_folder():
        folder = filedialog.askdirectory(initialdir=os.path.expanduser("~"))
        if folder:
            folder_var.set(folder)
            folder_entry.entry.delete(0, tk.END)
            folder_entry.entry.insert(0, folder)
            folder_entry.entry.config(fg="#374151")

    ModernButton(content, text="Browse", command=browse_folder, style="secondary").pack(padx=20, pady=(0, 15))

    tk.Label(content, text="Public Key (Base58)", font=("Segoe UI", 10, "bold"),
             bg="white", fg="#374151").pack(anchor="w", padx=20, pady=(0, 5))
    pubkey_entry = ModernEntry(content, placeholder="Enter public key for verification...")
    pubkey_entry.pack(fill="x", padx=20, pady=(0, 20))

    def verify_message():
        message = message_entry.get().strip()
        folder = folder_var.get().strip()
        pubkey = pubkey_entry.get().strip()

        if not message or not folder or not pubkey:
            messagebox.showerror("Error", "Please fill in all fields.")
            return

        sig_file = os.path.join(folder, "message.sig")
        if not os.path.isfile(sig_file):
            messagebox.showerror("Error", f"Signature file not found:\n{sig_file}")
            return

        # Clear main output
        output_text.config(state='normal')
        output_text.delete("1.0", tk.END)
        output_text.insert(tk.END, f"--- Verifying Message ---\n")
        output_text.insert(tk.END, f"Message: {message[:50]}{'...' if len(message) > 50 else ''}\n")
        output_text.insert(tk.END, f"Signature file: {sig_file}\n")
        output_text.insert(tk.END, f"Public key: {truncate_pubkey(pubkey)}\n\n")
        output_text.config(state='disabled')

        q = queue.Queue()

        def run_verify():
            try:
                proc = subprocess.Popen(
                    ["nockchain-wallet"] + GRPC_ARGS + 
                     ["verify-message", "-m", message, "-s", sig_file, "-p", pubkey],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
                )

                for line in proc.stdout:
                    clean_line = ANSI_ESCAPE.sub('', line).strip()
                    if not clean_line:
                        continue

                    # Remove timestamp/metadata like I (12:12:43) [no]
                    if clean_line.startswith(("I (", "E (")):
                        idx = clean_line.find("]")
                        if idx != -1:
                            clean_line = clean_line[idx+1:].strip()
                        else:
                            idx = clean_line.find(")")
                            if idx != -1:
                                clean_line = clean_line[idx+1:].strip()

                    lower_line = clean_line.lower()
                    # Skip system logs
                    if any(term in lower_line for term in ["kernel::boot", "nockchain_npc.sock", "nockapp"]):
                        continue

                    # Result formatting
                    if "valid signature" in lower_line or "success" in lower_line:
                        q.put(f"✅ Success: {clean_line}\n")
                    elif "invalid signature" in lower_line or "not verified" in lower_line:
                        q.put(f"Failed: {clean_line}\n")
                    # ignore other info lines

                proc.stdout.close()
                proc.wait()
            except Exception as e:
                q.put(f"Error verifying message: {e}\n")
            finally:
                q.put(None)

        threading.Thread(target=run_verify, daemon=True).start()
        update_output_text(output_text, q)
        win.destroy()

    ModernButton(content, text="Verify Signature", command=verify_message).pack(padx=20, pady=10)


def on_get_pubkeys():
    btn_get_pubkeys.button.config(text="Loading...")
    btn_get_pubkeys.set_enabled(False)
    
    output_text.config(state='normal')
    output_text.delete('1.0', tk.END)
    output_text.insert(tk.END, "Fetching Public Keys...\nThis may take a moment...\n\n")
    output_text.config(state='disabled')

    def worker():
        pubkeys = get_pubkeys()
        def update_ui():
            display_pubkeys(pubkeys)
            output_text.config(state='normal')
            output_text.insert(tk.END, f"Found {len(pubkeys)} public keys\n")
            if pubkeys:
                for i, pk in enumerate(pubkeys, 1):
                    output_text.insert(tk.END, f"   {i}. {pk}\n")
            output_text.config(state='disabled')
            btn_get_pubkeys.button.config(text="🔑 Get Pubkeys")
            btn_get_pubkeys.set_enabled(True)
        root.after(0, update_ui)

    threading.Thread(target=worker, daemon=True).start()

def on_send():
    # Get values from modern entries
    sender = sender_entry.get().strip()
    recipient = recipient_entry.get().strip()
    gift = gift_entry.get().strip()
    fee = fee_entry.get().strip()
    index = index_entry.get().strip()  # optional field

    # Validate required fields
    if not all([sender, recipient, gift, fee]):
        messagebox.showerror("Input Error", "Please fill all fields except Index (optional).")
        return

    if not (re.fullmatch(r"[A-Za-z0-9]+", sender) and re.fullmatch(r"[A-Za-z0-9]+", recipient)):
        messagebox.showerror("Input Error", "Sender and Recipient pubkeys must be alphanumeric.")
        return

    if not (gift.isdigit() and fee.isdigit()):
        messagebox.showerror("Input Error", "Gift and Fee must be numeric.")
        return

    btn_send.button.config(text="Sending...")
    btn_send.set_enabled(False)

    output_text.config(state='normal')
    output_text.delete('1.0', tk.END)

    # Define tags for colors
    output_text.tag_config("info", foreground="black")
    output_text.tag_config("success", foreground="green")
    output_text.tag_config("error", foreground="red")

    # Print initial info
    output_text.insert(tk.END, "Initiating transaction...\n", "info")
    output_text.insert(tk.END, f"From: {truncate_pubkey(sender)}\n", "info")
    output_text.insert(tk.END, f"To: {truncate_pubkey(recipient)}\n", "info")
    output_text.insert(tk.END, f"Amount: {gift} Nicks\n", "info")
    output_text.insert(tk.END, f"Fee: {fee} Nicks\n\n", "info")
    output_text.config(state='disabled')

    q = queue.Queue()

    def run_send():
        try:
            cmd = ["bash", "./sendsimple.sh"] + GRPC_ARGS
            if index != "":
                cmd.extend(["--index", index])

            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )

            # Send inputs to the script
            proc.stdin.write(f"{sender}\n{recipient}\n{gift}\n{fee}\n")
            proc.stdin.flush()
            proc.stdin.close()

            for line in proc.stdout:
                # Skip verbose logs
                if any(kw in line.lower() for kw in ["kernel::boot", "tracy tracing", "serf: cold"]):
                    continue
                # Color-code success/failure lines
                if "draft transaction created" in line.lower() or "transaction sent successfully" in line.lower():
                    q.put(("success", line))
                elif "failed" in line.lower() or "error" in line.lower():
                    q.put(("error", line))
                else:
                    q.put(("info", line))
            proc.stdout.close()
            proc.wait()

        except Exception as e:
            q.put(("error", f"Error sending transaction: {e}\n"))
        finally:
            q.put(None)

    # Update GUI text with colors
    def update_text():
        try:
            while True:
                item = q.get_nowait()
                if item is None:
                    break
                tag, line = item
                output_text.config(state='normal')
                output_text.insert(tk.END, line, tag)
                output_text.see(tk.END)
                output_text.config(state='disabled')
        except queue.Empty:
            root.after(100, update_text)

    threading.Thread(target=run_send, daemon=True).start()
    update_text()

    # Re-enable button after delay
    def reenable_btn():
        btn_send.button.config(text="Send Transaction")
        btn_send.set_enabled(True)
    root.after(8000, reenable_btn)
    
# Header
root = tk.Tk()
root.title("Robinhood's Nockchain Wallet Pro Edition")
root.geometry("1920x1080")
root.configure(bg="#1F2937")
header = tk.Frame(root, bg="#1F2937", height=60)
header.pack(fill="x")
header.pack_propagate(False)

header_content = tk.Frame(header, bg="#1F2937")
header_content.pack(fill="both", expand=True, padx=30, pady=15)

# Action buttons in header
header_buttons = tk.Frame(header_content, bg="#1F2937")
header_buttons.pack(side="top", pady=0)        # pack it at the top
header_buttons.place(relx=0.5, rely=0.5, anchor="center")  # center it

btn_create_wallet = ModernButton(header_buttons, text="✨ Create Wallet", command=on_create_wallet, style="secondary")
btn_create_wallet.pack(side="left", padx=2)

btn_derive_children = ModernButton(header_buttons, text="🧬 Derive Children", command=on_derive_children, style="secondary")
btn_derive_children.pack(side="left", padx=2)

btn_import_keys = ModernButton(header_buttons, text="📂 Import Keys", command=on_import_keys, style="secondary")
btn_import_keys.pack(side="left", padx=2)

btn_export_keys = ModernButton(header_buttons, text="💾 Export Keys", command=on_export_keys, style="secondary")
btn_export_keys.pack(side="left", padx=2)

btn_get_pubkeys = ModernButton(header_buttons, text="🔑 Get Pubkeys", command=on_get_pubkeys)
btn_get_pubkeys.pack(side="left", padx=2)

btn_nocknames = ModernButton(header_buttons, text="👨 Names", command=open_nocknames_window, style="secondary")
btn_nocknames.pack(side="left", padx=2)

btn_sign = ModernButton(header_buttons, text="📝 Sign", command=open_sign_message_window, style="secondary")
btn_sign.pack(side="left", padx=2)

btn_verify = ModernButton(header_buttons, text="🔏 Verify", command=open_verify_message_window, style="secondary")
btn_verify.pack(side="left", padx=2)

# Main content area
main_container = tk.Frame(root, bg="#1F2937")
main_container.pack(fill="both", expand=True, padx=20, pady=20)

# Left panel - Main content
left_panel = tk.Frame(main_container, bg="#1F2937")
left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

# Pubkeys section
pubkeys_frame = ModernFrame(left_panel, title="Public Keys")
pubkeys_frame.pack(fill="x", pady=(0, 15))

pubkeys_content = tk.Frame(pubkeys_frame, bg="white")
pubkeys_content.pack(fill="both", expand=True, pady=10)

# Activity Log section (moved to left, below pubkeys)
output_frame = ModernFrame(left_panel, title="Activity Log")
output_frame.pack(fill="both", expand=True)

output_text = tk.Text(
    output_frame,
    bg="white",
    fg="#1F2937",
    font=("Consolas", 9),
    relief="flat",
    bd=0,
    state='disabled',
    wrap="word"
)
output_text.pack(fill="both", expand=True, padx=20, pady=20)

# Scrollbar for output
scrollbar = ttk.Scrollbar(output_text)
scrollbar.pack(side="right", fill="y")
output_text.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=output_text.yview)

# Create a right-side container to hold multiple sections
right_side = tk.Frame(main_container, bg="#F3F4F6")
right_side.pack(side="right", fill="y", padx=(10, 0))

# --- Right Balance section ---
balance_frame = ModernFrame(right_side, title="🏦 Balance 🏦")
balance_frame.pack(fill="x", pady=(0,0))

balance_content = tk.Frame(balance_frame, bg="white", height=100)
balance_content.pack(fill="x", padx=10, pady=10)
balance_content.pack_propagate(False)

# Balance display elements
balance_main = tk.Label(
    balance_content,
    text="0.00 NOCK",
    font=("Segoe UI", 13, "bold"),
    bg="white",
    fg="#FF0000"
)
balance_main.pack(pady=(10, 5))

balance_details = tk.Label(
    balance_content,
    text="Select a key to view balance",
    font=("Segoe UI", 11),
    bg="white",
    fg="#6B7280"
)
balance_details.pack()

# --- Send Transaction Panel ---
right_panel = tk.Frame(right_side, bg="#F9FAFB")
right_panel.pack(fill="x", pady=(0,5))

# --- Directly below ---
below_panel = tk.Frame(right_side, bg="#F9FAFB")
below_panel.pack(fill="x", pady=(0,5))

tk.Label(
    below_panel,
    text="📡 Block Explorers",
    bg="#F9FAFB",
    font=("Segoe UI", 13, "bold")
).pack(pady=20)

btn_explorer = ModernButton(below_panel, text="🌐 NockBlocks", command=lambda: webbrowser.open_new_tab("https://nockblocks.com"), style="secondary")
btn_explorer.pack(pady=(0,10))

# --- Directly below 2 ---
below_panel = tk.Frame(right_side, bg="#F9FAFB")
below_panel.pack(fill="x", pady=(0,5))

tk.Label(
    below_panel,
    text="🛟 Mining Pools",
    bg="#F9FAFB",
    font=("Segoe UI", 13, "bold")
).pack(pady=20)

btn_explorer = ModernButton(below_panel, text="🐬 NockPool", command=lambda: webbrowser.open_new_tab("https://nockpool.com"), style="secondary")
btn_explorer.pack(pady=(0,10))

# Send Transaction Panel
send_frame = ModernFrame(right_panel, title="Send Transaction")
send_frame.pack(fill="x")
send_frame.config(width=400)

# Modern form fields
fields_frame = tk.Frame(send_frame, bg="white")
fields_frame.pack(fill="both", expand=True, padx=20, pady=10)

tk.Label(fields_frame, text="Sender Public Key", font=("Segoe UI", 10, "bold"), bg="white", fg="#374151").pack(anchor="w", pady=(0, 5))
sender_entry = ModernEntry(fields_frame, placeholder="Enter sender pubkey...")
sender_entry.pack(fill="x", pady=(0, 15))

tk.Label(fields_frame, text="Recipient Public Key", font=("Segoe UI", 10, "bold"), bg="white", fg="#374151").pack(anchor="w", pady=(0, 5))
recipient_entry = ModernEntry(fields_frame, placeholder="Enter recipient pubkey...")
recipient_entry.pack(fill="x", pady=(0, 15))

amounts_frame = tk.Frame(fields_frame, bg="white")
amounts_frame.pack(fill="x", pady=(0, 15))

gift_frame = tk.Frame(amounts_frame, bg="white")
gift_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
tk.Label(gift_frame, text="Gift Amount (Nicks)", font=("Segoe UI", 10, "bold"), bg="white", fg="#374151").pack(anchor="w", pady=(0, 5))
gift_entry = ModernEntry(gift_frame, placeholder="0")
gift_entry.pack(fill="x")

fee_frame = tk.Frame(amounts_frame, bg="white")
fee_frame.pack(side="left", fill="x", expand=True, padx=(10, 0))
tk.Label(fee_frame, text="Fee (Nicks)", font=("Segoe UI", 10, "bold"), bg="white", fg="#374151").pack(anchor="w", pady=(0, 5))
fee_entry = ModernEntry(fee_frame, placeholder="0")
fee_entry.pack(fill="x")

# Index field
tk.Label(fields_frame, text="Index", font=("Segoe UI", 10, "bold"), bg="white", fg="#374151").pack(anchor="w", pady=(0, 5))
index_entry = ModernEntry(fields_frame, placeholder="Enter index for Child or leave blank for Master...")
index_entry.pack(fill="x", pady=(0, 15))

btn_send = ModernButton(fields_frame, text="Send Transaction", command=on_send, style="primary")
btn_send.pack(fill="x", pady=15)

# Status bar
status_bar = StatusBar(root)
status_bar.pack(side="bottom", fill="x")

# Initial message
output_text.config(state='normal')
output_text.insert(tk.END, "Welcome to Robinhood's Nockchain Wallet Pro Edition!\n")
output_text.insert(tk.END, "─" * 50 + "\n")
output_text.insert(tk.END, "Click 'Get Pubkeys' to load your public keys.\n\n")
output_text.insert(tk.END, f"API Server: https://nockchain-api.zorp.io\n")
output_text.insert(tk.END, f"Connection Status: ✅ Ready\n")
# Node status check
if is_nockchain_running():
    node_status = "✅ Nockchain node is running"
else:
    node_status = "💢 Nockchain node is not running 💢"

output_text.insert(tk.END, f"Node Status: {node_status}\n\n")

output_text.insert(
    "end", 
    "💝 Donations 💝: 2deHSdGpxFh1hhC2qMjM5ujBvG7auCeoJLcLAwGKpfSsb8zfaTms8SMdax7fCyjoVTmbqXgUDWLc7GURXtMeEZbPz57LeakGKTAWZSVYcBwyHvcHuskqL4rVrw56rPXT6wSt\n"
)
output_text.config(state='disabled')

# Show empty list right away
display_pubkeys([])

nock_to_usd, change_24h = get_price()

root.mainloop()
