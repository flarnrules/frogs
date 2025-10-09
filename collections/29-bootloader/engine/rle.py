from PIL import Image
from typing import Optional, Tuple, List

def to_hex(rgb: Tuple[int,int,int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def base36(n:int)->str:
    chars="0123456789abcdefghijklmnopqrstuvwxyz"
    if n==0: return "0"
    s=""; m=abs(n)
    while m>0:
        m,r = divmod(m,36); s = chars[r]+s
    return s if n>=0 else "-"+s

def quantize(img: Image.Image, max_colors: Optional[int]) -> Image.Image:
    im = img.convert("RGBA")
    if not max_colors: return im
    return im.quantize(colors=max_colors, method=Image.FASTOCTREE, dither=Image.Dither.NONE).convert("RGBA")

def trim_alpha(img: Image.Image, thresh:int=0) -> Image.Image:
    bbox = img.split()[-1].point(lambda a: 255 if a>thresh else 0).getbbox()
    return img.crop(bbox) if bbox else img

def png_to_runs(img: Image.Image, max_colors: Optional[int], trim: bool, treat_transparent_as: Optional[Tuple[int,int,int]]):
    im = quantize(img, max_colors)
    if trim: im = trim_alpha(im)
    w,h = im.size; px = im.load()
    palette: List[Tuple[int,int,int]] = []; pindex = {}; rows = []
    def idx_of(rgb: Tuple[int,int,int]):
        if rgb not in pindex:
            pindex[rgb] = len(palette); palette.append(rgb)
        return pindex[rgb]
    for y in range(h):
        row = []
        r,g,b,a = px[0,y]
        cur = treat_transparent_as if (a==0 and treat_transparent_as is not None) else (r,g,b)
        length = 1
        for x in range(1,w):
            r,g,b,a = px[x,y]
            c = treat_transparent_as if (a==0 and treat_transparent_as is not None) else (r,g,b)
            if c == cur: length += 1
            else:
                row.append([length, idx_of(cur)])
                cur, length = c, 1
        row.append([length, idx_of(cur)])
        rows.append(row)
    pal_hex = [to_hex(rgb) for rgb in palette]
    return {"w": w, "h": h, "palette": pal_hex, "runs": rows}
