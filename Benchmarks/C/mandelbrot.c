/* Scalar mandelbrot, same arithmetic as Greg Buchholz, Benchmarks Game
 * gcc #8. N is 512 so a five-run pin fits on this machine. The official
 * timing size is 16000. Width is a multiple of 8, so every row emits
 * whole bytes and the tail shift in the original is not taken.
 * Checksum is the sum and xor of the P4 bitmap bytes, header excluded.
 * Multiplies and adds stay separate. Build with -ffp-contract=off.
 */
#include <stdio.h>

enum { N = 512, ITER = 50 };

int main(void) {
    int x, y, i;
    unsigned long long sum = 0;
    unsigned long long mix = 0;
    unsigned long long nbytes = 0;
    const double limit2 = 4.0;

    for (y = 0; y < N; y++) {
        unsigned int byte_acc = 0;
        int bit_num = 0;
        double ci = (2.0 * (double)y / (double)N) - 1.0;
        for (x = 0; x < N; x++) {
            double zr = 0.0;
            double zi = 0.0;
            double tr = 0.0;
            double ti = 0.0;
            double cr = (2.0 * (double)x / (double)N) - 1.5;
            for (i = 0; i < ITER && (tr + ti) <= limit2; i++) {
                double two_zr = 2.0 * zr;
                double zi_m = two_zr * zi;
                zi = zi_m + ci;
                double diff = tr - ti;
                zr = diff + cr;
                tr = zr * zr;
                ti = zi * zi;
            }
            byte_acc = byte_acc << 1;
            if ((tr + ti) <= limit2) {
                byte_acc = byte_acc | 1u;
            }
            bit_num++;
            if (bit_num == 8) {
                unsigned int b = byte_acc & 255u;
                sum += b;
                mix ^= b;
                nbytes++;
                byte_acc = 0;
                bit_num = 0;
            }
        }
    }
    printf("SUM %llu\n", sum);
    printf("XOR %llu\n", mix);
    printf("BYTES %llu\n", nbytes);
    return 0;
}
