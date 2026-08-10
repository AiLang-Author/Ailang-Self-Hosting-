# Build FLTK for CAD shell (no root required)

The FLTK presenter lives at `CAD/host/cad_shell_fltk.cxx` and expects a local install:

```text
third_party/fltk/bin/fltk-config
```

## One-shot (already done on dogfood machines)

```bash
cd /tmp
curl -fsSL -o fltk-1.3.9-source.tar.bz2 \
  https://www.fltk.org/pub/fltk/1.3.9/fltk-1.3.9-source.tar.bz2
tar xf fltk-1.3.9-source.tar.bz2
cd fltk-1.3.9
./configure --prefix="$PWD/../../Ailang-Self-Hosting-/third_party/fltk" \
  --disable-gl --disable-xft --disable-xdbe --enable-shared=no --enable-threads
# adjust prefix to your repo root/third_party/fltk
make -j$(nproc)
make install
```

From repo root:

```bash
PREFIX="$(pwd)/third_party/fltk"
cd /tmp/fltk-1.3.9   # or fresh extract
./configure --prefix="$PREFIX" --disable-gl --disable-xft --disable-xdbe \
  --enable-shared=no --enable-threads
make -j$(nproc) && make install
make -C CAD/host fltk
```

`--disable-xft` is required when libxft-dev / freetype pkg-config is missing.

## System packages (if you have sudo)

```bash
sudo apt-get install -y libfltk1.3-dev
# then set FLTK_CONFIG=fltk-config when building
```

## Build shell only

```bash
make -C CAD/host fltk
# or
g++ -O2 -o CAD/host/cad_shell_fltk CAD/host/cad_shell_fltk.cxx \
  $(third_party/fltk/bin/fltk-config --cxxflags) \
  $(third_party/fltk/bin/fltk-config --ldflags --use-images)
```
