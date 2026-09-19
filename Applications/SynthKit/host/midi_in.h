#ifndef SYNTHKIT_MIDI_IN_H
#define SYNTHKIT_MIDI_IN_H

int synthkit_midi_init(const char *midi_path);
void synthkit_midi_poll(void);
void synthkit_midi_shutdown(void);
int synthkit_midi_ports(void);

#endif
