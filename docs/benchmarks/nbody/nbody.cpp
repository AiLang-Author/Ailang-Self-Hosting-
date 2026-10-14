/* Five-body solar system from the Benchmarks Game n-body entry.
 * One array of structs: x, y, z, vx, vy, vz, mass. No SIMD intrinsics.
 * Products stay separate from adds so the bits match an unfused f64.
 */

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

enum { NB = 5, STRIDE = 7 };

static long long nsec_now(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000000000LL + ts.tv_nsec;
}

static double PI = 3.141592653589793;
static double DAYS = 365.24;

static void init(double *b)
{
    double solar = 4.0 * PI * PI;
    double raw[NB][STRIDE] = {
        { 0, 0, 0, 0, 0, 0, 1.0 },
        { 4.84143144246472090e+00, -1.16032004402742839e+00,
          -1.03622044471123109e-01, 1.66007664274403694e-03,
          7.69901118419740425e-03, -6.90460016972063023e-05,
          9.54791938424326609e-04 },
        { 8.34336671824457987e+00, 4.12479856412430479e+00,
          -4.03523417114321381e-01, -2.76742510726862411e-03,
          4.99852801234917238e-03, 2.30417297573763929e-05,
          2.85885980666130812e-04 },
        { 1.28943695621391310e+01, -1.51111514016986312e+01,
          -2.23307578892655734e-01, 2.96460137564761618e-03,
          2.37847173959480950e-03, -2.96589568540237556e-05,
          4.36624404335156298e-05 },
        { 1.53796971148509165e+01, -2.59193146099879641e+01,
          1.79258772950371181e-01, 2.68067772490389322e-03,
          1.62824170038242295e-03, -9.51592254519715870e-05,
          5.15138902046611451e-05 }
    };
    int i;
    for (i = 0; i < NB; i++) {
        b[i * STRIDE + 0] = raw[i][0];
        b[i * STRIDE + 1] = raw[i][1];
        b[i * STRIDE + 2] = raw[i][2];
        b[i * STRIDE + 3] = raw[i][3] * DAYS;
        b[i * STRIDE + 4] = raw[i][4] * DAYS;
        b[i * STRIDE + 5] = raw[i][5] * DAYS;
        b[i * STRIDE + 6] = raw[i][6] * solar;
    }
}

static void offset(double *b)
{
    double solar = b[6];
    double px = 0;
    double py = 0;
    double pz = 0;
    int i;
    for (i = 0; i < NB; i++) {
        double m = b[i * STRIDE + 6];
        double vx = b[i * STRIDE + 3];
        double vy = b[i * STRIDE + 4];
        double vz = b[i * STRIDE + 5];
        double mx = m * vx;
        double my = m * vy;
        double mz = m * vz;
        px = px + mx;
        py = py + my;
        pz = pz + mz;
    }
    b[3] = -px / solar;
    b[4] = -py / solar;
    b[5] = -pz / solar;
}

static void advance(double *b, double dt)
{
    int i, j;
    for (i = 0; i < NB; i++) {
        for (j = i + 1; j < NB; j++) {
            double *bi = b + i * STRIDE;
            double *bj = b + j * STRIDE;
            double dx = bi[0] - bj[0];
            double dy = bi[1] - bj[1];
            double dz = bi[2] - bj[2];
            double dx2 = dx * dx;
            double dy2 = dy * dy;
            double dz2 = dz * dz;
            double dist2 = dx2 + dy2;
            dist2 = dist2 + dz2;
            double dist = sqrt(dist2);
            double dist3 = dist2 * dist;
            double mag = dt / dist3;
            double m2 = bj[6] * mag;
            double m1 = bi[6] * mag;
            double dxm = dx * m2;
            double dym = dy * m2;
            double dzm = dz * m2;
            bi[3] = bi[3] - dxm;
            bi[4] = bi[4] - dym;
            bi[5] = bi[5] - dzm;
            dxm = dx * m1;
            dym = dy * m1;
            dzm = dz * m1;
            bj[3] = bj[3] + dxm;
            bj[4] = bj[4] + dym;
            bj[5] = bj[5] + dzm;
        }
    }
    for (i = 0; i < NB; i++) {
        double *bi = b + i * STRIDE;
        double dtvx = dt * bi[3];
        double dtvy = dt * bi[4];
        double dtvz = dt * bi[5];
        bi[0] = bi[0] + dtvx;
        bi[1] = bi[1] + dtvy;
        bi[2] = bi[2] + dtvz;
    }
}

static double energy(double *b)
{
    double half = 0.5;
    double e = 0;
    int i, j;
    for (i = 0; i < NB; i++) {
        double *bi = b + i * STRIDE;
        double vx2 = bi[3] * bi[3];
        double vy2 = bi[4] * bi[4];
        double vz2 = bi[5] * bi[5];
        double v2 = vx2 + vy2;
        v2 = v2 + vz2;
        double mv = bi[6] * v2;
        double kin = half * mv;
        e = e + kin;
        for (j = i + 1; j < NB; j++) {
            double *bj = b + j * STRIDE;
            double dx = bi[0] - bj[0];
            double dy = bi[1] - bj[1];
            double dz = bi[2] - bj[2];
            double dx2 = dx * dx;
            double dy2 = dy * dy;
            double dz2 = dz * dz;
            double dist2 = dx2 + dy2;
            dist2 = dist2 + dz2;
            double dist = sqrt(dist2);
            double mm = bi[6] * bj[6];
            double pot = mm / dist;
            e = e - pot;
        }
    }
    return e;
}

static void run(int steps)
{
    double b[NB * STRIDE];
    double dt = 0.01;
    long long t0, t1;
    int step;
    double ev;
    int64_t e0, e1;
    init(b);
    offset(b);
    ev = energy(b);
    memcpy(&e0, &ev, 8);
    t0 = nsec_now();
    for (step = 0; step < steps; step++)
        advance(b, dt);
    t1 = nsec_now();
    ev = energy(b);
    memcpy(&e1, &ev, 8);
    printf("NBODY %d e0 %lld e1 %lld ns %lld\n", steps,
           (long long)e0, (long long)e1, (long long)(t1 - t0));
}

int main(void)
{
    run(1000);
    run(1000000);
    return 0;
}
