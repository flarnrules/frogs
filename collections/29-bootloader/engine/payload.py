from .rle import base36

def pack_blob(model: dict) -> str:
    w,h = model["w"], model["h"]
    rows = model["runs"]
    p = "P:" + ",".join(model["palette"])
    rparts=[]
    for row in rows:
        rparts.append(",".join(f"{base36(L)}.{base36(i)}" for (L,i) in row))
    r = "R:" + ";".join(rparts)
    return f"{base36(w)},{base36(h)}|{p}|{r}"
