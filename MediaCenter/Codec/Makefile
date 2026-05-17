CC      = gcc
CFLAGS  = -O2 -Wall $(shell pkg-config --cflags libavcodec libavutil libswresample)
LIBS    = $(shell pkg-config --libs   libavcodec libavutil libswresample)

all: mp3_worker

mp3_worker: mp3_worker.c ailang_codec_abi.h
	$(CC) $(CFLAGS) -o mp3_worker mp3_worker.c $(LIBS)

clean:
	rm -f mp3_worker

.PHONY: all clean
