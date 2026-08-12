import os, sys, shutil, json, builtins, glob


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


def edit_config(configs, savespath, output):
    with open(configs, 'w', encoding='utf-8') as c:
        json.dump({'savespath': savespath, 'output': output}, c, indent=4)


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

    saves = []
    while True:
        autopath = True
        cmds = []
        savespath = cdata.get('savespath', None)
        if savespath is None or savespath.lower() == 'ask':
            savespath = input('Path to Noita saves (e.g. .../LocalLow/Nolla_Games_Noita): ').replace('"', '').replace('\\', '/')
        while True:
            if os.path.exists(savespath):
                saves = [n[4:] for n in os.listdir(savespath) if n.startswith('save') and n[4:].isdigit()]
            else:
                print("Path doesn't exist.")
                break
            if not saves:
                print('No valid save folder (e.g. "save00") could be found in the set Noita saves path.')
                autopath = False
                cmds = ['y', 'n']
                if input('Retry? (Y/n): ').startswith('n'):
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
            if input("Path doesn't exist. Create? (y/N): ").startswith('y'):
                os.makedirs(output, exist_ok=True)
            else:
                continue
        break

    autopath = False
    cmds = ['y', 'n']
    if newcon and not input('Save to config file? (Y/n): ').startswith('n'):
        edit_config(configs, savespath, output)
        print()

    print('''Backup: 0 (or empty)
Load: 1
Remove: 2
Quit: 3''')

    nam = {}
    firnam = []
    bc = {}
    bcv = {}
    firbc = []
    while True:
        autopath = False
        cmds = ['0', '1', '2']
        sect = input('> ')

        if os.path.exists(savespath):
            saves = [n[4:] for n in os.listdir(savespath) if n.startswith('save') and n[4:].isdigit()]
            if not saves:
                print("Every save folders in Noita saves path have been removed or renamed.")
                continue
        else:
            print("Path to Noita saves has been removed or renamed.")
            continue

        if not os.path.exists(output):
            print("Path to output for backups has been removed or renamed.")
            continue
        
        if sect == '0' or not sect:
            if not sect:
                out.write('\033[A\033[2C0\r\033[B')
                out.flush()
            try:
                while True:
                    cmds = saves
                    savenum = input('[Backup] ('+', '.join(saves)+'): ')
                    if not savenum: savenum = saves[0]
                    if savenum not in saves:
                        cand = [nu for nu in saves if nu==savenum or nu.endswith(savenum)]
                        if cand:
                            savenum = cand[0]
                        else:
                            print('No save slot with the given number exists.')
                    break
                savetar = pjoin(savespath, 'save'+savenum)

                while True:
                    savenam = 'save'+savenum
                    if not savenum in firnam:
                        nams = [b.replace('save'+savenum+('_' if b.startswith('save'+savenum+'_') else ''), '') for b in os.listdir(output) if b.startswith('save'+savenum)]
                        nams = [(b[:b.index('_')] if '_' in b else b) for b in nams if b]
                        cmds = nams
                        nam[savenum] = input('Backup name (optional): ')
                    savenam += ('_'+nam[savenum] if nam[savenum] else '')
                    backups = [int(b[len(savenam)+1:]) for b in os.listdir(output) if savenam in b and b[len(savenam)+1:].isdigit()]
                    bck = savenam in os.listdir(output)
                    savenam += ('_'+str(max(backups)+1) if backups else ('_1' if bck else ''))
                    cmds = ['y', 'n']
                    if input('"'+savenam+'"? (Y/n): ').startswith('n'):
                        if savenum in firnam:
                            firnam.remove(savenum)
                        continue
                    if not savenum in firnam: firnam.append(savenum)
                    break
                    
                outputtar = pjoin(output, savenam)

                if work(lambda: shutil.copytree(savetar, outputtar, dirs_exist_ok=True)):
                    print(f'Successfully made backup at "{outputtar}"')
                else:
                    continue
            except KeyboardInterrupt:
                print('←')
                continue

        elif sect in ('1', '2'):
            try:
                while True:
                    bcks = [(b.split('_')[0] if '_' in b else b).replace('save','') for b in os.listdir(output)]
                    backs = []
                    for b in bcks:
                        if b not in backs: backs.append(b)
                    cmds = backs
                    backnum = input(('[Load]' if sect=='1' else '[Remove]')+' ('+', '.join(backs)+'): ')
                    if not backnum: backnum = backs[0]
                    if backnum not in backs:
                        cand = [nu for nu in backs if nu==backnum or nu.endswith(backnum)]
                        if cand:
                            backnum = cand[0]
                        else:
                            print('No save slot with the given number exists. Retry.')
                            continue
                    break
                
                while True:
                    if not backnum in firbc:
                        while True:
                            bcs = [b.replace('save'+backnum+('_' if b.startswith('save'+backnum+'_') else ''), '') for b in os.listdir(output) if b.startswith('save'+backnum)]
                            bcs = [(b[:b.rfind('_')] if '_' in b and b[b.rfind('_')+1:].isdigit() else (b if not b.isdigit() else '')) for b in bcs]
                            cmds = list(dict.fromkeys([b for b in bcs if b]))
                            bc[backnum] = input('Backup name (optional): ')
                            bpre = 'save'+backnum+('_'+bc[backnum] if bc[backnum] else '')
                            mtchs = [b for b in os.listdir(output) if b==bpre or (b.startswith(bpre+'_') and b[len(bpre)+1:].isdigit())]
                            if not mtchs and not bc[backnum] and cmds:
                                bc[backnum] = cmds[0]
                                bpre = 'save'+backnum+'_'+bc[backnum]
                                mtchs = [b for b in os.listdir(output) if b==bpre or (b.startswith(bpre+'_') and b[len(bpre)+1:].isdigit())]
                            if not mtchs:
                                print('No match for "'+(bc[backnum] if bc[backnum] else 'save'+backnum)+'"')
                                continue
                            break
                        cmds = sorted([(b.replace(bpre, '').lstrip('_') or '0') for b in mtchs], key=lambda x: int(x) if x.isdigit() else -1)
                        bcv[backnum] = input('Version number (empty for last): ')
                    backnam = 'save'+backnum+('_'+bc[backnum] if bc[backnum] else '')
                    if bcv[backnum]:
                        backnam += ('' if bcv[backnum] == '0' else '_'+bcv[backnum])
                    else:
                        backups = [int(b[len(backnam)+1:]) for b in os.listdir(output) if b.startswith(backnam+'_') and b[len(backnam)+1:].isdigit()]
                        backnam += ('_'+str(max(backups)) if backups else '')
                    cmds = ['y', 'n']
                    if input('"'+backnam+'"? (Y/n): ').startswith('n'):
                        if backnum in firbc:
                            firbc.remove(backnum)
                        continue
                    if not backnum in firbc: firbc.append(backnum)
                    break

                backtar = pjoin(output, backnam)

                if sect == '1':
                    while True:
                        cmds = saves
                        slotnum = input('Load to save slot ('+', '.join(saves)+'): ')
                        if not slotnum: slotnum = backnum
                        if slotnum not in saves:
                            cand = [nu for nu in saves if nu==slotnum or nu.endswith(slotnum)]
                            if cand:
                                slotnum = cand[0]
                            else:
                                print('No save slot with the given number exists. Retry.')
                                continue
                        break
                    savetar = pjoin(savespath, 'save'+slotnum)
                    if work(lambda: shutil.copytree(backtar, savetar, dirs_exist_ok=True)):
                        print(f'Successfully loaded backup at "{backtar}"')
                    else:
                        continue
                else:
                    if work(lambda: shutil.rmtree(backtar)):
                        print(f'Successfully removed backup at "{backtar}"')
                    else:
                        continue
            except KeyboardInterrupt:
                print('←')
                continue

        elif sect == '3':
            exit()
        
    


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        raise
