# AILang HDL templates

Copy-paste starting points for `-hdl` chips. Not auto-imported.

| File | Use |
|---|---|
| `stream_skid_1deep.ailang` | Ready/valid stream with 1-deep skid hold |

```bash
./ailang_hdl.x -hdl dev/hdl_templates/stream_skid_1deep.ailang /tmp/skid
yosys -s /tmp/skid.ys
```

User guide: `Programming_Manual/AILANG HDL Programming Guide.md`
