import pathlib

root = pathlib.Path(r"C:\Users\bunkyo\Desktop\a15_full_system\django\core\templates")

# 対象: テンプレート配下の .html
files = list(root.rglob("*.html"))

converted = []
already = []
failed = []

for f in files:
    b = f.read_bytes()
    # まず UTF-8 で読めるか試す
    try:
        b.decode("utf-8")
        already.append(str(f))
        continue
    except UnicodeDecodeError:
        pass
    # ダメなら CP932(Shift_JIS) で読んで UTF-8 で書き直す
    try:
        s = b.decode("cp932")
        f.write_text(s, encoding="utf-8")   # UTF-8 で保存（BOMなし）
        converted.append(str(f))
    except Exception as e:
        failed.append((str(f), repr(e)))

print("ALREADY_UTF8:", len(already))
print("CONVERTED_TO_UTF8:", len(converted))
for x in converted:
    print("  converted:", x)
if failed:
    print("FAILED:", len(failed))
    for x in failed:
        print("  failed:", x[0], x[1])
