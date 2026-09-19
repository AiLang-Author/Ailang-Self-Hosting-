# SynthKit Gtk3 chrome. Kernel owns the synth; this window is keys + knobs.
# Copyright © 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL v1.0.

AILANG_ROOT ?= $(HOME)/Ailang-Self-Hosting-
ARCADE ?= $(HOME)/Arcade
GTKH := $(AILANG_ROOT)/third_party/gtk3-headers
GLIB_INC := /usr/include/glib-2.0
GLIB_GEN := /usr/lib/x86_64-linux-gnu/glib-2.0/include
LIBDIR := /usr/lib/x86_64-linux-gnu

PKG := $(shell pkg-config --exists gtk+-3.0 && echo yes)

ifeq ($(PKG),yes)
  GTK_CFLAGS := $(shell pkg-config --cflags gtk+-3.0)
  GTK_LIBS := $(shell pkg-config --libs gtk+-3.0)
else
  GTK_CFLAGS := \
	-I$(GTKH)/usr/include/gtk-3.0 \
	-I$(GTKH)/usr/include/cairo \
	-I$(GTKH)/usr/include/pango-1.0 \
	-I$(GTKH)/usr/include/gdk-pixbuf-2.0 \
	-I$(GTKH)/usr/include/atk-1.0 \
	-I$(GTKH)/usr/include/harfbuzz \
	-I$(GTKH)/usr/include/fribidi \
	-I$(GTKH)/usr/include/freetype2 \
	-I$(GTKH)/usr/include \
	-I$(GLIB_INC) \
	-I$(GLIB_GEN)
  GTK_LIBS := \
	$(LIBDIR)/libgtk-3.so.0 \
	$(LIBDIR)/libgdk-3.so.0 \
	$(LIBDIR)/libcairo.so.2 \
	-lgobject-2.0 -lglib-2.0 -lm
endif

.PHONY: all clean

all: synth_shell_gtk

synth_shell_gtk: synth_shell_gtk.cxx pcm_play.cc pcm_play.h midi_in.cc midi_in.h
	g++ -O2 -std=c++17 -I$(ARCADE)/host -o $@ synth_shell_gtk.cxx pcm_play.cc midi_in.cc \
		$(GTK_CFLAGS) $(GTK_LIBS) -lpthread -ldl -lm

clean:
	rm -f synth_shell_gtk
