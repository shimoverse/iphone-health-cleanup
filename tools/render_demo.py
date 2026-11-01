# SPDX-License-Identifier: GPL-3.0-or-later
"""Render a fully synthetic, explicitly labeled workflow illustration.

This is an illustrated storyboard, not a capture of an assistant or device UI.
Requires Pillow and ffmpeg. No phone, account or network access.
"""
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont

import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, required=True, help='Output folder outside the public source checkout')
OUT = parser.parse_args().out
OUT.mkdir(parents=True, exist_ok=True)
W, H, S = 1440, 900, 2
PAPER, INK, MUTED = '#F5F4ED', '#1E342E', '#65766F'
GREEN, PALE, LINE, ORANGE = '#21654C', '#E8EFE8', '#DCE3DA', '#A45426'
FONT = Path('/System/Library/Fonts/Supplemental')

def font(n, bold=False, serif=False):
    name = 'Georgia.ttf' if serif else ('Arial Bold.ttf' if bold else 'Arial.ttf')
    return ImageFont.truetype(str(FONT / name), n*S)

def scene(index, title, subtitle):
    im = Image.new('RGB', (W*S,H*S), PAPER)
    d = ImageDraw.Draw(im)
    def rect(box, fill, radius=20, outline=None):
        d.rounded_rectangle(tuple(int(v*S) for v in box), radius*S, fill=fill, outline=outline, width=2*S)
    def text(x,y,s,n=26,c=INK,bold=False,serif=False):
        d.text((int(x*S),int(y*S)),s,font=font(n,bold,serif),fill=c,spacing=10*S)
    text(54,31,'PHONE HEALTH & CLEANUP',22,GREEN,True)
    text(817,34,'ILLUSTRATED DEMO  /  FICTIONAL APPS',19,MUTED,True)
    text(54,84,title,46,INK,serif=True)
    text(56,150,subtitle,25,MUTED)
    # A phone-shaped illustration, deliberately not a native screenshot.
    rect((54,208,423,779),'#DCE4DA',35)
    rect((65,219,412,768),'#FFFFFF',29)
    rect((170,232,307,241),INK,4)
    text(92,265,'Sample mirrored phone',22,GREEN,True)
    text(92,308,'Apps & saved data',27,INK,True)
    apps = [('Example Game','Offloaded'),('Example Trial','Offloaded'),('Example Travel','Offloaded'),('Example Wallet','Protected'),('Authenticator','Protected')]
    removed = index >= 6
    y = 369
    for name,status in apps:
        if removed and name in {'Example Game','Example Trial'}:
            continue
        rect((87,y,390,y+62),PALE if status=='Protected' else '#F4F5F1',10)
        text(99,y+7,name,23,INK,True)
        text(99,y+36,status,18,GREEN if status=='Protected' else MUTED)
        y += 73
    rect((469,208,1386,779),'#FFFFFF',25)
    for i in range(7):
        rect((54+i*191,812,230+i*191,819),GREEN if i <= index else LINE,3)
    text(54,844,f'{index+1:02d} / 07',21,GREEN,True)
    text(199,844,'Illustration only. No phone is connected. No speed or space claim.',21,MUTED)
    return im,d,rect,text

def table(rect,text,travel='Delete',approved=False):
    text(502,247,'APP',19,MUTED,True);text(916,247,'DECISION',19,MUTED,True)
    rows=[('Example Game','Delete'),('Example Trial','Delete'),('Example Travel',travel),('Example Wallet','Keep'),('Authenticator','Keep')]
    for i,(n,a) in enumerate(rows):
        y=290+i*69
        rect((496,y,1358,y+60), '#F0F5EF' if a=='Keep' else '#FAF5ED',10)
        text(512,y+17,n,25,INK,True)
        text(928,y+17,a,25,GREEN if a=='Keep' else ORANGE,True)
    text(504,658,'Saved local data is deleted with the app.',24,ORANGE)
    if approved:
        rect((502,706,1351,757),GREEN,12);text(527,718,'Approve these 2 apps and their local data',24,'#FFFFFF',True)
    else:
        text(504,711,'Nothing is deleted at this stage.',24,MUTED)

images=[]
specs=[
 ('Start with an ordinary request','A local assistant uses the installed skill. No special prompt to remember.'),
 ('Choose how to connect','Mirroring for supported screen steps. Trusted USB for included scripts.'),
 ('Inspect before changing anything','Check storage, battery and the task that feels slow. Mark gaps clearly.'),
 ('Review the exact app list','Recommendations come first. Sensitive and uncertain apps stay kept.'),
 ('Change any recommendation','You can keep a recommended app before approving the final list.'),
 ('Approve a specific batch','In this example, only Game and Trial are approved, including local data.'),
 ('Verify, then report what happened','Check removals and retained apps. Measure space and speed separately.')]
for i,(title,subtitle) in enumerate(specs):
    im,d,rect,text=scene(i,title,subtitle)
    if i==0:
        text(508,256,'You ask',22,GREEN,True)
        text(506,311,'“My phone is slow.\nCheck its health and help\nme make some space.”',42,INK,serif=True)
        rect((503,535,1352,673),PALE,18)
        text(531,560,'The skill supplies the workflow.',28,INK,True)
        text(531,610,'Your approval controls the deletion list.',25,MUTED)
        text(507,714,'Public source: iPhone + Android modules',23,GREEN,True)
    elif i==1:
        for y,label,detail in [(252,'iPhone Mirroring','Keep the iPhone nearby and locked.'),(410,'Trusted USB','Use the included inventory and cleanup scripts.')]:
            rect((502,y,1352,y+137),PALE,18);text(529,y+20,label,31,GREEN,True);text(529,y+76,detail,25,INK)
        text(506,600,'USB read-only checks generally allow phone use.',24,INK)
        text(506,650,'Keep the phone idle during approved changes.',24,INK)
        text(506,712,'Mirroring requires reliable screen controls.',24,ORANGE)
    elif i==2:
        for y,label,detail in [(253,'Storage','What uses space? What can be recovered?'),(392,'Battery & lag','What is observed? What remains unknown?'),(531,'Evidence coverage','Complete inventory, or clearly marked partial?')]:
            rect((502,y,1352,y+116),PALE,16);text(527,y+17,label,29,GREEN,True);text(527,y+63,detail,24,INK)
        text(506,705,'Read-only inspection. No cleanup yet.',25,GREEN,True)
    elif i==3: table(rect,text)
    elif i==4:
        table(rect,text,travel='Keep: your override')
        rect((492,424,1362,489),'#EEF4E8',12,GREEN)
        text(512,443,'Example Travel',25,INK,True);text(928,443,'Keep: your override',25,GREEN,True)
    elif i==5:
        table(rect,text,travel='Keep: your override',approved=True)
    else:
        text(506,249,'ILLUSTRATIVE RESULT',20,GREEN,True)
        for y,label,detail in [(295,'2 sample apps removed','Game and Trial only. Check each result.'),(428,'Protected apps retained','Wallet, Authenticator and Travel stay.'),(561,'No invented benefit','Device-wide space and lag need measurement.')]:
            rect((502,y,1352,y+115),PALE,16);text(528,y+18,label,29,GREEN,True);text(528,y+68,detail,24,INK)
        text(506,714,'github.com/shimoverse/iphone-health-cleanup',24,GREEN,True)
    images.append(im.resize((W,H),Image.Resampling.LANCZOS))

with tempfile.TemporaryDirectory(prefix='phone-storyboard-') as td:
    td=Path(td)
    for i,im in enumerate(images): im.save(td/f'scene-{i}.png')
    durations=[4,5,4,5,4,5,5]
    concat=''.join(f"file '{td/f'scene-{i}.png'}'\nduration {dur}\n" for i,dur in enumerate(durations))
    concat+=f"file '{td/'scene-6.png'}'\n"
    (td/'frames.txt').write_text(concat)
    common=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(td/'frames.txt')]
    subprocess.run(common+['-t',str(sum(durations)),'-vf','fps=10,format=yuv420p','-c:v','libx264','-crf','18','-movflags','+faststart',str(OUT/'phone-cleanup-demo.mp4')],check=True)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(OUT/'phone-cleanup-demo.mp4'),'-vf','fps=8,scale=1200:-1:flags=lanczos,palettegen=stats_mode=diff',str(td/'palette.png')],check=True)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(OUT/'phone-cleanup-demo.mp4'),'-i',str(td/'palette.png'),'-lavfi','fps=8,scale=1200:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=sierra2_4a:diff_mode=rectangle','-loop','0',str(OUT/'phone-cleanup-demo.gif')],check=True)

images[4].save(OUT/'phone-cleanup-demo-poster.png')
sheet=Image.new('RGB',(1440,3*450),PAPER)
for n,i in enumerate([0,1,2,3,4,6]):
    sheet.paste(images[i].resize((720,450),Image.Resampling.LANCZOS),((n%2)*720,(n//2)*450))
sheet.save(OUT/'demo-contact-sheet.png')
for p in OUT.iterdir(): print(p.name,p.stat().st_size)
