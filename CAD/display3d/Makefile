# CAD/display3d — orthogonal AilangVk + Display3D viewport
#
# AilangVk is a compiler / Display / CAD GPU resource.
# Display3D is the 3D viewport consumer (SSE2 fallback if Vulkan is absent).
# Copyright (c) 2025-2026 Sean Collins, 2 Paws Machine and Engineering. All rights reserved.
# Licensed under the Sean Collins Software License (SCSL v1.0).

CXX      ?= g++
CC       ?= gcc
PREFIX   ?=
INCLUDES  = -Iinclude -Isrc
CXXFLAGS ?= -O2 -Wall -Wextra -msse2 -fno-exceptions -fno-rtti
CFLAGS   ?= -O2 -Wall -Wextra
LDFLAGS  ?= -shared -fPIC

HAS_VULKAN := $(shell test -f /usr/include/vulkan/vulkan.h && echo 1)

ifeq ($(HAS_VULKAN),1)
  CXXFLAGS += -DHAS_VULKAN=1
  LIBS     += -lvulkan
endif
LIBS += -lm

TARGET   = libailang_display3d.so
WORKER   = vk_worker
SRCS     = src/ailang_vk.cpp src/display3d_vulkan.cpp
TEST_VK  = tests/test_ailang_vk
TEST_D3D = tests/test_display3d

.PHONY: all clean test shaders test-vk test-d3d

all: $(TARGET) $(WORKER)

shaders:
	python3 src/shaders/gen_mesh_spv.py

$(TARGET): $(SRCS) include/ailang_vk.h include/ailang_display3d.h src/shaders/mesh_vert.spv.h src/shaders/mesh_frag.spv.h
	$(CXX) $(CXXFLAGS) -fPIC $(INCLUDES) $(SRCS) $(LDFLAGS) $(LIBS) -o $@

$(TEST_VK): tests/test_ailang_vk.c $(TARGET)
	$(CC) $(CFLAGS) -Iinclude tests/test_ailang_vk.c -L. -lailang_display3d -lm -o $@

$(TEST_D3D): tests/test_display3d.c $(TARGET)
	$(CC) $(CFLAGS) -Iinclude tests/test_display3d.c -L. -lailang_display3d -lm -o $@

$(WORKER): src/vk_worker.c $(TARGET)
	$(CC) $(CFLAGS) -Iinclude src/vk_worker.c -L. -lailang_display3d -Wl,-rpath,'$$ORIGIN' -o $@

test-vk: $(TARGET) $(TEST_VK)
	LD_LIBRARY_PATH=. ./$(TEST_VK)

test-d3d: $(TARGET) $(TEST_D3D)
	LD_LIBRARY_PATH=. ./$(TEST_D3D)

test: test-vk test-d3d

clean:
	rm -f $(TARGET) $(WORKER) $(TEST_VK) $(TEST_D3D)
