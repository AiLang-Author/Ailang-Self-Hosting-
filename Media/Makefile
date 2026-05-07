CC = gcc
CFLAGS = -O2 -Wall -Wextra
COMMON_SRC = packetring.c playbackclock.c
COMMON_OBJ = packetring.o playbackclock.o

# ============================================================================
# Targets — always-built (no external deps) and conditionally-built (need libs)
# ============================================================================
TARGETS = decode_pcm.x resample_audio.x

# Detect available libraries and enable targets
HAVE_OPENH264 := $(shell pkg-config --exists openh264 2>/dev/null && echo yes)
HAVE_VPX      := $(shell pkg-config --exists vpx 2>/dev/null && echo yes)
HAVE_FAAD     := $(shell test -f /usr/include/neaacdec.h -o -f /usr/local/include/neaacdec.h && echo yes)
HAVE_OPUS     := $(shell pkg-config --exists opus 2>/dev/null && echo yes)
HAVE_MPG123   := $(shell pkg-config --exists libmpg123 2>/dev/null && echo yes)
HAVE_DE265    := $(shell pkg-config --exists libde265 2>/dev/null && echo yes)
HAVE_DAV1D    := $(shell pkg-config --exists dav1d 2>/dev/null && echo yes)
HAVE_FLAC     := $(shell pkg-config --exists flac 2>/dev/null && echo yes)

ifeq ($(HAVE_OPENH264),yes)
  TARGETS += decode_h264.x
endif
ifeq ($(HAVE_VPX),yes)
  TARGETS += decode_vp9.x
endif
ifeq ($(HAVE_FAAD),yes)
  TARGETS += decode_aac.x
endif
ifeq ($(HAVE_OPUS),yes)
  TARGETS += decode_opus.x
endif
ifeq ($(HAVE_MPG123),yes)
  TARGETS += decode_mp3.x
endif
ifeq ($(HAVE_DE265),yes)
  TARGETS += decode_h265.x
endif
ifeq ($(HAVE_DAV1D),yes)
  TARGETS += decode_av1.x
endif
ifeq ($(HAVE_FLAC),yes)
  TARGETS += decode_flac.x
endif

.PHONY: all clean info

all: $(TARGETS)
	@echo "Built: $(TARGETS)"

info:
	@echo "HAVE_OPENH264 = $(HAVE_OPENH264)"
	@echo "HAVE_VPX      = $(HAVE_VPX)"
	@echo "HAVE_FAAD     = $(HAVE_FAAD)"
	@echo "HAVE_OPUS     = $(HAVE_OPUS)"
	@echo "HAVE_MPG123   = $(HAVE_MPG123)"
	@echo "HAVE_DE265    = $(HAVE_DE265)"
	@echo "HAVE_DAV1D    = $(HAVE_DAV1D)"
	@echo "HAVE_FLAC     = $(HAVE_FLAC)"
	@echo "TARGETS       = $(TARGETS)"

# Common objects
packetring.o: packetring.c packetring.h
	$(CC) $(CFLAGS) -c packetring.c -o packetring.o

playbackclock.o: playbackclock.c playbackclock.h
	$(CC) $(CFLAGS) -c playbackclock.c -o playbackclock.o

# ============================================================================
# PCM pass-through decoder (no external codec lib)
# ============================================================================
decode_pcm.x: decode_pcm.c $(COMMON_OBJ)
	$(CC) $(CFLAGS) -o decode_pcm.x decode_pcm.c $(COMMON_OBJ)

# ============================================================================
# Audio resampler (no external codec lib — pure linear interpolation)
# ============================================================================
resample_audio.x: resample_audio.c $(COMMON_OBJ)
	$(CC) $(CFLAGS) -o resample_audio.x resample_audio.c $(COMMON_OBJ)

# ============================================================================
# H.264 decoder (OpenH264)
# ============================================================================
decode_h264.x: decode_h264.c $(COMMON_OBJ)
	$(CC) $(CFLAGS) -o decode_h264.x decode_h264.c $(COMMON_OBJ) \
		$$(pkg-config --cflags --libs openh264)

# ============================================================================
# H.265/HEVC decoder (libde265)
# ============================================================================
decode_h265.x: decode_h265.c $(COMMON_OBJ)
	$(CC) $(CFLAGS) -o decode_h265.x decode_h265.c $(COMMON_OBJ) \
		$$(pkg-config --cflags --libs libde265)

# ============================================================================
# VP9 decoder (libvpx)
# ============================================================================
decode_vp9.x: decode_vp9.c $(COMMON_OBJ)
	$(CC) $(CFLAGS) -o decode_vp9.x decode_vp9.c $(COMMON_OBJ) \
		$$(pkg-config --cflags --libs vpx)

# ============================================================================
# AV1 decoder (dav1d)
# ============================================================================
decode_av1.x: decode_av1.c $(COMMON_OBJ)
	$(CC) $(CFLAGS) -o decode_av1.x decode_av1.c $(COMMON_OBJ) \
		$$(pkg-config --cflags --libs dav1d)

# ============================================================================
# AAC decoder (faad2 / libfaad)
# ============================================================================
decode_aac.x: decode_aac.c $(COMMON_OBJ)
	$(CC) $(CFLAGS) -o decode_aac.x decode_aac.c $(COMMON_OBJ) -lfaad

# ============================================================================
# Opus decoder (libopus)
# ============================================================================
decode_opus.x: decode_opus.c $(COMMON_OBJ)
	$(CC) $(CFLAGS) -o decode_opus.x decode_opus.c $(COMMON_OBJ) \
		$$(pkg-config --cflags --libs opus)

# ============================================================================
# MP3 decoder (libmpg123)
# ============================================================================
decode_mp3.x: decode_mp3.c $(COMMON_OBJ)
	$(CC) $(CFLAGS) -o decode_mp3.x decode_mp3.c $(COMMON_OBJ) \
		$$(pkg-config --cflags --libs libmpg123)

# ============================================================================
# FLAC decoder (libFLAC)
# ============================================================================
decode_flac.x: decode_flac.c $(COMMON_OBJ)
	$(CC) $(CFLAGS) -o decode_flac.x decode_flac.c $(COMMON_OBJ) \
		$$(pkg-config --cflags --libs flac)

clean:
	rm -f *.o decode_pcm.x decode_h264.x decode_h265.x decode_vp9.x \
		decode_av1.x decode_aac.x decode_opus.x decode_mp3.x \
		decode_flac.x resample_audio.x
