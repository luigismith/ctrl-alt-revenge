# Makefile for CTRL+ALT REVENGE! GBC
GBDK = D:/gbdk/gbdk
LCC = $(GBDK)/bin/lcc
CFLAGS = -Wa-l -Wl-m -Wl-j -Wf--bo -DUSE_SFR_FOR_REG
ROM_NAME = CTRL_ALT_REVENGE

all: build/$(ROM_NAME).gbc

build/$(ROM_NAME).gbc: src/main.c src/game.h res/sprites.h res/tiles.h res/palettes.h
	$(LCC) $(CFLAGS) -o build/$(ROM_NAME).gbc src/main.c

clean:
	rm -f build/*.gbc build/*.map build/*.noi build/*.sym

.PHONY: all clean
