import os, sys, shutil, json


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
    if not os.path.isfile(configs):
        configs = open(configs, 'x').name
    with open(configs, 'w') as c:
        c.write('{\n   '+'"savespath":"'+savespath+'",\n   "output":"'+output+'"'+'\n}')


def work(*func):
    out = sys.stdout
    out.write('Working...')
    out.flush()
    try:
        for fu in func:
            fu()
    except Exception as e:
        out.write('\r\x1b[K')
        print('Failure: '+e)
        out.flush()
        return False
    out.write('\r\x1b[K')
    print('Success')
    out.flush()
    return True


def main():
    #CONFIGURATION
    savespath = 'ask'
    output = 'ask'
    
    pjoin = os.path.join
    cwd = os.getcwd()

    configs = pjoin(cwd, 'noita-states-config.json')
    cdata, newcon = fetch_config(configs)

    saves = []
    while True:
        savespath = cdata.get('savespath', None)
        if savespath is None or savespath.lower() == 'ask':
            savespath = input('Path to Noita saves (e.g. .../LocalLow/Nolla_Games_Noita): ').replace('"', '').replace('\\', '/')
        saves = [n[4:] for n in os.listdir(savespath) if n.startswith('save') and n[4:].isdigit()]
        if not saves:
            print('No valid save folder (e.g. "save00") could be found in the set Noita saves path. Try loading new world first.')
            if input('Retry? (Y/n): ').startswith('n'):
                cdata.pop('savespath')
        else:
            break
    output = cdata.get('output', None)
    if output is None or output.lower() == 'ask':
        output = input('Path to output for backups (e.g. .../Noita/backup): ').replace('"', '').replace('\\', '/')

    if newcon and not input('Save to config file? (Y/n): ').startswith('n'):
        edit_config(configs, savespath, output)
        print()

    print('''Backup: 0
Load: 1''')

    nam = ''
    firnam = True
    bc = ''
    bcv = ''
    firbc = True
    while True:
        sect = input('> ')
        
        if sect == '0' or not sect:
            try:
                savenum = input('[Backup] ('+', '.join(saves)+'): ')
                if not savenum: savenum = "00"
                savetar = pjoin(savespath, 'save'+savenum)

                while True:
                    savenam = 'save'+savenum
                    if firnam:
                        nam = input('Backup name (optional): ')
                    savenam += ('_'+nam if nam else '')
                    backups = [int(b[len(savenam)+1:]) for b in os.listdir(output) if savenam in b and b[len(savenam)+1:].isdigit()]
                    bck = savenam in os.listdir(output)
                    savenam += ('_'+str(max(backups)+1) if backups else ('_1' if bck else ''))
                    if input('"'+savenam+'"? (Y/n): ').startswith('n'):
                        firnam = True
                        continue
                    firnam = False
                    break
                    
                outputtar = pjoin(output, savenam)

                if not work(lambda: shutil.copytree(savetar, outputtar, dirs_exist_ok=True)):
                    continue
            except KeyboardInterrupt:
                print()
                continue

        elif sect == '1':
            try:
                backnum = input('[Load] ('+', '.join(saves)+'): ')
                if not backnum: backnum = "00"
                savetar = pjoin(savespath, 'save'+backnum)
                
                while True:
                    backnam = 'save'+backnum
                    if firbc:
                        while True:
                            bc = input('Backup name (optional): ')
                            mtchs = [b for b in os.listdir(output) if ('_'+bc if bc else 'save'+backnum) in b]
                            if not mtchs:
                                print('No match for "'+(bc if bc else 'save'+backnum)+'"')
                                continue
                            bc = mtchs[0].replace('save'+backnum+('_' if mtchs[0].startswith('save'+backnum+'_') else ''), '')
                            break
                        bcv = input('Version number (empty for last): ')
                    backnam += ('_'+bc+('_'+bcv if bcv and bcv!='0' else '') if bc else '')
                    if not bcv:
                        backups = [int(b[len(backnam)+1:]) for b in os.listdir(output) if backnam in b and b[len(backnam)+1:].isdigit()]
                        backnam += ('_'+str(max(backups)) if backups else '')
                    if input('"'+backnam+'"? (Y/n): ').startswith('n'):
                        firnam = True
                        continue
                    firnam = False
                    break

                backtar = pjoin(output, backnam)

                if not work(lambda: shutil.copytree(backtar, savetar, dirs_exist_ok=True)):
                    continue
            except KeyboardInterrupt:
                print()
                continue
        
    


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        input(e)
