#!/usr/bin/env python3

import random
import datetime
from os import path, listdir
from array import array
from voip import loadWAVtoPCM

selfPath = path.dirname(path.realpath(__file__))

backgroundsNormalPath = path.join(selfPath, "./bgs/normal")
backgroundsWeirdPath = path.join(selfPath, "./bgs/weird")
bodiesPath = path.join(selfPath, "./fishes/body")
headsPath = path.join(selfPath, "./fishes/head")
tailsPath = path.join(selfPath, "./fishes/tail")

skeletonPath = path.join(selfPath, "./fish_skeleton.png")

backgroundsNormal = listdir(backgroundsNormalPath)
backgroundsWeird = listdir(backgroundsWeirdPath)
bodies = listdir(bodiesPath)
heads = listdir(headsPath)
tails = listdir(tailsPath)

def generate_fish():
    # Import in scope to prevent crashes when dependencies arent installed
    from PIL import Image 
    from pysstv import color

    skeleton = Image.open(skeletonPath)

    backgroundPath = path.join(backgroundsNormalPath, random.choice(backgroundsNormal))
    if (random.random() < 0.15):
        backgroundPath = path.join(backgroundsWeirdPath, random.choice(backgroundsWeird))

    bodyPath = path.join(bodiesPath, random.choice(bodies))
    headPath = path.join(headsPath, random.choice(heads))
    tailPath = path.join(tailsPath,random.choice(tails))

    final = Image.new("RGBA", (320, 256))

    body = Image.open(bodyPath)
    head = Image.open(headPath)
    tail = Image.open(tailPath)

    final.paste(Image.open(backgroundPath))
    final.paste(skeleton, (0,0), skeleton)
    final.paste(body, (0,0), body)
    final.paste(head, (0,0), head)
    final.paste(tail, (0,0), tail)

    sstv = color.MartinM1(final, 8000, 16)
    return sstv.gen_values()

async def handler(call):
    # Since we have no way of verifying timezone, we'll make a fish at every 
    # 11th minute to not leave anyone out. In theory we could verify by area 
    # code, but that's not always accurate, and would be pain to map out
    currTime = datetime.datetime.now()

    if currTime.minute == 11:
        await call.playPCM(array("f", generate_fish()))
    else:
        await call.playPCM(loadWAVtoPCM("assets/fish_not_ready.wav"))
