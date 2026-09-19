ROOT := ../..
GTKH := $(ROOT)/third_party/gtk3-headers
GLIB_INC := /usr/include/glib-2.0
GLIB_GEN := /usr/lib/x86_64-linux-gnu/glib-2.0/include

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

LIBDIR := /usr/lib/x86_64-linux-gnu
GTK_LIBS := \
	$(LIBDIR)/libgtk-3.so.0 \
	$(LIBDIR)/libgdk-3.so.0 \
	$(LIBDIR)/libcairo.so.2 \
	$(LIBDIR)/libpango-1.0.so.0 \
	$(LIBDIR)/libpangocairo-1.0.so.0 \
	$(LIBDIR)/libgdk_pixbuf-2.0.so.0 \
	$(LIBDIR)/libatk-1.0.so.0 \
	-lgobject-2.0 -lglib-2.0 -lm

.PHONY: all clean

all: c64_shell_gtk

c64_shell_gtk: c64_shell_gtk.cxx
	@test -f $(GTKH)/usr/include/gtk-3.0/gtk/gtk.h || \
	  (echo "GTK headers missing at $(GTKH)." >&2; exit 1)
	g++ -O2 -std=c++17 -o $@ $< $(GTK_CFLAGS) $(GTK_LIBS)

clean:
	rm -f c64_shell_gtk
