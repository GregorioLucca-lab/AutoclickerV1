import os
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pyautogui
# --- MODIFICA: Aggiunta libreria per input "diretto" ---
try:
    import pydirectinput
except ImportError:
    print("Manca pydirectinput. Per favore installalo: pip install pydirectinput")
    messagebox.showerror("Errore Libreria", "Manca la libreria 'pydirectinput'.\nInstallala con: pip install pydirectinput")
    pydirectinput = None # Imposta a None per controlli futuri

import cv2
import numpy as np

CONF_FILE = "areas.json"
NUM_ZONES = 5

areas = [{"label": f"Zona {i+1}", "area": None, "template": None} for i in range(NUM_ZONES)]
global_threshold = 0.85
monitor_thread = None
stop_flag = threading.Event()


# ---------- Utility file per salvare/caricare ----------
def save_config():
    """Salva la configurazione corrente (aree, template, label) su file JSON."""
    with open(CONF_FILE, "w", encoding="utf-8") as f:
        json.dump(areas, f, ensure_ascii=False, indent=2)
    print("Config salvato in", CONF_FILE)


def load_config():
    """Carica la configurazione dal file JSON all'avvio."""
    global areas
    if os.path.exists(CONF_FILE):
        try:
            with open(CONF_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # merge per sicurezza: mantieni NUM_ZONES
            for i in range(NUM_ZONES):
                if i < len(data):
                    areas[i]["label"] = data[i].get("label", areas[i]["label"])
                    areas[i]["area"] = data[i].get("area", areas[i]["area"])
                    areas[i]["template"] = data[i].get("template", areas[i]["template"])
        except Exception as e:
            print("Errore caricamento config:", e)


# ---------- Selezione area con mouse (fullscreen overlay) ----------
def select_area_ui(zone_index):
    """Mostra un overlay trasparente per selezionare un'area dello schermo."""
    sel_win = tk.Toplevel(root)
    sel_win.attributes("-fullscreen", True)
    sel_win.attributes("-topmost", True)
    sel_win.attributes("-alpha", 0.25)
    sel_win.config(bg="black")

    canvas = tk.Canvas(sel_win, bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    rect_id = None
    start_x = start_y = None

    info = tk.Label(sel_win, text="Clicca e trascina per selezionare l'area.\nPremi ESC per annullare.",
                    bg="black", fg="white", font=("Segoe UI", 12))
    info.place(relx=0.5, rely=0.02, anchor="n")

    def on_key(event):
        if event.keysym == "Escape":
            sel_win.destroy()

    def on_button_down(event):
        nonlocal start_x, start_y, rect_id
        start_x = event.x_root
        start_y = event.y_root
        rect_id = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="red", width=3)

    def on_drag(event):
        nonlocal rect_id
        if rect_id is not None:
            canvas.coords(rect_id, start_x, start_y, event.x_root, event.y_root)

    def on_release(event):
        nonlocal rect_id
        end_x = event.x_root
        end_y = event.y_root
        x1 = min(start_x, end_x)
        y1 = min(start_y, end_y)
        x2 = max(start_x, end_x)
        y2 = max(start_y, end_y)
        w = x2 - x1
        h = y2 - y1
        if w < 5 or h < 5:
            messagebox.showwarning("Selezione non valida", "Area troppo piccola, riprova.")
            sel_win.destroy()
            return
        areas[zone_index]["area"] = [int(x1), int(y1), int(w), int(h)]
        save_config()
        update_zone_ui(zone_index)
        sel_win.destroy()

    canvas.bind("<Button-1>", on_button_down)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    sel_win.bind("<Key>", on_key)
    sel_win.focus_force()


# ---------- Carica template tramite file dialog ----------
def load_template(zone_index):
    """Apre una finestra per selezionare un file immagine come template."""
    filetypes = [("PNG/JPG images", ("*.png", "*.jpg", "*.jpeg", "*.bmp")), ("All files", "*.*")]
    path = filedialog.askopenfilename(title="Seleziona immagine template", filetypes=filetypes)
    if path:
        areas[zone_index]["template"] = path
        save_config()
        update_zone_ui(zone_index)


# ---------- Test matching singolo (mostra risultato) ----------
def test_zone(zone_index):
    """Esegue un test di matching singolo sulla zona e mostra il risultato."""
    cfg = areas[zone_index]
    if not cfg["area"]:
        messagebox.showinfo("Test zona", "Area non impostata.")
        return
    if not cfg["template"] or not os.path.exists(cfg["template"]):
        messagebox.showinfo("Test zona", "Template non impostato o file non trovato.")
        return

    x, y, w, h = cfg["area"]
    try:
        shot = pyautogui.screenshot(region=(x, y, w, h)) 
        frame = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2GRAY)
        template = cv2.imread(cfg["template"], cv2.IMREAD_GRAYSCALE)
        if template is None:
            messagebox.showerror("Errore", "Impossibile leggere il file template.")
            return

        th, tw = template.shape[:2]
        if th > frame.shape[0] or tw > frame.shape[1]:
            messagebox.showwarning("Errore Test", 
                                f"Il template ({tw}x{th}) è più grande dell'area ({w}x{h}).")
            return

        res = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        found = max_val >= global_threshold
        msg = f"Max matching: {max_val:.3f}\nSoglia attuale: {global_threshold}\nTrovato: {'Sì' if found else 'No'}"
        messagebox.showinfo("Risultato Test", msg)
    except Exception as e:
        messagebox.showerror("Errore Test", f"Si è verificato un errore: {e}")


# ---------- Aggiorna UI per una zona ----------
def update_zone_ui(i):
    """Aggiorna le label nell'interfaccia utente per una specifica zona."""
    cfg = areas[i]
    area_txt = f"{cfg['area']}" if cfg['area'] else "non impostata"
    templ_txt = os.path.basename(cfg['template']) if cfg['template'] else "non impostato"
    zone_labels[i]["area"].config(text=f"Area: {area_txt}")
    zone_labels[i]["template"].config(text=f"Template: {templ_txt}")
    zone_labels[i]["label_entry"].delete(0, tk.END)
    zone_labels[i]["label_entry"].insert(0, cfg["label"])


# ---------- THREAD di monitoraggio ----------
def monitor_loop():
    """Loop principale eseguito in un thread separato per il monitoraggio."""
    if pydirectinput is None:
        print("Errore: libreria pydirectinput non trovata. Il monitor non può avviarsi.")
        root.after(0, stop_monitor) 
        root.after(0, lambda: messagebox.showerror("Errore Libreria", 
        "Libreria 'pydirectinput' non trovata. Monitor fermato."))
        return

    # carichiamo i template in memoria per performance
    templates = []
    for cfg in areas:
        tp = None
        if cfg["template"] and os.path.exists(cfg["template"]):
            tp = cv2.imread(cfg["template"], cv2.IMREAD_GRAYSCALE)
            if tp is None:
                print(f"Impossibile leggere template per zona {cfg['label']}:", cfg["template"])
        templates.append(tp)

    print("Monitor avviato. Soglia:", global_threshold)
    while not stop_flag.is_set():
        for i, cfg in enumerate(areas):
            if stop_flag.is_set():
                break
            
            tpl = templates[i]
            
            if tpl is None:
                continue
            
            if not cfg["area"]:
                continue

            try:
                x, y, w, h = cfg["area"]
                shot = pyautogui.screenshot(region=(x, y, w, h))
                frame = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2GRAY)
                
                th, tw = tpl.shape[:2]
                if th > frame.shape[0] or tw > frame.shape[1]:
                    if templates[i] is not None:
                        print(f"Template più grande dell'area per zona {i+1}, skip.")
                        templates[i] = None # Evita di controllare di nuovo
                    continue
                
                res = cv2.matchTemplate(frame, tpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                
                if max_val >= global_threshold:
                    print(f"[{cfg['label']}] Match! max_val={max_val:.3f} -> Eseguo azione...")
                    
                    # --- MODIFICA CHIAVE: Azione condizionale ---
                    # Controlla se l'etichetta della zona contiene "rigioca"
                    if "rigioca" in cfg['label'].lower():
                        # Azione "Rigioca" (W + Enter con pause lunghe)
                        print(f"Azione Rigioca per '{cfg['label']}'")
                        pydirectinput.press("w")
                        time.sleep(3.0) # Pausa più lunga come richiesto
                        pydirectinput.press("enter")
                        time.sleep(22.0) # Pausa più lunga come richiesto

                    elif "ingresso" in cfg['label'].lower():
                        # Azione "Rigioca" (W + Enter con pause lunghe)
                        print(f"Azione Ingresso per '{cfg['label']}'")
                        pydirectinput.press("enter")
                        time.sleep(2.0) # Pausa più lunga come richiesto
                        pydirectinput.press("s")
                        time.sleep(2.0) # Pausa più lunga come richiesto

                    else:
                        # Azione "Standard" (D, W, Enter)
                        print(f"Azione Standard per '{cfg['label']}'")
                        pydirectinput.press("w")
                        time.sleep(3) 
                        pydirectinput.press("enter")
                        time.sleep(4.0)
                        pydirectinput.keyDown('c')
                        
                    # ---------------------------------------------
                    
                    # time.sleep(4.0) 

            except Exception as e:
                print(f"Errore nel monitoraggio (zona {i+1}): {e}")
                templates[i] = None 
                time.sleep(1.0) 

            time.sleep(0.15) # Piccola pausa tra il controllo di ogni zona
        
        time.sleep(0.5) # Pausa alla fine di un ciclo completo di tutte le zone
    print("Monitor terminato.")


def start_monitor():
    """Avvia il thread di monitoraggio."""
    global monitor_thread, stop_flag
    
    if pydirectinput is None:
        messagebox.showerror("Errore Libreria", "Manca la libreria 'pydirectinput'.\nInstallala con: pip install pydirectinput")
        return

    try:
        val = float(threshold_var.get())
        if 0.0 <= val <= 1.0:
            set_threshold(val)
        else:
            messagebox.showwarning("Soglia", "Inserisci valore tra 0.0 e 1.0")
            return
    except:
        messagebox.showwarning("Soglia", "Valore soglia non valido")
        return
    
    is_any_zone_valid = False
    for cfg in areas:
        if cfg["area"] and cfg["template"] and os.path.exists(cfg["template"]):
            is_any_zone_valid = True
            break
            
    if not is_any_zone_valid:
        messagebox.showwarning("Avvio Monitor", "Nessuna zona è configurata correttamente (area + template valido).")
        return

    stop_flag.clear()
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    status_label.config(text="Monitor: ATTIVO", fg="lightgreen")
    start_btn.config(state="disabled")
    stop_btn.config(state="normal")


def stop_monitor():
    """Ferma il thread di monitoraggio."""
    stop_flag.set()
    status_label.config(text="Monitor: FERMO", fg="orange")
    start_btn.config(state="normal")
    stop_btn.config(state="disabled")


def set_threshold(val):
    """Imposta la soglia globale di matching."""
    global global_threshold
    global_threshold = float(val)
    threshold_var.set(f"{global_threshold:.2f}")


# ---------- UI principale ----------
root = tk.Tk()
root.title("Auto 4 Zones - Template Matching")
root.geometry("760x560")
root.configure(bg="#1e1e1e")

style = ttk.Style()
style.configure("TButton", padding=6, relief="flat", font=("Segoe UI", 9))
# Stili per bottoni start/stop
style.configure("Start.TButton", background="#2d882d", foreground="white") 
style.configure("Stop.TButton", background="#aa2d2d", foreground="white")

title = tk.Label(root, text="Auto 4 Zones - Template Matching", font=("Segoe UI", 18, "bold"), fg="white", bg="#1e1e1e")
title.pack(pady=10)

frame_zones = tk.Frame(root, bg="#1e1e1e")
frame_zones.pack(pady=5, fill="x", padx=10)
frame_zones.grid_columnconfigure(0, weight=1)
frame_zones.grid_columnconfigure(1, weight=1)

zone_labels = []
for i in range(NUM_ZONES):
    zframe = tk.LabelFrame(frame_zones, text=f"Config Zona {i+1}", bg="#2a2a2a", fg="white", font=("Segoe UI", 10, "bold"), padx=10, pady=10)
    zframe.grid(row=i // 2, column=i % 2, padx=8, pady=8, sticky="nsew")

    lbl = tk.Label(zframe, text="Label:", bg="#2a2a2a", fg="white")
    lbl.grid(row=0, column=0, sticky="w", padx=6, pady=3)
    label_entry = tk.Entry(zframe, width=25, bg="#3a3a3a", fg="white", relief="flat", insertbackground="white")
    label_entry.grid(row=0, column=1, columnspan=2, padx=6, pady=3, sticky="we")
    label_entry.insert(0, areas[i]["label"])

    area_label = tk.Label(zframe, text=f"Area: {areas[i]['area']}", bg="#2a2a2a", fg="gray", wraplength=300, justify="left")
    area_label.grid(row=1, column=0, columnspan=3, sticky="w", padx=6, pady=3)

    template_label = tk.Label(zframe, text=f"Template: {os.path.basename(areas[i]['template']) if areas[i]['template'] else 'non impostato'}", bg="#2a2a2a", fg="gray", wraplength=300, justify="left")
    template_label.grid(row=2, column=0, columnspan=3, sticky="w", padx=6, pady=3)

    btn_sel = ttk.Button(zframe, text="Seleziona area", command=lambda idx=i: select_area_ui(idx))
    btn_sel.grid(row=3, column=0, padx=6, pady=6, sticky="ew")
    btn_load = ttk.Button(zframe, text="Carica template", command=lambda idx=i: load_template(idx))
    btn_load.grid(row=3, column=1, padx=6, pady=6, sticky="ew")
    btn_test = ttk.Button(zframe, text="Test zona", command=lambda idx=i: test_zone(idx))
    btn_test.grid(row=3, column=2, padx=6, pady=6, sticky="ew")
    
    # Funzione factory per creare il comando di salvataggio label
    def create_save_command(idx):
        def cmd_func():
            new_label = zone_labels[idx]["label_entry"].get()
            if not new_label:
                new_label = f"Zona {idx+1}" # fallback
            areas[idx]["label"] = new_label
            save_config()
            update_zone_ui(idx) # Aggiorna solo per sicurezza
            zframe.config(text=f"Config {areas[idx]['label']}") # Aggiorna titolo frame
        return cmd_func

    btn_save_label = ttk.Button(zframe, text="Salva label", command=create_save_command(i))
    btn_save_label.grid(row=0, column=3, padx=6, pady=3, sticky="e") 

    zframe.config(text=f"Config {areas[i]['label']}") 

    zone_labels.append({
        "frame": zframe,
        "area": area_label,
        "template": template_label,
        "label_entry": label_entry
    })

# pannello controllo
ctrl_frame = tk.Frame(root, bg="#1e1e1e")
ctrl_frame.pack(pady=20)

threshold_lbl = tk.Label(ctrl_frame, text="Soglia matching (0.0 - 1.0):", bg="#1e1e1e", fg="white")
threshold_lbl.grid(row=0, column=0, padx=6, pady=4)
threshold_var = tk.StringVar(value=f"{global_threshold:.2f}")
threshold_entry = tk.Entry(ctrl_frame, textvariable=threshold_var, width=6, bg="#3a3a3a", fg="white", relief="flat")
threshold_entry.grid(row=0, column=1, padx=6, pady=4)

start_btn = ttk.Button(ctrl_frame, text="▶ Avvia monitor", command=start_monitor, style="TButton") 
start_btn.grid(row=0, column=2, padx=8)
stop_btn = ttk.Button(ctrl_frame, text="■ Ferma monitor", command=stop_monitor, style="TButton", state="disabled") 
stop_btn.grid(row=0, column=3, padx=8)

save_btn = ttk.Button(ctrl_frame, text="Salva config", command=save_config, style="TButton")
save_btn.grid(row=0, column=4, padx=8)

status_label = tk.Label(root, text="Monitor: FERMO", bg="#1e1e1e", fg="orange", font=("Segoe UI", 11))
status_label.pack(pady=6)

# Carica config e aggiorna UI all'avvio
load_config()
for i in range(NUM_ZONES):
    update_zone_ui(i)
    zone_labels[i]["frame"].config(text=f"Config {areas[i]['label']}")

def on_closing():
    """Gestisce la chiusura della finestra."""
    stop_monitor()
    if monitor_thread and monitor_thread.is_alive():
        monitor_thread.join(timeout=0.5) 
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()
