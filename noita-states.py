import os, sys, shutil, hashlib, json, builtins, glob, subprocess


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
        print(f'Config file (noita-states-config.json) could not be read: {e}')
        newcon = True
        pass
    return data, newcon


def edit_config(configs, savespath, output, noitaexe='ask', defaultaction='play'):
    with open(configs, 'w', encoding='utf-8') as c:
        json.dump({'savespath': savespath, 'output': output, 'noitaexe': noitaexe, 'defaultaction': defaultaction}, c, indent=4)


def start_noita(noitaexe):
    if sys.platform.startswith('win'):
        subprocess.Popen([noitaexe], cwd=os.path.dirname(noitaexe) or None)
    else:
        subprocess.Popen(noitaexe, shell=True)


def work(*func):
    out = sys.stdout
    out.write('Working...')
    out.flush()
    try:
        for fu in func:
            fu()
    except Exception as e:
        out.write('\r\x1b[K')
        print(f'Failure: {e}')
        out.flush()
        return False
    out.write('\r\x1b[K')
    out.flush()
    return True


def main():
    savespath = 'ask'
    output = 'ask'
    
    pjoin = os.path.join
    cwd = os.getcwd()
    out = sys.stdout
    cmds = []
    autopath = True

    if sys.stdin.isatty() and 'idlelib' not in sys.modules:
        if not sys.platform.startswith('win'):
            import readline

            def complete(text, state):
                if autopath:
                    target = os.path.expanduser(text or './')
                    if target.endswith(':'):
                        target += '/'
                    raw = glob.glob(target + '*')
                    options = [m.replace('\\', '/') + ('/' if os.path.isdir(m) else '') for m in raw]
                else:
                    options = [c for c in cmds if c.startswith(text)]
                return options[state] if state < len(options) else None

            readline.set_completer_delims(' \t\n;')
            readline.parse_and_bind('tab: complete')
            readline.set_completer(complete)
        else:
            import msvcrt

            def win_input(prompt=''):
                sys.stdout.write(prompt)
                sys.stdout.flush()
                buffer = []
                matches, match_idx = [], 0
                tab_base = ''

                while True:
                    ch = msvcrt.getwch()
                    if ch in ('\r', '\n'):
                        print()
                        return ''.join(buffer)
                    elif ch in ('\x00', '\xe0'):
                        msvcrt.getwch()
                    elif ch == '\x08':
                        if buffer:
                            buffer.pop()
                            sys.stdout.write('\b \b')
                            sys.stdout.flush()
                        matches = []
                    elif ch == '\t':
                        if not matches:
                            tab_base = ''.join(buffer)
                            if autopath:
                                target = os.path.expanduser(tab_base or './')
                                if target.endswith(':'):
                                    target += '/'
                                raw = glob.glob(target + '*')
                                matches = [m.replace('\\', '/') + ('/' if os.path.isdir(m) else '') for m in raw]
                            else:
                                matches = [c for c in cmds if c.startswith(tab_base)]
                            match_idx = 0
                        if matches:
                            chosen = matches[match_idx % len(matches)]
                            match_idx += 1
                            sys.stdout.write('\b \b' * len(buffer) + chosen)
                            sys.stdout.flush()
                            buffer = list(chosen)
                            if len(matches) == 1 and chosen != tab_base:
                                matches = []
                    elif ch == '\x03':
                        raise KeyboardInterrupt
                    elif ord(ch) >= 32:
                        buffer.append(ch)
                        sys.stdout.write(ch)
                        sys.stdout.flush()
                        matches = []

            builtins.input = win_input

    configs = pjoin(cwd, 'noita-states-config.json')
    cdata, newcon = fetch_config(configs)

    noitaexe = cdata.get('noitaexe', None)
    noitaexe_saved = (not newcon) and bool(noitaexe) and noitaexe.lower() != 'ask'

    defaultaction = cdata.get('defaultaction', 'play')

    saves = []
    while True:
        autopath = True
        cmds = []
        savespath = cdata.get('savespath', None)
        if savespath is None or savespath.lower() == 'ask':
            savespath = input('Path to Noita saves (e.g. .../LocalLow/Nolla_Games_Noita): ').replace('"', '').replace('\\', '/')
        while True:
            if os.path.exists(savespath):
                saves = [n[4:n.find('_')] if '_' in n else n[4:] for n in os.listdir(savespath) if n.startswith('save') and (n[4:n.find('_')] if '_' in n else n[4:]).isdigit()]
            else:
                print("Path doesn't exist.")
                break
            if not saves:
                print('No valid save folder (e.g. "save00") could be found in the set Noita saves path.')
                autopath = False
                cmds = ['y', 'n']
                if input('Retry? (Y/n): ').lower().startswith('n'):
                    cdata.pop('savespath', None)
                    break
                continue
            break
        if saves:
            break

    while True:
        autopath = True
        cmds = []
        output = cdata.get('output', None)
        if output is None or output.lower() == 'ask':
            output = input('Path to output for backups (e.g. .../Noita/backup): ').replace('"', '').replace('\\', '/')
        if not os.path.exists(output):
            autopath = False
            cmds = ['y', 'n']
            if input("Path doesn't exist. Create? (y/N): ").lower().startswith('y'):
                os.makedirs(output, exist_ok=True)
            else:
                continue
        break

    autopath = False
    cmds = ['y', 'n']
    if newcon and not input('Save to config file? (Y/n): ').lower().startswith('n'):
        edit_config(configs, savespath, output, defaultaction=defaultaction)
        print()

    menu_map = {
        'play': 'Run Noita: play',
        '0': 'Quit: 0',
        '1': 'Backup: 1',
        '2': 'Load: 2',
        '3': 'Remove: 3',
        '4': 'Rename: 4',
        '5': 'List: 5',
        '6': 'Clear: 6',
        '7': 'Prune: 7',
        '8': 'Purge: 8',
    }
    for action, label in menu_map.items():
        if action == defaultaction:
            menu_map[action] = label + ' (or empty)'
    menu_map['play'] += f' ({noitaexe})' if noitaexe_saved else ''
    menu_sorted = {key:val for key,val in sorted(menu_map.items(), key=lambda item: item[0].isdigit())}
    menu_lines = menu_sorted.values()
    print('\n'.join(menu_lines))

    nam = {}
    firnam = []
    bc = {}
    bcv = {}
    firbc = []
    while True:
        autopath = False
        cmds = menu_sorted.keys()
        sect = input('> ')
        if not sect:
            out.write('\033[A\033[2C' + defaultaction + '\r\033[B')
            out.flush()
            sect = defaultaction

        if os.path.exists(savespath):
            saves = [n[4:n.find('_')] if '_' in n else n[4:] for n in os.listdir(savespath) if n.startswith('save') and (n[4:n.find('_')] if '_' in n else n[4:]).isdigit()]
            if not saves:
                print("Every save folders in Noita saves path have been removed or renamed.")
                continue
        else:
            print("Path to Noita saves has been removed or renamed.")
            continue

        if not os.path.exists(output):
            print("Path to output for backups has been removed or renamed.")
            continue

        if sect == '0':
            exit()

        elif sect == 'play':
            try:
                if not noitaexe or noitaexe.lower() == 'ask':
                    autopath = True
                    cmds = []
                    if sys.platform.startswith('win'):
                        noitaexe = input('Path to noita.exe: ').replace('"', '').replace('\\', '/')
                    else:
                        noitaexe = input('Command to run noita.exe: ')
                    noitaexe_saved = False

                if not noitaexe_saved:
                    autopath = False
                    cmds = ['y', 'n']
                    if not input('Save to config file? (Y/n): ').lower().startswith('n'):
                        edit_config(configs, savespath, output, noitaexe, defaultaction)
                        noitaexe_saved = True

                if work(lambda: start_noita(noitaexe)):
                    print('Running')
                else:
                    continue
            except KeyboardInterrupt:
                print('←')
                continue

        elif sect == '1':
            try:
                while True:
                    cmds = saves
                    savenum = input('[Backup] ('+', '.join([f'*{s}*' if s == saves[0] else s for s in saves])+'): ')
                    if not savenum: savenum = saves[0]
                    if savenum not in saves:
                        cand = [nu for nu in saves if nu==savenum or nu.endswith(savenum)]
                        if cand:
                            savenum = cand[0]
                        else:
                            print('No save slot with the given number exists.')
                            continue
                    break
                savetar = pjoin(savespath, 'save'+savenum)

                while True:
                    base_nam = 'save' + savenum
                    base_full = 'save' + savenum + ('_' + nam[savenum] if nam.get(savenum) else '')
                    mtchs = [b for b in os.listdir(output) if b == base_full or (b.startswith(base_full + '_') and b[len(base_full)+1:].isdigit())]
                    if not savenum in firnam or not mtchs:
                        bcs = [b.replace('save'+savenum+('_' if b.lower().startswith(('save'+savenum+'_').lower()) else ''), '') for b in os.listdir(output) if b.lower().startswith(('save'+savenum).lower())]
                        bcs = [(b[:b.rfind('_')] if '_' in b and b[b.rfind('_')+1:].isdigit() else (b if not b.isdigit() else '')) for b in bcs]
                        cmds = list(dict.fromkeys([b for b in bcs if b]))
                        nam[savenum] = input('Backup name (optional): ')
                    base_nam += ('_' + nam[savenum] if nam.get(savenum) else '')
                    base_low = base_nam.lower()
                    backups = [int(b[len(base_nam)+1:]) for b in os.listdir(output) if b.lower().startswith(base_low+'_') and b[len(base_nam)+1:].isdigit()]
                    bck = any(b.lower() == base_low for b in os.listdir(output))
                    savenam = base_nam + ('_' + str(max(backups)+1) if backups else ('_1' if bck else ''))
                    cmds = ['y', 'n']
                    if input('"'+savenam+'"? (Y/n): ').lower().startswith('n'):
                        if savenum in firnam:
                            firnam.remove(savenum)
                        continue
                    if not savenum in firnam: firnam.append(savenum)
                    break
                    
                outputtar = pjoin(output, savenam)

                if os.path.exists(outputtar):
                    cmds = ['y', 'n']
                    if not input(f'Backup folder "{savenam}" already exists. Overwrite? (y/N): ').lower().startswith('y'):
                        continue

                if work(lambda: shutil.copytree(savetar, outputtar, copy_function=smart_copy, dirs_exist_ok=True)):
                    print(f'Successfully made backup at "{outputtar}"')
                else:
                    continue
            except KeyboardInterrupt:
                print('←')
                continue

        elif sect in ('2', '3', '4', '8'):
            baacks = [n[4:n.find('_')] if '_' in n else n[4:] for n in os.listdir(output) if n.startswith('save') and (n[4:n.find('_')] if '_' in n else n[4:]).isdigit()]
            if not baacks:
                print("Path to output for backups has no save slots.")
                continue
            try:
                while True:
                    bcks = [(b.split('_')[0] if '_' in b else b)[4:] for b in os.listdir(output) if b.startswith('save') and (b[4:b.find('_')] if '_' in b else b[4:]).isdigit()]
                    backs = []
                    for b in bcks:
                        if b not in backs: backs.append(b)
                    cmds = backs
                    backnum = input(('[Load]' if sect=='2' else '[Remove]' if sect=='3' else '[Rename]' if sect=='4' else '[Purge]')+' ('+', '.join([f'*{s}*' if s == backs[0] else s for s in backs])+'): ')
                    if not backnum: backnum = backs[0]
                    if backnum not in backs:
                        cand = [nu for nu in backs if nu==backnum or nu.endswith(backnum)]
                        if cand:
                            backnum = cand[0]
                        else:
                            print('No save slot with the given number exists.')
                            continue
                    break
                
                while True:
                    backss = [b for b in os.listdir(output) if b.startswith('save') and b.split('_')[0][4:] == backnum]
                    askd = False
                    bpre_check = 'save' + backnum + ('_' + bc[backnum] if bc.get(backnum) else '')
                    mtchs = [b for b in os.listdir(output) if b == bpre_check or (b.startswith(bpre_check + '_') and b[len(bpre_check)+1:].isdigit())]
                    if (not backnum in firbc or sect != '2' or not mtchs) and len(backss) > 1:
                        askd = True
                        bcs = [b.replace('save'+backnum+('_' if b.startswith('save'+backnum+'_') else ''), '') for b in os.listdir(output) if b.startswith('save'+backnum)]
                        bcs = [(b[:b.rfind('_')] if '_' in b and b[b.rfind('_')+1:].isdigit() else (b if not b.isdigit() else '')) for b in bcs]
                        unique_names = list(dict.fromkeys(bcs))
                        if len(unique_names) == 1:
                            bc[backnum] = unique_names[0]
                            bpre = 'save'+backnum+('_'+bc[backnum] if bc.get(backnum) else '')
                            mtchs = [b for b in os.listdir(output) if b==bpre or (b.startswith(bpre+'_') and b[len(bpre)+1:].isdigit())]
                        else:
                            while True:
                                bcs = [b.replace('save'+backnum+('_' if b.startswith('save'+backnum+'_') else ''), '') for b in os.listdir(output) if b.startswith('save'+backnum)]
                                bcs = [(b[:b.rfind('_')] if '_' in b and b[b.rfind('_')+1:].isdigit() else (b if not b.isdigit() else '')) for b in bcs]
                                cmds = list(dict.fromkeys([b for b in bcs if b]))
                                bc[backnum] = input(f'Backup name (empty for first "save{backnum}" match): ')
                                bpre = 'save'+backnum+('_'+bc[backnum] if bc.get(backnum) else '')
                                mtchs = [b for b in os.listdir(output) if b==bpre or (b.startswith(bpre+'_') and b[len(bpre)+1:].isdigit())]
                                if not mtchs and not bc.get(backnum) and cmds:
                                    bc[backnum] = cmds[0]
                                    bpre = 'save'+backnum+'_'+bc[backnum]
                                    mtchs = [b for b in os.listdir(output) if b==bpre or (b.startswith(bpre+'_') and b[len(bpre)+1:].isdigit())]
                                    out.write(f'\033[A\033[{44+len(backnum)}C{cmds[0]}\r\033[B')
                                    out.flush()
                                if not mtchs:
                                    print('No match for "'+(bc.get(backnum) or 'save'+backnum)+'"')
                                    continue
                                break
                        cmds = sorted([(b.replace(bpre, '').lstrip('_') or '0') for b in mtchs], key=lambda x: int(x) if x.isdigit() else -1)
                        if sect != '8':
                            if len(mtchs) > 1:
                                bcv[backnum] = input('Version number (empty for last): ')
                            else:
                                bcv[backnum] = mtchs[0].replace(bpre, '').lstrip('_')
                    if len(backss) == 1:
                        rem = backss[0][len('save' + backnum):].lstrip('_')
                        if rem:
                            parts = rem.split('_')
                            if parts[-1].isdigit():
                                bcv[backnum] = parts[-1]
                                bc[backnum] = '_'.join(parts[:-1])
                            else:
                                bcv[backnum] = ''
                                bc[backnum] = rem
                        else:
                            bc[backnum] = ''
                            bcv[backnum] = ''
                    
                    bpre = 'save'+backnum+('_'+bc[backnum] if bc.get(backnum) else '')
                    mtchs = [b for b in os.listdir(output) if b==bpre or (b.startswith(bpre+'_') and b[len(bpre)+1:].isdigit())]

                    if sect != '8':
                        backnam = 'save'+backnum+('_'+bc[backnum] if bc.get(backnum) else '')
                        if bcv.get(backnum):
                            backnam += ('' if bcv[backnum] == '0' else '_'+bcv[backnum])
                        else:
                            backups = [int(b[len(backnam)+1:]) for b in os.listdir(output) if b.startswith(backnam+'_') and b[len(backnam)+1:].isdigit()]
                            ver = ('_'+str(max(backups)) if backups else '')
                            backnam += ver
                            if askd:
                                out.write(f'\033[A\033[33C{ver.replace("_","")}\r\033[B')
                                out.flush()
                        backtar = pjoin(output, backnam)

                    cmds = ['y', 'n']
                    if sect == '4':
                        print(f'Previous: "{backnam}"')
                    elif sect != '8':
                        if input('"'+backnam+'"? (Y/n): ').lower().startswith('n'):
                            if backnum in firbc:
                                firbc.remove(backnum)
                            continue
                    if not backnum in firbc and sect == '2': firbc.append(backnum)
                    break

                if sect == '2':
                    while True:
                        cmds = saves
                        slotnum = input('Load to save slot ('+', '.join([f'*{s}*' if s == backnum else s for s in saves])+'): ')
                        if not slotnum: slotnum = backnum
                        if slotnum not in saves:
                            cand = [nu for nu in saves if nu==slotnum or nu.endswith(slotnum)]
                            if cand:
                                slotnum = cand[0]
                            else:
                                print('No save slot with the given number exists.')
                                continue
                        break
                    savetar = pjoin(savespath, 'save'+slotnum)
                    if work(lambda: shutil.copytree(backtar, savetar, copy_function=smart_copy, dirs_exist_ok=True)):
                        print(f'Successfully loaded backup from "{backtar}" to "save{slotnum}"')
                    else:
                        continue
                    
                elif sect == '3':
                    if work(lambda: shutil.rmtree(backtar)):
                        print(f'Successfully removed backup at "{backtar}"')
                    else:
                        continue
                    
                elif sect == '4':
                    while True:
                        cmds = saves
                        slotres = input('New save slot number ('+', '.join([f'*{s}*' if s == backnum else s for s in saves])+'): ')
                        if not slotres: slotres = backnum
                        if slotres not in saves:
                            cand = [nu for nu in saves if nu==slotres or nu.endswith(slotres)]
                            if cand:
                                slotres = cand[0]
                            else:
                                print('No save slot with the given number exists.')
                                continue
                        baseres = 'save' + slotres
                        bcs = [b.replace('save'+backnum+('_' if b.lower().startswith(('save'+backnum+'_').lower()) else ''), '') for b in os.listdir(output) if b.lower().startswith(('save'+backnum).lower())]
                        bcs = [(b[:b.rfind('_')] if '_' in b and b[b.rfind('_')+1:].isdigit() else (b if not b.isdigit() else '')) for b in bcs]
                        cmds = list(dict.fromkeys([b for b in bcs if b]))
                        namres = input('Rename (empty to keep previous): ')
                        baseres += ('_' + namres if namres else ('_' + bc[backnum] if bc.get(backnum) else ''))
                        baselow = baseres.lower()
                        backups = [int(b[len(baseres)+1:]) for b in os.listdir(output) if b.lower().startswith(baselow+'_') and b[len(baseres)+1:].isdigit() and b != backnam]
                        bck = any(b.lower() == baselow for b in os.listdir(output))
                        mtchs_res = [b for b in os.listdir(output) if (b.lower() == baselow or (b.lower().startswith(baselow + '_') and b[len(baseres)+1:].isdigit())) and b.lower() != backnam.lower()]
                        cmds = sorted([(b.replace(baseres, '').lstrip('_') or '0') for b in mtchs_res], key=lambda x: int(x) if x.isdigit() else -1)
                        verres = input('Version number (empty for auto): ')
                        if verres:
                            backres = baseres + ('' if verres == '0' else '_' + verres)
                        else:
                            if not namres and slotres == backnum and bcv.get(backnum):
                                backres = baseres + ('' if bcv[backnum] == '0' else '_' + bcv[backnum])
                            else:
                                backres = baseres + ('_' + str(max(backups)+1) if backups else ('_1' if bck and baselow != backnam.lower() else ''))
                        
                        if os.path.exists(pjoin(output, backres)) and backres.lower() != backnam.lower():
                            print(f'Backup "{backres}" already exists.')
                            continue

                        cmds = ['y', 'n']
                        if input('"'+backres+'"? (Y/n): ').lower().startswith('n'):
                            continue
                        break
                    if work(lambda: os.rename(backtar, pjoin(output, backres))):
                        print(f'Successfully renamed backup previously at "{backtar}"')
                    else:
                        continue

                elif sect == '8':
                    cmds = ['y', 'n']
                    if input(f'"{bpre}" ({len(mtchs)} backup{"s" if len(mtchs)>1 else ""})? (y/N): ').lower().startswith('y'):
                        success = True
                        for m in mtchs:
                            if not work(lambda m=m: shutil.rmtree(pjoin(output, m))):
                                success = False
                        if success:
                            print(f'Successfully purged backup(s) for "{bpre}"')
                        else:
                            continue
            except KeyboardInterrupt:
                print('←')
                continue

        elif sect == '5':
            try:
                baacks = [n+f' ({", ".join(sorted(os.listdir(pjoin(output, n)), key=lambda k: k.count(".")))})' for n in os.listdir(output) if n.startswith('save') and (n[4:n.find('_')] if '_' in n else n[4:]).isdigit()]
                saaves = [n+f' ({", ".join(sorted(os.listdir(pjoin(savespath, n)), key=lambda k: k.count(".")))})' for n in os.listdir(savespath) if n.startswith('save') and (n[4:n.find('_')] if '_' in n else n[4:]).isdigit()]
                cmds = ['b', 's']
                print('\n'.join(baacks if not input('Backups or saves? (B/s): ').lower().startswith('s') else saaves))
            except KeyboardInterrupt:
                print('←')
                continue

        elif sect == '6':
            try:
                while True:
                    cmds = saves
                    savenum = input('[Clear] ('+', '.join([f'*{s}*' if s == saves[0] else s for s in saves])+'): ')
                    if not savenum: savenum = saves[0]
                    if savenum not in saves:
                        cand = [nu for nu in saves if nu==savenum or nu.endswith(savenum)]
                        if cand:
                            savenum = cand[0]
                        else:
                            print('No save slot with the given number exists.')
                            continue
                    break
                savetar = pjoin(savespath, 'save'+savenum)

                cmds = ['y', 'n']
                if not input(f'Clear "save{savenum}"? (y/N): ').lower().startswith('y'):
                    continue

                def clear_save():
                    for item in os.listdir(savetar):
                        if item == 'persistent':
                            continue
                        item_path = pjoin(savetar, item)
                        if os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                        else:
                            os.remove(item_path)

                if work(clear_save):
                    print(f'Successfully cleared save at "{savetar}"')
                else:
                    continue
            except KeyboardInterrupt:
                print('←')
                continue

        elif sect == '7':
            baacks = [n[4:n.find('_')] if '_' in n else n[4:] for n in os.listdir(output) if n.startswith('save') and (n[4:n.find('_')] if '_' in n else n[4:]).isdigit()]
            if not baacks:
                print("Path to output for backups has no save slots.")
                continue
            try:
                while True:
                    bcks = [(b.split('_')[0] if '_' in b else b)[4:] for b in os.listdir(output) if b.startswith('save') and (b[4:b.find('_')] if '_' in b else b[4:]).isdigit()]
                    backs = []
                    for b in bcks:
                        if b not in backs: backs.append(b)
                    cmds = backs
                    backnum = input('[Prune] ('+', '.join([f'*{s}*' if s == backs[0] else s for s in backs])+'): ')
                    if not backnum: backnum = backs[0]
                    if backnum not in backs:
                        cand = [nu for nu in backs if nu==backnum or nu.endswith(backnum)]
                        if cand:
                            backnum = cand[0]
                        else:
                            print('No save slot with the given number exists.')
                            continue
                    break

                bcs = [b.replace('save'+backnum+('_' if b.lower().startswith(('save'+backnum+'_').lower()) else ''), '') for b in os.listdir(output) if b.lower().startswith(('save'+backnum).lower())]
                bcs = [(b[:b.rfind('_')] if '_' in b and b[b.rfind('_')+1:].isdigit() else (b if not b.isdigit() else '')) for b in bcs]
                unique_names = list(dict.fromkeys(bcs))
                cmds = list(dict.fromkeys([b for b in bcs if b]))

                asked_bc_name = False
                if len(unique_names) == 1:
                    bc_name = unique_names[0]
                else:
                    asked_bc_name = True
                    bc_name = input('Backup name (empty for all): ')

                to_prune = []

                if asked_bc_name and not bc_name:
                    backss = [b for b in os.listdir(output) if b.startswith('save') and b.split('_')[0][4:] == backnum]

                    groups = {}
                    for b in backss:
                        parts = b.split('_')
                        if len(parts) > 1 and parts[-1].isdigit():
                            base = '_'.join(parts[:-1])
                        else:
                            base = b
                        groups.setdefault(base, []).append(b)

                    for base, items in groups.items():
                        if len(items) > 1:
                            sorted_items = sorted(
                                items,
                                key=lambda x: (
                                    int(x.rpartition('_')[2]) if x.rpartition('_')[2].isdigit() else 0,
                                    os.path.getmtime(pjoin(output, x))
                                )
                            )
                            to_prune.extend(sorted_items[:-1])
                else:
                    bpre = 'save' + backnum + ('_' + bc_name if bc_name else '')
                    mtchs = [b for b in os.listdir(output) if b == bpre or (b.startswith(bpre + '_') and b[len(bpre)+1:].isdigit())]
                    if not mtchs:
                        print('No match for "' + bc_name + '"')
                        continue

                    if len(mtchs) > 1:
                        cmds = sorted([(b.replace(bpre, '').lstrip('_') or '0') for b in mtchs], key=lambda x: int(x) if x.isdigit() else -1)
                        ver_num = input('Version number to prune older than (empty for last): ')

                        if not ver_num:
                            digit_vers = [int(v) for v in cmds if v.isdigit()]
                            target_ver = max(digit_vers) if digit_vers else 0
                            out.write(f'\033[A\033[53C{target_ver}\r\033[B')
                            out.flush()
                        else:
                            target_ver = int(ver_num) if ver_num.isdigit() else 0

                        for b in mtchs:
                            v_str = b.replace(bpre, '').lstrip('_') or '0'
                            v_int = int(v_str) if v_str.isdigit() else 0
                            if v_int < target_ver:
                                to_prune.append(b)

                if not to_prune:
                    print(f'No old backup versions to prune for "save{backnum}".')
                    continue

                print(f'Backups to delete: {", ".join(to_prune)}')
                cmds = ['y', 'n']
                if not input(f'Prune {len(to_prune)} old backup(s) for "save{backnum}"? (y/N): ').lower().startswith('y'):
                    continue

                def do_prune():
                    for folder in to_prune:
                        shutil.rmtree(pjoin(output, folder))

                if work(do_prune):
                    print(f'Successfully pruned {len(to_prune)} old backup(s) for "save{backnum}"')
                else:
                    continue
            except KeyboardInterrupt:
                print('←')
                continue


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('(Interrupt)')
    except Exception as e:
        raise
