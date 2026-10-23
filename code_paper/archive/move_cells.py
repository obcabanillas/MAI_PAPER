"""Move notebook cells into an archive notebook (used to strip exhibits not in the paper).

    python archive/move_cells.py SOURCE.ipynb ARCHIVE.ipynb CELL_ID [CELL_ID ...]

The cells are removed from SOURCE and appended, in their original order and with
their outputs, to ARCHIVE (created if missing). A markdown cell records where they
came from. Nothing else in SOURCE changes.
"""
import json
import os
import sys
import uuid


def main(src, dst, ids):
    nb = json.load(open(src, encoding="utf-8"))
    ids = set(ids)
    moved = [c for c in nb["cells"] if c.get("id") in ids]
    missing = ids - {c.get("id") for c in moved}
    if missing:
        sys.exit(f"cell ids not found in {src}: {sorted(missing)}")
    nb["cells"] = [c for c in nb["cells"] if c.get("id") not in ids]

    if os.path.exists(dst):
        ar = json.load(open(dst, encoding="utf-8"))
    else:
        ar = {k: v for k, v in nb.items() if k != "cells"}
        ar["cells"] = [{"cell_type": "markdown", "id": uuid.uuid4().hex[:8], "metadata": {},
                        "source": [f"# Archive of {os.path.basename(src)}\n\n",
                                   "Cells moved out of the working notebook because they make exhibits that are not "
                                   "in the final paper (AFG_paper_revised.docx), or are exploratory. They are kept "
                                   "as they were and are not maintained; they may depend on variables defined in "
                                   "the original notebook."]}]
    ar["cells"].append({"cell_type": "markdown", "id": uuid.uuid4().hex[:8], "metadata": {},
                        "source": [f"## Moved from `{os.path.basename(src)}`: cells "
                                   + ", ".join(c['id'] for c in moved)]})
    ar["cells"].extend(moved)
    json.dump(ar, open(dst, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(nb, open(src, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"moved {len(moved)} cells from {src} to {dst}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
