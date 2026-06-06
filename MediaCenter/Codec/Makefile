# MediaCenter/Codec/Makefile
# Builds all atomized codec workers.
#
# Each worker is a standalone process wrapping one libavcodec decoder.
# They communicate with MediaCenter via mmap ring buffers in /dev/shm.
#
# Copyright 2026 Sean Collins, 2 Paws Machine and Engineering. SCSL.

CC       = gcc
CFLAGS   = -O2 -Wall -Wextra -Wno-unused-parameter

# pkg-config for ffmpeg libraries
AV_CFLAGS  = $(shell pkg-config --cflags libavcodec libavutil libswresample 2>/dev/null)
AV_LIBS    = $(shell pkg-config --libs libavcodec libavutil libswresample 2>/dev/null)
SWS_CFLAGS = $(shell pkg-config --cflags libswscale 2>/dev/null)
SWS_LIBS   = $(shell pkg-config --libs libswscale 2>/dev/null)
FMT_CFLAGS = $(shell pkg-config --cflags libavformat 2>/dev/null)
FMT_LIBS   = $(shell pkg-config --libs libavformat 2>/dev/null)

# Worker lists
AUDIO_WORKERS = mp3_worker aac_worker opus_worker flac_worker vorbis_worker pcm_worker
VIDEO_WORKERS = h264_worker h265_worker vp9_worker av1_worker
DEMUX_WORKERS = demux_worker

ALL_WORKERS = $(AUDIO_WORKERS) $(VIDEO_WORKERS) $(DEMUX_WORKERS)

.PHONY: all clean audio video demux

all: $(ALL_WORKERS)

audio: $(AUDIO_WORKERS)
video: $(VIDEO_WORKERS)
demux: $(DEMUX_WORKERS)

# Audio workers: libavcodec + libswresample
$(AUDIO_WORKERS): %: %.c ailang_codec_abi.h
	$(CC) $(CFLAGS) $(AV_CFLAGS) -o $@ $< $(AV_LIBS)

# Video workers: libavcodec + libswscale
$(VIDEO_WORKERS): %: %.c ailang_codec_abi.h
	$(CC) $(CFLAGS) $(AV_CFLAGS) $(SWS_CFLAGS) -o $@ $< $(AV_LIBS) $(SWS_LIBS)

# Demux worker: libavformat + libavcodec
$(DEMUX_WORKERS): %: %.c ailang_codec_abi.h
	$(CC) $(CFLAGS) $(AV_CFLAGS) $(FMT_CFLAGS) -o $@ $< $(AV_LIBS) $(FMT_LIBS)

clean:
	rm -f $(ALL_WORKERS)
