import json, glob, re, sys
PAT = re.compile(r'^[0-9A-HJKMNP-TV-Z]{26}$')
CAND = re.compile(r'"(01[0-9A-Z]{20,30})"')   # anything shaped like a ULID literal
bad = []
for f in sorted(glob.glob('*/v1/*.json')):
    for m in CAND.finditer(open(f).read()):
        v = m.group(1)
        if not PAT.match(v):
            why = []
            if len(v) != 26: why.append(f"len {len(v)}")
            illegal = sorted(set(c for c in v if c in 'ILOU'))
            if illegal: why.append("illegal " + ",".join(illegal))
            bad.append((f, v, "; ".join(why)))
for f, v, why in bad:
    print(f"  FAIL {f}: {v}  ({why})")
print(f"  ok - every ULID literal is 26-char Crockford base32 (excludes I L O U)" if not bad
      else f"  {len(bad)} malformed ULID literal(s)")
sys.exit(1 if bad else 0)
