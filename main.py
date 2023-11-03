import zipfile
import os
import shutil
import adjnoun
import json
from tqdm import tqdm
import format

with open('./config.json') as config_json:
    config = json.load(config_json)

def zip_folder(folder_path, output_path):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname=arcname)

    return

unanonymize = {}

config['numberDiffs'] = int(config['numberDiffs'])

HOME = os.getcwd()
maps = os.path.join(HOME, 'maps.zip')
unzip = os.path.join(HOME, 'unzip')
oszs = os.path.join(HOME, 'oszs')
tozip = os.path.join(HOME, 'tozip')
decode = os.path.join(HOME, 'decode.json')
outdir = os.path.join(HOME, 'output')

if os.path.exists(outdir):
    shutil.rmtree(outdir)
if os.path.exists(unzip):
    shutil.rmtree(unzip)
if os.path.exists(oszs):
    shutil.rmtree(oszs)
if os.path.exists(tozip):
    shutil.rmtree(tozip)
if os.path.exists(decode):
    os.remove(decode)
if os.path.exists('./anonmaps.zip'):
    os.remove('./anonmaps.zip')

os.mkdir(unzip)
os.mkdir(oszs)
os.mkdir(tozip)

with zipfile.ZipFile(maps, "r") as zip_ref:
    zip_ref.extractall(unzip)

extr = os.listdir(unzip)
for file in extr:
    os.mkdir(os.path.join(oszs, file))
    with zipfile.ZipFile(os.path.join(unzip, file), 'r') as t_zip:
        t_zip.extractall(os.path.join(oszs, file))

oszf = os.listdir(oszs)
print('Anonymizing .osz files')
for folder in tqdm(oszf):
    newName = adjnoun.get()
    allfiles = [x for x in os.listdir(os.path.join(oszs, folder))]
    for file in allfiles:
        if file.endswith('.osb'):
            os.remove(os.path.join(oszs, folder, file))
        if os.path.isdir(os.path.join(oszs, folder, file)):
            shutil.rmtree(os.path.join(oszs, folder, file))
    oslist = [x for x in os.listdir(os.path.join(oszs, folder)) if x.endswith('.osu')]
    imlist = [x for x in os.listdir(os.path.join(oszs, folder)) if x.endswith(('.jpg', '.png'))]
    audiolist = [x for x in os.listdir(os.path.join(oszs, folder)) if x.endswith(('.ogg', '.mp3'))]
    if len(oslist) != config['numberDiffs']:
        print('Error: %s includes wrong number of .osu files' % folder)
        continue
    ctr = 0
    newName = adjnoun.get()
    for file in oslist:
        tow = []
        with open(os.path.join(oszs, folder, file), encoding='utf8') as f:
            lines = [line.rstrip() for line in f]
        for line in lines:
            repl = False
            if line.startswith('Creator'):
                unanonymize[newName] = line[8:]
                repl = 'Creator: Anonymous'
            elif line.startswith('TimelineZoom'):
                repl = 'TimelineZoom: 2.6'
            elif line.startswith('GridSize'):
                repl = 'GridSize: 64'
            elif line.startswith('Tags:'):
                repl = 'Tags:'
            elif line.startswith('Version:'):
                repl = 'Version: ' + newName
                if len(oslist) > 1:
                    repl += ' ' + str(ctr+1)
                    ctr+=1
            elif line.startswith('Source'):
                repl = 'Source:'
            elif line.startswith('0,0,"'):
                bg = line.split(',')[2]
                bg = bg.replace('"', '')
                ext = bg[-4:]
                splt = line.split(',')
                repl = splt[0]+','+splt[1]+','+'"bg'+ext+'",'+splt[3]+','+splt[4]
                nname = 'bg'+ext
                bgp = os.path.join(oszs, folder, bg)
                try:
                    os.rename(bgp, os.path.join(oszs, folder, nname))
                except FileNotFoundError:
                    pass
            elif line.startswith("BeatmapID"):
                repl = 'BeatmapID:0'
            elif line.startswith('BeatmapSetID'):
                repl = 'BeatmapSetID:-1'
            elif line.startswith('Bookmarks'):
                repl = 'Bookmarks:'
            elif len(line.split(',')) == 6:
                repl = '256,192,'+','.join(line.split(',')[2:])
            elif len(line.split(',')) == 7:
                repl = '256,192,' + ','.join(line.split(',')[2:])
            if repl:
                tow.append(repl+'\n')
            else:
                tow.append(line+'\n')
        if len(oslist) > 1:
            fntosave = os.path.join(oszs, folder, 'beatmap (' + newName + str(ctr) + ').osu')
        else:
            fntosave = os.path.join(oszs, folder, 'beatmap (' + newName + ').osu')
        f = open(fntosave, "a", encoding='utf8')
        f.writelines(tow)
        f.close()
        os.remove(os.path.join(oszs, folder, file))


    #remove all images except background, assuming 1 bg for all diffs
    for im in imlist:
        if im == bg:
            continue
        else:
            os.remove(os.path.join(oszs, folder, im))

    toz = os.path.join(oszs, folder)
    outn = config['tournamentName'] + ' (' + newName+').osz'
    ouz = os.path.join(tozip, outn)
    zip_folder(toz, ouz)


shutil.rmtree(unzip)

with open('decode.json', 'w') as decode_json:
    json.dump(unanonymize, decode_json)


zip_folder(tozip, os.path.join(HOME, 'anonmaps.zip'))
success = format.formatMask(HOME)

shutil.rmtree(tozip)
shutil.rmtree(oszs)

os.mkdir(outdir)
os.rename('./anonmaps.zip', os.path.join(outdir, 'anonmaps.zip'))
os.rename('./masking.csv', os.path.join(outdir, 'masking.csv'))





if success:
    print('Yay your entries are now anonymized, apart from the ones listed above that failed')
else:
    print('Oops I did a fucky wucky')