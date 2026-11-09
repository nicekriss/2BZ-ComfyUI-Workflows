"""mp4에 360(equirectangular) 표시를 넣는다 — google/spatial-media가 넣는 Spherical Video V1 uuid 박스와 같은 내용.
ffmpeg 기본 출력처럼 moov가 mdat 뒤에 있는 파일만 처리(그래야 청크 오프셋을 안 고쳐도 됨).
사용: python inject360.py 입력.mp4 출력.mp4
"""
import struct, sys

UUID = bytes.fromhex("ffcc8263f8554a938814587a02521fdd")
XML = (b'<?xml version="1.0"?><rdf:SphericalVideo\nxmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"\n'
       b'xmlns:GSpherical="http://ns.google.com/videos/1.0/spherical/"><GSpherical:Spherical>true</GSpherical:Spherical>'
       b'<GSpherical:Stitched>true</GSpherical:Stitched><GSpherical:StitchingSoftware>Spherical Metadata Tool</GSpherical:StitchingSoftware>'
       b'<GSpherical:ProjectionType>equirectangular</GSpherical:ProjectionType></rdf:SphericalVideo>')


def boxes(buf, start, end):
    i = start
    while i + 8 <= end:
        size, typ = struct.unpack(">I4s", buf[i:i + 8])
        hdr = 8
        if size == 1:
            size, hdr = struct.unpack(">Q", buf[i + 8:i + 16])[0], 16
        elif size == 0:
            size = end - i
        yield i, size, hdr, typ
        i += size


def find(buf, start, end, typ):
    return next(((o, s, h) for o, s, h, t in boxes(buf, start, end) if t == typ), None)


def main(src, dst):
    buf = bytearray(open(src, "rb").read())
    top = {t: (o, s, h) for o, s, h, t in boxes(buf, 0, len(buf))}
    mo, ms, mh = top[b"moov"]
    if b"mdat" in top and top[b"mdat"][0] > mo:
        sys.exit("moov가 mdat 앞에 있음(faststart) — 지원 안 함")
    if mh != 8:
        sys.exit("64비트 moov — 지원 안 함")
    for to, ts, th, t in boxes(buf, mo + 8, mo + ms):
        if t != b"trak":
            continue
        md = find(buf, to + 8, to + ts, b"mdia")
        hd = md and find(buf, md[0] + 8, md[0] + md[1], b"hdlr")
        if hd and buf[hd[0] + 16:hd[0] + 20] == b"vide":
            if UUID in buf[to:to + ts]:
                sys.exit("이미 360 표시 있음")
            box = struct.pack(">I4s", 8 + 16 + len(XML), b"uuid") + UUID + XML
            buf[to + ts:to + ts] = box
            struct.pack_into(">I", buf, to, ts + len(box))
            struct.pack_into(">I", buf, mo, ms + len(box))
            open(dst, "wb").write(buf)
            print("ok", dst)
            return
    sys.exit("영상 트랙 없음")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
