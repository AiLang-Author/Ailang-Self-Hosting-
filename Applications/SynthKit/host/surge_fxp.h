#ifndef SYNTHKIT_SURGE_FXP_H
#define SYNTHKIT_SURGE_FXP_H

/* Surge XT stores a patch as a VST .fxp chunk whose payload is XML.
   This reads scene A and maps the parts our synth can sound. */

struct SurgeMapped {
    char title[160];
    char note[320];
    int wave;
    int wave2;
    int oscmix;
    int cutoff;
    int res;
    int fenv;
    int atk;
    int dec;
    int sus;
    int rel;
    int vol;
};

int surge_fxp_map(const char *path, SurgeMapped *out);

#endif
