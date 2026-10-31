/* Interior pixels of a 400x400 Mandelbrot, 50 iterations.
   Same map as mandelbrot.ailang. -ffp-contract=off so the count matches. */
#include <stdio.h>
#include <time.h>

static long long stamp(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static int count_inside(int h) {
    double two = 2.0;
    double scale2 = two / (double)h;
    double scale3 = 3.0 / (double)h;
    double half = 0.5;
    double four = 4.0;
    int half_i = h / 2;
    int n = 0;
    int y, x;
    for (y = 0; y < h; y++) {
        double ci = (double)(y - half_i) * scale2;
        for (x = 0; x < h; x++) {
            double cr = (double)(x - half_i) * scale3 - half;
            double zr = 0.0;
            double zi = 0.0;
            int inside = 1;
            int i;
            for (i = 0; i < 50; i++) {
                double zr2 = zr * zr;
                double zi2 = zi * zi;
                double mag = zr2 + zi2;
                if (four < mag) {
                    inside = 0;
                    break;
                }
                zi = two * zr * zi + ci;
                zr = zr2 - zi2 + cr;
            }
            n += inside;
        }
    }
    return n;
}

int main(void) {
    long long t0 = stamp();
    int n = count_inside(400);
    long long t1 = stamp();
    printf("MANDEL inside %d ns %lld\n", n, t1 - t0);
    return 0;
}
