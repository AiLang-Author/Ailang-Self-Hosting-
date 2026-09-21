#!/usr/bin/env python3
"""Board JSON -> Graphviz. python3 board_dot.py c64.board.json"""
import json, os, sys

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "c64.board.json")
    board = json.load(open(path))
    out = os.path.splitext(path)[0] + ".dot"
    lines = [
        "digraph board {",
        "  rankdir=LR;",
        '  node [shape=box, fontname="Helvetica"];',
        '  edge [fontname="Helvetica", fontsize=10];',
        '  labelloc="t";',
        '  label="%s";' % board.get("title", board.get("board", "board")),
    ]
    for c in board.get("chips", []):
        cid = c["id"]
        label = "%s\\n%s\\n%s" % (cid, c.get("part", ""), c.get("model", ""))
        lines.append('  "%s" [label="%s"];' % (cid, label))
    for m in board.get("maps", []):
        chip = m["chip"]
        lab = "%s-%s devid %s" % (m.get("lo", "?"), m.get("hi", "?"), m.get("devid", "?"))
        lines.append('  "cpu_bus" -> "%s" [style=dashed, label="%s"];' % (chip, lab))
    lines.append('  "cpu_bus" [shape=ellipse, style=filled, fillcolor=lightgrey];')
    for n in board.get("nets", []):
        name = n.get("name", "net")
        dests = n.get("to", [])
        srcs = n.get("from", [])
        for s in srcs:
            src = s.split(".")[0]
            for d in dests:
                dst = d.split(".")[0]
                lines.append('  "%s" -> "%s" [color=red, label="%s"];' % (src, dst, name))
    lines.append("}")
    open(out, "w").write("\n".join(lines) + "\n")
    print(out)

if __name__ == "__main__":
    main()
