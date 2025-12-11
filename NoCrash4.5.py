"""
Gestor de Máquinas Virtuais - VirtualBox Automation
---------------------------------------------------
Este script gerencia automaticamente uma VM baseada em um arquivo OVA,
realizando importação, reinicialização diária e recuperação automática.

Interface gráfica simples com Tkinter para visualização de logs.
"""

import os
import subprocess
import threading
import time
from datetime import datetime
from tkinter import Tk, Label, Text, END
from PIL import Image, ImageTk

# ============================================================
# CONFIGURAÇÕES
# ============================================================

OVA_PATH = r"C:\CAMINHO\PARA\SEU_ARQUIVO.ova"
BASE_FOLDER = r"C:\CAMINHO\PARA\BACKUPS"
VBOXMANAGE = r'"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"'
LOGO_PATH = r"C:\CAMINHO\PARA\LOGO.jpg"

SCHEDULE_TIME = "08:00"   # horário da rotina diária (HH:MM)

# ============================================================
# INTERFACE GRÁFICA
# ============================================================

root = Tk()
root.title("Gestor de VM - VirtualBox")
root.geometry("480x600")
root.resizable(False, False)
root.configure(bg="white")

# Logo (opcional)
try:
    logo_img = Image.open(LOGO_PATH).resize((180, 180))
    logo = ImageTk.PhotoImage(logo_img)
    Label(root, image=logo, bg="white").pack(pady=10)
except Exception:
    Label(root, text="(Logo não encontrado)", bg="white", fg="red").pack()

status_box = Text(root, height=20, width=55, bg="#f4f4f4", fg="black")
status_box.pack(pady=10)

def log(msg: str):
    status_box.insert(END, msg + "\n")
    status_box.see(END)
    root.update()

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def run_cmd(command: str):
    return subprocess.run(
        command,
        shell=True, capture_output=True, text=True
    )

def list_vms():
    result = run_cmd(f"{VBOXMANAGE} list vms")
    return result.stdout.strip().split("\n") if result.stdout else []

def list_running_vms():
    result = run_cmd(f"{VBOXMANAGE} list runningvms")
    return result.stdout

def get_last_vm():
    lines = list_vms()
    if not lines:
        return None
    return lines[-1].split('"')[1]

def vm_exists(name: str):
    return any(name in line for line in list_vms())

def vm_is_running(name: str):
    return name in list_running_vms()

def create_incremental_folder():
    os.makedirs(BASE_FOLDER, exist_ok=True)

    existing = [
        int(x.replace("VM_", ""))
        for x in os.listdir(BASE_FOLDER)
        if x.startswith("VM_") and x.replace("VM_", "").isdigit()
    ]

    next_num = max(existing) + 1 if existing else 1
    new_path = os.path.join(BASE_FOLDER, f"VM_{next_num}")
    os.makedirs(new_path)

    return new_path

def stop_vm(name: str):
    log(f"Desligando VM: {name}")
    run_cmd(f'{VBOXMANAGE} controlvm "{name}" poweroff')
    time.sleep(3)

def delete_vm(name: str):
    log(f"Removendo VM: {name}")
    run_cmd(f'{VBOXMANAGE} unregistervm "{name}" --delete')
    time.sleep(2)

def import_vm(destination: str):
    log("Importando VM...")

    cmd = (
        f'{VBOXMANAGE} import "{OVA_PATH}" '
        f'--vsys 0 '
        f'--basefolder "{destination}" '
        f'--options keepallmacs'
    )

    run_cmd(cmd)
    log("Importação concluída.")

    return get_last_vm()

def start_vm(name: str):
    log(f"Iniciando VM: {name}")
    run_cmd(f'{VBOXMANAGE} startvm "{name}" --type headless')
    log("VM iniciada.")

# ============================================================
# VERIFICAÇÃO INICIAL
# ============================================================

def initial_check():
    last = get_last_vm()

    if not last:
        log("Nenhuma VM encontrada. Importando nova instância...")
        folder = create_incremental_folder()
        vm = import_vm(folder)
        start_vm(vm)
        return

    if not vm_is_running(last):
        log("VM estava desligada no boot. Iniciando...")
        start_vm(last)
    else:
        log("A VM já estava ligada.")

initial_check()

# ============================================================
# ROTINA DIÁRIA + AUTO-RECOVERY
# ============================================================

def daily_routine():
    last_execution = ""

    while True:
        now = datetime.now().strftime("%H:%M")

        # Rotina diária programada
        if now == SCHEDULE_TIME and last_execution != now:
            last_execution = now

            log("===== EXECUTANDO ROTINA DIÁRIA =====")

            current_vm = get_last_vm()

            if vm_is_running(current_vm):
                stop_vm(current_vm)

            delete_vm(current_vm)

            folder = create_incremental_folder()
            new_vm = import_vm(folder)

            start_vm(new_vm)
            log("===== ROTINA FINALIZADA =====")

        # Auto-Recovery (caso a VM desligue sozinha)
        current_vm = get_last_vm()
        if current_vm and not vm_is_running(current_vm):
            log("A VM desligou inesperadamente. Reiniciando...")
            start_vm(current_vm)

        time.sleep(10)

threading.Thread(target=daily_routine, daemon=True).start()

root.mainloop()
