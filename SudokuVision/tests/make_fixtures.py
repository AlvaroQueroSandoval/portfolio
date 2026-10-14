"""Genera cinco sudokus independientes con solución única y diez imágenes por tablero."""
import json
from pathlib import Path
import random
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from solver import solve_board


def generate(seed):
    rng = random.Random(seed)
    b = [[0] * 9 for _ in range(9)]
    def fill(pos=0):
        if pos == 81:
            return True
        r, c = divmod(pos, 9)
        used = set(b[r]) | {row[c] for row in b}
        used |= {b[y][x] for y in range(r//3*3,r//3*3+3) for x in range(c//3*3,c//3*3+3)}
        nums = [n for n in range(1,10) if n not in used]
        rng.shuffle(nums)
        for n in nums:
            b[r][c]=n
            if fill(pos+1): return True
        b[r][c]=0
        return False
    fill()
    solution=[row[:] for row in b]
    order=list(range(81));rng.shuffle(order)
    for i in order:
        r,c=divmod(i,9);n=b[r][c];b[r][c]=0
        if solve_board(b,timeout=2)["status"] != "solved":
            b[r][c]=n
        if sum(bool(n) for row in b for n in row)<=32:break
    return b,solution


def render(board, serif=False, font_path=None):
    image=Image.new("RGB",(760,760),"white");draw=ImageDraw.Draw(image)
    font_file=Path(font_path or ("C:/Windows/Fonts/georgia.ttf" if serif else "C:/Windows/Fonts/arial.ttf"))
    font=ImageFont.truetype(str(font_file) if font_file.exists() else ("DejaVuSerif.ttf" if serif else "DejaVuSans.ttf"),46)
    for i in range(10):
        pos=20+i*80
        draw.line((20,pos,740,pos),fill="black",width=5 if i%3==0 else 2)
        draw.line((pos,20,pos,740),fill="black",width=5 if i%3==0 else 2)
    for r in range(9):
        for c in range(9):
            if board[r][c]:
                draw.text((60+c*80,60+r*80),str(board[r][c]),font=font,fill="black",anchor="mm")
    return cv2.cvtColor(np.asarray(image),cv2.COLOR_RGB2BGR)


def variants(board,seed):
    image=render(board)
    h,w=image.shape[:2]
    src=np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]])
    dst=np.float32([[120,60],[870,160],[820,860],[50,780]])
    rng=np.random.default_rng(seed)
    noisy=np.clip(image.astype(float)+rng.normal(0,10,image.shape),0,255).astype(np.uint8)
    _, encoded=cv2.imencode(".jpg",noisy,[cv2.IMWRITE_JPEG_QUALITY,35])
    return {
        "normal":image,
        "reducido_300":cv2.resize(image,(300,300),interpolation=cv2.INTER_AREA),
        "muy_pequeno_144":cv2.resize(image,(144,144),interpolation=cv2.INTER_AREA),
        "giro_90":cv2.rotate(image,cv2.ROTATE_90_CLOCKWISE),
        "inclinacion_10":cv2.warpAffine(image,cv2.getRotationMatrix2D((w/2,h/2),10,.87),(w,h),borderValue=(220,220,220)),
        "perspectiva":cv2.warpPerspective(image,cv2.getPerspectiveTransform(src,dst),(960,960),borderValue=(220,220,220)),
        "sombra":(image.astype(float)*np.linspace(.25,1,w)[None,:,None]).astype(np.uint8),
        "desenfoque":cv2.GaussianBlur(image,(17,17),4),
        "ruido_jpeg":cv2.imdecode(encoded,cv2.IMREAD_COLOR),
        "tipografia_serif":render(board,True),
    }


if __name__=="__main__":
    folder=ROOT/"tests/fixtures";folder.mkdir(parents=True,exist_ok=True)
    examples=ROOT/"static/examples";examples.mkdir(exist_ok=True)
    manifest=[]
    for number,seed in enumerate([1103,2207,3301,4409,5501],1):
        board,solution=generate(seed)
        assert solve_board(board)["solution"]==solution
        record={"id":number,"seed":seed,"board":board,"solution":solution,"images":{}}
        for name,image in variants(board,seed).items():
            filename=f"sudoku-{number}-{name}.png"
            cv2.imwrite(str(folder/filename),image)
            record["images"][name]=filename
            if name=="normal" and number<=2:
                cv2.imwrite(str(examples/f"sudoku-{number}.png"),image)
        manifest.append(record)
    (folder/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print("Creados 5 sudokus distintos, de solución única, y 50 imágenes.")
