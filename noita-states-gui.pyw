import os, sys, shutil, hashlib, json, builtins, glob, subprocess, traceback, tkinter, tkinter.filedialog, tkinter.ttk

#TODO: Manage popup = 2 folder views side by side (noita saves, backup saves), if one folder is moved to another then it will be overwritten/copied, when a folder is clicked then show a context menu (noita specific: backup, clear, prune, purge) (backup specific: load, remove, rename)
#Polish list: Replace placeholder in logger

def smart_copy(src, dst):
    try:
        def hashdata(file_path, algorithm='sha1'):
            hash_func = hashlib.new(algorithm)
            with open(file_path, 'rb') as file:
                while chunk := file.read(8192):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        sstat = hashdata(src)
        dstat = hashdata(dst)
        if sstat == dstat:
            return
    except OSError:
        pass
    shutil.copy2(src, dst)


def fetch_config(configs):
    newcon = False
    data = {}
    try:
        with open(configs) as c:
            data = json.loads(c.read().replace('\\', '/'))
    except FileNotFoundError:
        newcon = True
        pass
    except Exception as e:
        print(f'Config file (noita-states-gui-config.json) could not be read: {e}')
        newcon = True
        pass
    return data, newcon


def edit_config(configs, savespath, output, noitaexe):
    os.makedirs(os.path.dirname(configs), exist_ok=True)
    with open(configs, 'w', encoding='utf-8') as c:
        json.dump({'savespath': savespath, 'output': output, 'noitaexe': noitaexe}, c, indent=4)


def bring_picker(widget, dirorfile="dir"):
    if dirorfile == "dir":
        location = tkinter.filedialog.askdirectory()
    elif dirorfile == "file":
        location = tkinter.filedialog.askopenfilename()

    if location:
        widget.delete(0, tkinter.END)
        widget.insert([0], location)


def start_noita(noitaexe):
    if sys.platform.startswith('win'):
        subprocess.Popen([noitaexe], cwd=os.path.dirname(noitaexe) or None)
    else:
        subprocess.Popen(noitaexe, shell=True)

def main():
    pjoin = os.path.join
    joinp = os.path.join
    cwd = os.getcwd()
    out = sys.stdout
    cmds = []
    autopath = True

    APP_DIRNAME = "NoitaStates"
    def default_config_dir():
        home = os.path.expanduser("~")
        if sys.platform.startswith("win"):
            base = os.environ.get("APPDATA") or joinp(home, "AppData", "Roaming")
            return joinp(base, APP_DIRNAME)
        if sys.platform == "darwin":
            return joinp(home, "Library", "Application Support", APP_DIRNAME)
        base = os.environ.get("XDG_CONFIG_HOME") or joinp(home, ".config")
        return joinp(base, "noita-states")

    cfgdir = default_config_dir()
    configs = joinp(cfgdir, "noita-states-gui-config.json")
    cdata, newcon = fetch_config(configs)

    root = tkinter.Tk()
    root.title("Noita States GUI")
    root.resizable(False, False)

    def save_changes():
        try:
            if not os.path.exists(savesentry.get()):
                raise FileNotFoundError(f"Entered saves path doesn't exist: {savesentry.get()}")
            if not os.path.exists(backupentry.get()):
                raise FileNotFoundError(f"Entered backups path doesn't exist: {backupentry.get()}")
            edit_config(configs, savesentry.get(), backupentry.get(), exeentry.get())
            return True
        except Exception as e:
            traceback.print_exc()
            tkinter.messagebox.showerror("Error", str(e))
            return False

    def swap_page(pagen):
        if pagen == "config":
            if save_changes():
                page("manage")
        elif pagen == "manage":
            page("config")


    def page(pagename):
        for widget in root.winfo_children():
            widget.destroy()

        cdata, newcon = fetch_config(configs)

        tkinter.Label(text="Noita States", font=(("Arial", 20))).pack()
        tkinter.ttk.Separator().pack(fill=tkinter.X)
        if pagename == "config":
            global savesentry, backupentry, exeentry

            locationframe = tkinter.Frame()

            locationframe.grid_columnconfigure(1, weight=1)
            locationframe.grid_columnconfigure(2, weight=0)

            tkinter.Label(locationframe, text="Saves path").grid(column=1, columnspan=2, row=0, sticky="WE")

            savesentry = tkinter.Entry(locationframe, width=35)
            savesentry.insert([0], cdata.get('savespath', ''))
            savesentry.grid(column=1, row=1, sticky="WE")

            getlocation = tkinter.Button(locationframe, text="Pick", width=5, command=lambda:bring_picker(savesentry))
            getlocation.grid(column=2, row=1, sticky="WE")

            tkinter.Label(locationframe, text="Backups path").grid(column=1, columnspan=2, row=2, sticky="WE")

            backupentry = tkinter.Entry(locationframe, width=35)
            backupentry.insert([0], cdata.get('output', ''))
            backupentry.grid(column=1, row=3, sticky="WE")

            getloc = tkinter.Button(locationframe, text="Pick", width=5, command=lambda:bring_picker(backupentry))
            getloc.grid(column=2, row=3, sticky="WE")

            tkinter.Label(locationframe, text="Game executable" if sys.platform.startswith('win') else "Game execution command").grid(column=1, columnspan=2, row=4, sticky="WE")

            exeentry = tkinter.Entry(locationframe, width=35)
            exeentry.insert([0], cdata.get('noitaexe', ''))
            exeentry.grid(column=1, row=5, sticky="WE")

            getexe = tkinter.Button(locationframe, text="Pick", width=5, command=lambda:bring_picker(exeentry, "file"))
            getexe.grid(column=2, row=5, sticky="WE")

            locationframe.pack(fill=tkinter.BOTH, expand=True)

            manage = tkinter.Button(text="Save", font=(("Arial", 15, "bold")), command=lambda:swap_page(pagename))
            manage.config(command=None)
            manage.pack(expand=True, fill=tkinter.X)
        elif pagename == "manage":
            explorerframe = tkinter.Frame()
            
            explorerframe.grid_columnconfigure(1, weight=1, minsize=176)
            explorerframe.grid_columnconfigure(3, weight=1, minsize=176)

            noitabox = tkinter.Listbox(explorerframe, width=20)
            tkinter.Label(explorerframe, text="Noita").grid(column=1, row=0)
            tkinter.Label(explorerframe, text="Backups").grid(column=3, row=0)
            noitabox.grid(column=1, row=1, sticky="NSEW")
            
            tkinter.ttk.Separator(explorerframe, orient=tkinter.VERTICAL).grid(column=2, row=0, sticky="NS")
            
            backupbox = tkinter.Listbox(explorerframe, width=20)
            backupbox.grid(column=3, row=1, sticky="NSEW")

            def addfiles(widget, directory):
                try:
                    index = 1
                    files = [b for b in os.listdir(directory) if b.startswith('save') and (b[4:b.find('_')] if '_' in b else b[4:]).isdigit()]
                    for filey in files:
                        if not os.path.isfile(pjoin(directory, filey)):
                            widget.insert(index, filey)
                            index += 1
                except Exception as e:
                    traceback.print_exc()
                    tkinter.messagebox.showerror("Error", str(e))
                    swap_page(pagename)

            addfiles(noitabox, cdata.get("savespath"))
            addfiles(backupbox, cdata.get("output"))


            # variables
            global drag_data, target_widget
            target_widget = None
            drag_data = {"item": None, "source": None, "index": None}

            def on_press(event):
                widget = event.widget

                index = widget.nearest(event.y)
                drag_data["item"] = widget.get(index)
                drag_data["index"] = index
                drag_data["source"] = widget

                print()
                if widget == noitabox:
                    print("From: Noita")
                elif widget == backupbox:
                    print("From: Backups")

            def on_context(event):
                widget = event.widget

                index = widget.nearest(event.y)
                drag_data["item"] = widget.get(index)
                drag_data["index"] = index
                drag_data["source"] = widget

                print(drag_data)
                if widget == noitabox:
                    mode = "noita"
                elif widget == backupbox:
                    mode = "backups"

                context_menu = tkinter.Menu(root, tearoff=0)

                if mode == "noita":
                    context_menu.add_command(label="Backup", command=print)
                    context_menu.add_command(label="Clear", command=print)
                    context_menu.add_command(label="Prune", command=print)
                    context_menu.add_command(label="Purge", command=print)
                elif mode == "backups":
                    context_menu.add_command(label="Load", command=print)
                    context_menu.add_command(label="Rename", command=print)
                    context_menu.add_command(label="Remove", command=print)

                def disappear(temp):
                    context_menu.destroy()
                context_menu.bind("<Leave>", disappear)
                context_menu.post(event.x_root, event.y_root)

            def on_release(event):
                global drag_data
                if not drag_data["item"]:
                    return

                x, y = event.x_root, event.y_root
                target_widget = event.widget.winfo_containing(x, y)

                if target_widget in (noitabox, backupbox) and target_widget != drag_data["source"]:
                    #drag_data["source"].delete(drag_data["index"])
                    #target_widget.insert(tkinter.END, drag_data["item"])

                    if target_widget == noitabox:
                        logger.config(text=f"Loading {drag_data['item']} to (SLOT)")
                        shutil.copytree(pjoin(cdata.get("output"), drag_data['item']), pjoin(cdata.get("savespath"), drag_data['item']), copy_function=smart_copy, dirs_exist_ok=True)
                        logger.config(text=f"Loaded {drag_data['item']} to (SLOT)")
                    elif target_widget == backupbox:
                        logger.config(text=f"Backed up {drag_data['item']} as (VERSION)")
                        target_widget.insert(tkinter.END, drag_data["item"])

                drag_data = {"item": None, "source": None, "index": None}


            # events
            for lb in (noitabox, backupbox):
                lb.bind("<Button-1>", on_press)
                lb.bind("<Button-3>", on_context)
                lb.bind("<ButtonRelease-1>", on_release)


            explorerframe.pack(fill=tkinter.BOTH, expand=True)

            logger = tkinter.Label(root, text="Drag or right click the folders", font=(("Arial", 10)))
            logger.pack()
            
            tkinter.ttk.Separator().pack(fill=tkinter.X)
            
            if cdata.get("noitaexe", None):
                startgame = tkinter.Button(text="Start", font=(("Arial", 15, "bold")), command=lambda:start_noita(cdata.get("noitaexe")))
                startgame.pack(expand=True, fill=tkinter.X)


            configure = tkinter.Button(text="Configure", font=(("Arial", 15, "bold")), command=lambda:swap_page(pagename))
            configure.pack(expand=True, fill=tkinter.X)


    pagename = 'manage' if (not newcon and os.path.isdir(cdata.get('savespath', None)) and os.path.isdir(cdata.get('output', 'ask'))) else 'config'
    page(pagename)

    root.focus_force()
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('(Interrupt)')
    except Exception as e:
        raise
