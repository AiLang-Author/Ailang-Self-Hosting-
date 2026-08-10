# CAD presenters — X11 reference + FLTK shell
ROOT := ../..
FLTK_CONFIG ?= $(ROOT)/third_party/fltk/bin/fltk-config

.PHONY: all clean x11 fltk

all: x11 fltk

x11: cad_host_x11 cad_panel_x11

cad_host_x11: cad_host_x11.c
	cc -O2 -o $@ $< -lX11 -lm

cad_panel_x11: cad_panel_x11.c
	cc -O2 -o $@ $< -lX11

fltk: cad_shell_fltk

cad_shell_fltk: cad_shell_fltk.cxx
	@if [ ! -x "$(FLTK_CONFIG)" ]; then \
	  echo "FLTK missing at $(FLTK_CONFIG)"; \
	  echo "Build: see CAD/host/BUILD_FLTK.md"; \
	  exit 1; \
	fi
	g++ -O2 -o $@ $< $$($(FLTK_CONFIG) --cxxflags) $$($(FLTK_CONFIG) --ldflags --use-images)

clean:
	rm -f cad_host_x11 cad_panel_x11 cad_shell_fltk
