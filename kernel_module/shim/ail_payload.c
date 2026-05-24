/*
 * ail_payload.c — GCN 1.0 (Southern Islands) kernel-mode GPU driver payload.
 *
 * Probe sequence:
 *   1. Enable PCI device, map BARs
 *   2. Read diagnostic registers
 *   3. Halt CP, set up PM4 ring buffer in VRAM
 *   4. Unhalt CP, submit NOP ring test
 *   5. Upload shader, setup buffers, dispatch compute kernel
 *   6. Verify results: dst[gid] = src[gid] + 42
 */

#include <linux/kernel.h>
#include <linux/pci.h>
#include <linux/io.h>
#include <linux/delay.h>
#include <linux/slab.h>
#include "ail_shim.h"
#include "ail_shim_pcie.h"

/* =====================================================================
 * Southern Islands MMIO Register Offsets
 * ===================================================================== */

/* GRBM / SRBM status */
#define GRBM_STATUS           0x8010
#define GRBM_STATUS2          0x8008
#define SRBM_STATUS           0x0E50
#define GRBM_SOFT_RESET       0x8020
#define CONFIG_MEMSIZE        0x5428

/* CP control */
#define CP_ME_CNTL            0x86D8
#define CP_RB_WPTR_DELAY      0x8704

/* CP Ring 0 registers */
#define CP_RB0_CNTL           0xC104
#define CP_RB0_BASE           0xC100
#define CP_RB0_RPTR           0x8700
#define CP_RB0_RPTR_ADDR      0xC10C
#define CP_RB0_RPTR_ADDR_HI   0xC110
#define CP_RB0_WPTR           0xC114

/* Scratch registers */
#define SCRATCH_REG0          0x8500

/* CP_ME_CNTL halt bits */
#define CE_HALT               (1 << 24)
#define PFP_HALT              (1 << 26)
#define ME_HALT               (1 << 28)
#define CP_ALL_HALT           (CE_HALT | PFP_HALT | ME_HALT)

/* CP_RB_CNTL bits */
#define RB_RPTR_WR_ENA        (1U << 31)

/* Ring buffer configuration */
#define RING_SIZE_DWORDS      16384
#define RING_SIZE_BYTES       (RING_SIZE_DWORDS * 4)
#define RING_LOG2             14
#define RING_MASK             (RING_SIZE_DWORDS - 1)
#define PAGE_LOG2             8

/* VRAM layout — all offsets from start of VRAM aperture */
#define VRAM_RING_OFFSET      0x01000000   /* 16MB: PM4 ring (64KB) */
#define VRAM_RPTR_WB_OFFSET   (VRAM_RING_OFFSET + RING_SIZE_BYTES)
#define VRAM_FENCE_WB_OFFSET  (VRAM_RPTR_WB_OFFSET + 8)
#define VRAM_SHADER_OFFSET    0x01100000   /* 17MB: shader code (256B aligned) */
#define VRAM_SRC_OFFSET       0x01200000   /* 18MB: src buffer (64 * 4 = 256B) */
#define VRAM_DST_OFFSET       0x01201000   /* 18MB+4K: dst buffer (256B) */

/* PM4 packet building */
#define PM4_TYPE3_HDR(op, cnt) \
	(0xC0000000u | (((cnt) - 1) << 16) | ((op) << 8))

/* PM4 opcodes */
#define PM4_OP_NOP                0x10
#define PM4_OP_SET_SH_REG         0x76
#define PM4_OP_DISPATCH_DIRECT    0x15
#define PM4_OP_EVENT_WRITE_EOP    0x47

/* SET_SH_REG base: DWORD offset 0x2C00 (byte 0xB000) */
#define SH_REG_BASE_DWORD        0x2C00

/* Compute shader registers (byte offsets) → DWORD offsets for SET_SH_REG */
#define COMPUTE_PGM_LO            0xB830
#define COMPUTE_PGM_HI            0xB834
#define COMPUTE_PGM_RSRC1         0xB848
#define COMPUTE_PGM_RSRC2         0xB84C
#define COMPUTE_RESOURCE_LIMITS   0xB854
#define COMPUTE_NUM_THREAD_X      0xB81C
#define COMPUTE_NUM_THREAD_Y      0xB820
#define COMPUTE_NUM_THREAD_Z      0xB824
#define COMPUTE_USER_DATA_0       0xB900
#define COMPUTE_USER_DATA_1       0xB904
#define COMPUTE_USER_DATA_2       0xB908
#define COMPUTE_USER_DATA_3       0xB90C
#define COMPUTE_USER_DATA_4       0xB910
#define COMPUTE_USER_DATA_5       0xB914
#define COMPUTE_USER_DATA_6       0xB918
#define COMPUTE_USER_DATA_7       0xB91C
#define COMPUTE_TMPRING_SIZE      0xB860
#define COMPUTE_STATIC_THREAD_MGMT_SE0 0xB858
#define COMPUTE_STATIC_THREAD_MGMT_SE1 0xB85C

/* Number of test elements */
#define NUM_ELEMENTS              64

/* =====================================================================
 * GCN 1.0 Shader Binary: dst[gid] = src[gid] + 42
 *
 * Register conventions (single workgroup, so gid == thread_id):
 *   v0 = thread_id_x (pre-loaded by HW)
 *   s[0:3] = src buffer V# (loaded via USER_DATA_0..3)
 *   s[4:7] = dst buffer V# (loaded via USER_DATA_4..7)
 *
 * Instructions:
 *   BUFFER_LOAD_DWORD v1, v0, s[0:3], 0 offen    ; v1 = src[tid]
 *   S_WAITCNT vmcnt(0)                             ; wait for load
 *   V_MOV_B32 v2, 42 (literal)                     ; v2 = 42
 *   V_ADD_I32 v3, v1, v2                           ; v3 = v1 + v2
 *   BUFFER_STORE_DWORD v3, v0, s[4:7], 0 offen    ; dst[tid] = v3
 *   S_WAITCNT vmcnt(0)                             ; wait for store
 *   S_ENDPGM                                       ; done
 * ===================================================================== */

/*
 * GCN 1.0 MUBUF encoding (64-bit):
 *   [31:26] = 0x38 (MUBUF encoding)
 *   [25]    = 0 (lds)
 *   [24:18] = opcode (12 = BUFFER_LOAD_DWORD, 28 = BUFFER_STORE_DWORD)
 *   [17:16] = 0 (addr64=0, glc=0)
 *   [15:12] = offset_en flags (offen=1 → bit 12)
 *   [11:0]  = offset (0)
 *   ---
 *   Word 1:
 *   [31:24] = soffset (0x80 = literal 0, or register)
 *   [23]    = tfe (0)
 *   [22]    = slc (0)
 *   [21:18] = dfmt for typed (0 for raw)
 *   [17:14] = nfmt for typed (0 for raw)
 *   [13:8]  = srsrc (SGPR base / 4: s[0:3]=0, s[4:7]=1)
 *   [7:0]   = vdata (VGPR)
 *
 * Simpler: use the known encodings from the CIR lowering.
 *
 * MUBUF encoding for SI:
 *   word0 = (0x38 << 26) | (opcode << 18) | (offen << 12) | offset
 *   word1 = (soffset << 24) | (srsrc << 8) | vdata  [+ vaddr in [23:16]... wait]
 *
 * Actually the MUBUF format on SI:
 *   Word 0 [31:0]:
 *     [31:26] = 0b111000 = 0x38 (MUBUF marker)
 *     [25:18] = opcode
 *     [17]    = 0 (unused)
 *     [16]    = glc
 *     [15]    = 0
 *     [14]    = addr64
 *     [13]    = slc
 *     [12]    = offen
 *     [11:0]  = offset
 *   Word 1 [31:0]:
 *     [31:24] = soffset
 *     [23]    = tfe
 *     [22:18] = vdata_hi (for multi-dword loads)
 *     [17:12] = unused / idxen stuff
 *     [11:6]  = srsrc (SGPR base / 4)
 *     [5:0]   = unused
 *
 * Wait, I need to be more precise. Let me use the exact encoding from the
 * GCN 1.0 ISA manual.
 */

/*
 * Correct MUBUF encoding for GCN 1.0 (Southern Islands):
 *
 * Word 0 bits [31:0]:
 *   [31:26] = 111000 (0x38) - MUBUF identifier
 *   [25:18] = OP[7:0] - opcode
 *   [17]    = unused
 *   [16]    = GLC
 *   [15]    = unused
 *   [14]    = ADDR64
 *   [13]    = SLC
 *   [12]    = OFFEN
 *   [11:0]  = OFFSET
 *
 * Word 1 bits [31:0]:
 *   [31:24] = SOFFSET - scalar offset register (0x80 = literal 0, or SGPR number)
 *   [23]    = TFE
 *   [22:18] = unused
 *   [17:16] = DFMT (data format, 0 for untyped)
 *   [15:14] = NFMT (number format)
 *   [13:9]  = SRSRC (SGPR group: s[0:3]=0, s[4:7]=1, s[8:11]=2, ...)
 *   [8]     = IDXEN
 *   [7:0]   = VDATA (VGPR for data)
 *
 * Wait, I should just look at what the encoder generates. The CIR_GCN lowering
 * calls: GCNEnc_Emit_MUBUF(opcode, vdst, vidx, srsrc_group, offset, flags)
 * with flags=4096 meaning offen=1 (bit 12).
 *
 * Let me compute the exact encodings by hand using the GCN ISA reference.
 */

/*
 * After careful analysis of the SI MUBUF encoding:
 *
 * BUFFER_LOAD_DWORD: OP = 0x30 (48 decimal) in MTBUF or 0x0C in MUBUF
 *   ... Actually in the MUBUF opcode space:
 *   BUFFER_LOAD_FORMAT_X   = 0
 *   BUFFER_LOAD_FORMAT_XY  = 1
 *   BUFFER_STORE_FORMAT_X  = 4
 *   BUFFER_LOAD_DWORD      = 12 (0x0C)  ← unformatted
 *   BUFFER_STORE_DWORD     = 28 (0x1C)  ← unformatted
 *
 * For BUFFER_LOAD_DWORD v1, v0, s[0:3], 0 offen:
 *   Word 0:
 *     [31:26] = 0x38 = 111000
 *     [25:18] = 12 (BUFFER_LOAD_DWORD)
 *     [12]    = 1 (offen)
 *     [11:0]  = 0 (offset)
 *     = (0x38 << 26) | (12 << 18) | (1 << 12)
 *     = 0xE0301000
 *
 *   Word 1:
 *     [31:24] = 0x80 (soffset = off, literal 0 via SQ_SRC_0 = 128 = 0x80)
 *     [13:9]  = 0 (srsrc = s[0:3], group 0)
 *     [8]     = 0 (idxen = 0, we use offen)
 *     [7:0]   = 1 (vdata = v1)
 *     ... but where is vaddr?
 *
 * Hmm, vaddr is encoded differently. Let me re-read.
 * In MUBUF, VADDR is not explicitly in the encoding - it's implied by
 * OFFEN and IDXEN flags. When OFFEN=1, the VGPR right after VDATA provides
 * the offset. No wait - actually VADDR is:
 *
 * Looking at the actual ISA reference more carefully:
 *
 * Word 0: OFFSET[11:0], OFFEN[12], IDXEN[13], GLC[14], ADDR64[15], LDS[16],
 *         OP[24:18], ENC[31:26]=111000
 * Word 1: VADDR[39:32], VDATA[47:40], SRSRC[52:48], SLC[54], TFE[55],
 *         SOFFSET[63:56]
 *
 * So Word 1 layout:
 *   [7:0]   = VADDR  (v0)
 *   [15:8]  = VDATA  (v1)
 *   [20:16] = SRSRC  (0 for s[0:3], 1 for s[4:7])
 *   [22]    = SLC
 *   [23]    = TFE
 *   [31:24] = SOFFSET (0x80 for literal 0 / off)
 */

/* Build MUBUF instruction words */
static void build_mubuf(u32 *w0, u32 *w1,
			u32 opcode, u32 vaddr, u32 vdata,
			u32 srsrc_group, u32 offen)
{
	*w0 = (0x38u << 26) | (opcode << 18) | (offen << 12);
	*w1 = (0x80u << 24) | (srsrc_group << 16) | (vdata << 8) | vaddr;
}

/* Build VOP1 instruction: V_MOV_B32 etc.
 * Encoding: [31:25]=0, [24:17]=opcode, [16:9]=vdst, [8:0]=src0
 * VOP1 marker: bits [31:25] = 0111111 = 0x3F? No...
 *
 * VOP1 encoding on GCN1:
 *   [31:25] = 0x3F (0111111)
 *   [24:17] = opcode
 *   [16:9]  = VDST
 *   [8:0]   = SRC0
 */
static u32 build_vop1(u32 opcode, u32 vdst, u32 src0)
{
	return (0x3Fu << 25) | (opcode << 17) | (vdst << 9) | src0;
}

/* Build VOP2 instruction: V_ADD_I32 etc.
 * Encoding:
 *   [31]    = 0
 *   [30:25] = opcode
 *   [24:17] = VDST
 *   [16:9]  = VSRC1 (VGPR only)
 *   [8:0]   = SRC0 (SGPR/VGPR/literal/const)
 */
static u32 build_vop2(u32 opcode, u32 vdst, u32 src0, u32 vsrc1)
{
	return (opcode << 25) | (vdst << 17) | (vsrc1 << 9) | src0;
}

/* Build SOPP instruction: S_WAITCNT, S_ENDPGM etc.
 * Encoding:
 *   [31:23] = 101111111 = 0x17F
 *   [22:16] = opcode
 *   [15:0]  = SIMM16
 */
static u32 build_sopp(u32 opcode, u32 simm16)
{
	return (0x17Fu << 23) | (opcode << 16) | (simm16 & 0xFFFF);
}

/* S_ENDPGM = SOPP opcode 1, simm16=0 */
#define GCN_S_ENDPGM     build_sopp(1, 0)
/* S_WAITCNT = SOPP opcode 12, simm16 encodes vmcnt/expcnt/lgkmcnt */
/* vmcnt=0, expcnt=0, lgkmcnt=0 → simm16 = 0 */
#define GCN_S_WAITCNT_0  build_sopp(12, 0)

/*
 * The shader binary for: dst[gid] = src[gid] + 42
 * Single workgroup of 64 threads. gid == thread_id (v0).
 *
 * s[0:3] = src V# descriptor (via USER_DATA_0..3)
 * s[4:7] = dst V# descriptor (via USER_DATA_4..7)
 * v0     = thread_id_x (HW pre-loaded)
 *
 * Instructions (with computed encodings):
 */

#define SHADER_NUM_DWORDS 12  /* total DWORDs in shader */

static u32 shader_code[SHADER_NUM_DWORDS];

static void build_shader(void)
{
	u32 w0, w1;
	int i = 0;

	/* Inst 0: BUFFER_LOAD_DWORD v1, v0, s[0:3], 0 offen
	 * Load src[tid] into v1 */
	build_mubuf(&w0, &w1, 12, 0, 1, 0, 1);
	shader_code[i++] = w0;  /* MUBUF word 0 */
	shader_code[i++] = w1;  /* MUBUF word 1 */

	/* Inst 1: S_WAITCNT vmcnt(0) — wait for load */
	shader_code[i++] = GCN_S_WAITCNT_0;

	/* Inst 2: V_MOV_B32 v2, literal(42)
	 * VOP1 opcode 1 = V_MOV_B32, src0=255 (literal follows) */
	shader_code[i++] = build_vop1(1, 2, 255);
	shader_code[i++] = 42;  /* literal constant */

	/* Inst 3: V_ADD_I32 v3, v1, v2
	 * VOP2 opcode 37 = V_ADD_I32
	 * src0 = v1 = VGPR1 as src encoding = 256+1 = 257
	 * vsrc1 = v2 (VGPR number, not encoded +256 for vsrc1) */
	shader_code[i++] = build_vop2(37, 3, 257, 2);

	/* Inst 4: BUFFER_STORE_DWORD v3, v0, s[4:7], 0 offen
	 * Store v3 to dst[tid] using descriptor group 1 (s[4:7]) */
	build_mubuf(&w0, &w1, 28, 0, 3, 1, 1);
	shader_code[i++] = w0;
	shader_code[i++] = w1;

	/* Inst 5: S_WAITCNT vmcnt(0) — wait for store */
	shader_code[i++] = GCN_S_WAITCNT_0;

	/* Inst 6: S_ENDPGM */
	shader_code[i++] = GCN_S_ENDPGM;

	/* Padding NOPs to 256-byte alignment (64 DWORDs) — not strictly
	 * required but safe for ISA alignment constraints */
	while (i < SHADER_NUM_DWORDS)
		shader_code[i++] = build_sopp(0, 0); /* S_NOP */
}

/* =====================================================================
 * SI Buffer Resource Descriptor (V#) — 128 bits / 4 DWORDs
 *
 * DWORD0: base_address[31:0]
 * DWORD1: stride[29:16] | base_address[47:32] (bits [15:0])
 * DWORD2: num_records (element count for typed, byte count for raw)
 * DWORD3: dst_sel_x/y/z/w | num_format | data_format | ...
 *
 * For raw (untyped) DWORD buffer:
 *   stride = 4 (bytes per element)
 *   num_records = number of elements
 *   data_format = 4 (BUF_DATA_FORMAT_32)
 *   num_format = 1 (BUF_NUM_FORMAT_UINT)
 *   dst_sel = default (X,Y,Z,W → 4,5,6,7) in bits [11:0] of DW3
 * ===================================================================== */

static void build_buffer_v(u32 *desc, u64 gpu_addr, u32 num_elements,
			   u32 stride)
{
	desc[0] = (u32)(gpu_addr & 0xFFFFFFFF);
	desc[1] = (u32)((gpu_addr >> 32) & 0xFFFF) | (stride << 16);
	desc[2] = num_elements;
	/* data_format=4 at [25:22], num_format=1 at [28:26] */
	desc[3] = (4u << 22) | (1u << 26);
}

/* =====================================================================
 * Per-device state
 * ===================================================================== */

struct gcn_device {
	void __iomem *mmio;
	void __iomem *vram;
	u64           mmio_size;
	u64           vram_size;
	int           bar0_reserved;
	int           bar2_reserved;

	u32           wptr;
	int           ring_ready;
};

/* =====================================================================
 * MMIO / VRAM helpers
 * ===================================================================== */

static inline u32 gpu_rd32(struct gcn_device *gcn, u32 reg)
{
	return readl(gcn->mmio + reg);
}

static inline void gpu_wr32(struct gcn_device *gcn, u32 reg, u32 val)
{
	writel(val, gcn->mmio + reg);
}

static inline u32 vram_rd32(struct gcn_device *gcn, u64 offset)
{
	return readl(gcn->vram + offset);
}

static inline void vram_wr32(struct gcn_device *gcn, u64 offset, u32 val)
{
	writel(val, gcn->vram + offset);
}

/* =====================================================================
 * PM4 Ring Operations
 * ===================================================================== */

static void ring_emit(struct gcn_device *gcn, u32 value)
{
	u32 slot = gcn->wptr & RING_MASK;
	vram_wr32(gcn, VRAM_RING_OFFSET + (slot * 4), value);
	gcn->wptr++;
}

static void ring_commit(struct gcn_device *gcn)
{
	wmb();
	gpu_wr32(gcn, CP_RB0_WPTR, gcn->wptr & RING_MASK);
}

/* Emit SET_SH_REG: writes 1 register */
static void ring_set_sh_reg(struct gcn_device *gcn, u32 reg_byte_off, u32 val)
{
	u32 sh_offset = (reg_byte_off / 4) - SH_REG_BASE_DWORD;
	/* PM4 header: SET_SH_REG, count=2 (offset + value), shader_type=compute(bit1) */
	ring_emit(gcn, PM4_TYPE3_HDR(PM4_OP_SET_SH_REG, 2) | 2);
	ring_emit(gcn, sh_offset);
	ring_emit(gcn, val);
}

/* Emit SET_SH_REG for 2 consecutive registers */
static void ring_set_sh_reg_pair(struct gcn_device *gcn, u32 reg_byte_off,
				 u32 lo, u32 hi)
{
	u32 sh_offset = (reg_byte_off / 4) - SH_REG_BASE_DWORD;
	ring_emit(gcn, PM4_TYPE3_HDR(PM4_OP_SET_SH_REG, 3) | 2);
	ring_emit(gcn, sh_offset);
	ring_emit(gcn, lo);
	ring_emit(gcn, hi);
}

/* Emit SET_SH_REG for 4 consecutive registers (V# descriptor) */
static void ring_set_sh_reg_quad(struct gcn_device *gcn, u32 reg_byte_off,
				 u32 d0, u32 d1, u32 d2, u32 d3)
{
	u32 sh_offset = (reg_byte_off / 4) - SH_REG_BASE_DWORD;
	ring_emit(gcn, PM4_TYPE3_HDR(PM4_OP_SET_SH_REG, 5) | 2);
	ring_emit(gcn, sh_offset);
	ring_emit(gcn, d0);
	ring_emit(gcn, d1);
	ring_emit(gcn, d2);
	ring_emit(gcn, d3);
}

/* =====================================================================
 * CP Control
 * ===================================================================== */

static void cp_halt(struct gcn_device *gcn)
{
	gpu_wr32(gcn, CP_ME_CNTL, CP_ALL_HALT);
	udelay(100);
}

static void cp_unhalt(struct gcn_device *gcn)
{
	gpu_wr32(gcn, CP_ME_CNTL, 0);
	udelay(50);
}

/* =====================================================================
 * PM4 Ring Setup
 * ===================================================================== */

static int pm4_setup_ring(struct gcn_device *gcn)
{
	u32 cntl_val;
	int i;

	cp_halt(gcn);

	/* Zero ring + writeback */
	for (i = 0; i < (RING_SIZE_BYTES + 64) / 4; i++)
		vram_wr32(gcn, VRAM_RING_OFFSET + (i * 4), 0);

	gpu_wr32(gcn, CP_RB_WPTR_DELAY, 0);
	cntl_val = RING_LOG2 | (PAGE_LOG2 << 8);

	gpu_wr32(gcn, CP_RB0_CNTL, cntl_val | RB_RPTR_WR_ENA);
	gpu_wr32(gcn, CP_RB0_WPTR, 0);
	gcn->wptr = 0;

	gpu_wr32(gcn, CP_RB0_RPTR_ADDR, VRAM_RPTR_WB_OFFSET >> 8);
	gpu_wr32(gcn, CP_RB0_RPTR_ADDR_HI, 0);
	gpu_wr32(gcn, CP_RB0_CNTL, cntl_val);
	gpu_wr32(gcn, CP_RB0_BASE, VRAM_RING_OFFSET >> 8);

	printk(KERN_INFO "ail_payload: ring at VRAM+0x%x, RPTR WB at VRAM+0x%x\n",
	       VRAM_RING_OFFSET, VRAM_RPTR_WB_OFFSET);

	cp_unhalt(gcn);
	return 0;
}

/* =====================================================================
 * Ring Test — NOP submission
 * ===================================================================== */

static int pm4_ring_test(struct gcn_device *gcn)
{
	u32 rptr;
	int i;

	ring_emit(gcn, PM4_TYPE3_HDR(PM4_OP_NOP, 1));
	ring_emit(gcn, 0xDEADBEEF);
	ring_commit(gcn);

	for (i = 0; i < 100; i++) {
		rptr = gpu_rd32(gcn, CP_RB0_RPTR);
		if (rptr == (gcn->wptr & RING_MASK)) {
			printk(KERN_INFO "ail_payload: ring test PASSED"
			       " — RPTR=%u (%d ms)\n", rptr, i);
			gcn->ring_ready = 1;
			return 0;
		}
		msleep(1);
	}

	printk(KERN_WARNING "ail_payload: ring test FAILED — RPTR=%u want %u\n",
	       gpu_rd32(gcn, CP_RB0_RPTR), gcn->wptr & RING_MASK);
	return -EIO;
}

/* =====================================================================
 * Compute Dispatch: dst[gid] = src[gid] + 42
 * ===================================================================== */

static int compute_dispatch(struct gcn_device *gcn)
{
	u32 src_desc[4], dst_desc[4];
	u32 pgm_lo, pgm_hi;
	u32 rsrc1, rsrc2;
	u32 fence_val;
	u32 rptr;
	int i;

	printk(KERN_INFO "ail_payload: --- Compute Dispatch ---\n");

	/* 1. Build and upload shader to VRAM */
	build_shader();
	for (i = 0; i < SHADER_NUM_DWORDS; i++)
		vram_wr32(gcn, VRAM_SHADER_OFFSET + (i * 4), shader_code[i]);

	printk(KERN_INFO "ail_payload: shader uploaded to VRAM+0x%x"
	       " (%d DWORDs)\n", VRAM_SHADER_OFFSET, SHADER_NUM_DWORDS);

	/* Dump first few shader words for verification */
	for (i = 0; i < SHADER_NUM_DWORDS && i < 12; i++)
		printk(KERN_INFO "ail_payload:   shader[%d] = 0x%08x\n",
		       i, shader_code[i]);

	/* 2. Fill src buffer: src[i] = i for i in 0..63 */
	for (i = 0; i < NUM_ELEMENTS; i++)
		vram_wr32(gcn, VRAM_SRC_OFFSET + (i * 4), i);

	/* 3. Zero dst buffer */
	for (i = 0; i < NUM_ELEMENTS; i++)
		vram_wr32(gcn, VRAM_DST_OFFSET + (i * 4), 0);

	/* Also zero fence writeback */
	vram_wr32(gcn, VRAM_FENCE_WB_OFFSET, 0);

	printk(KERN_INFO "ail_payload: src filled (0..63), dst zeroed\n");

	/* 4. Build buffer V# descriptors */
	build_buffer_v(src_desc, VRAM_SRC_OFFSET, NUM_ELEMENTS, 4);
	build_buffer_v(dst_desc, VRAM_DST_OFFSET, NUM_ELEMENTS, 4);

	printk(KERN_INFO "ail_payload: src V# = {0x%08x, 0x%08x, 0x%08x, 0x%08x}\n",
	       src_desc[0], src_desc[1], src_desc[2], src_desc[3]);
	printk(KERN_INFO "ail_payload: dst V# = {0x%08x, 0x%08x, 0x%08x, 0x%08x}\n",
	       dst_desc[0], dst_desc[1], dst_desc[2], dst_desc[3]);

	/* 5. Emit PM4 packets for compute dispatch */

	/* PGM_LO/HI: shader GPU address >> 8 */
	pgm_lo = VRAM_SHADER_OFFSET >> 8;
	pgm_hi = 0;
	ring_set_sh_reg_pair(gcn, COMPUTE_PGM_LO, pgm_lo, pgm_hi);

	/* PGM_RSRC1:
	 *   bits [5:0] = (num_vgprs / 4) - 1 = (4/4)-1 = 0
	 *   bits [9:6] = (num_sgprs / 8) - 1 = (8/8)-1 = 0
	 *   We use 4 VGPRs (v0-v3) and 8 SGPRs (s0-s7)
	 */
	rsrc1 = 0;  /* 4 VGPRs, 8 SGPRs minimum granularity */
	ring_set_sh_reg(gcn, COMPUTE_PGM_RSRC1, rsrc1);

	/* PGM_RSRC2:
	 *   bits [5:1] = user_sgpr count = 8 (s0-s7 for two V# descriptors)
	 *   bit [6]    = tgid_x_en = 1 (enable workgroup ID X in SGPRs)
	 *   For single workgroup, we don't strictly need tgid, but safe
	 */
	rsrc2 = (8 << 1) | (1 << 6);
	ring_set_sh_reg(gcn, COMPUTE_PGM_RSRC2, rsrc2);

	/* RESOURCE_LIMITS: 0 = no restrictions */
	ring_set_sh_reg(gcn, COMPUTE_RESOURCE_LIMITS, 0);

	/* Thread group dimensions */
	ring_set_sh_reg(gcn, COMPUTE_NUM_THREAD_X, NUM_ELEMENTS);
	ring_set_sh_reg(gcn, COMPUTE_NUM_THREAD_Y, 1);
	ring_set_sh_reg(gcn, COMPUTE_NUM_THREAD_Z, 1);

	/* TMPRING_SIZE: 0 (no scratch) */
	ring_set_sh_reg(gcn, COMPUTE_TMPRING_SIZE, 0);

	/* STATIC_THREAD_MGMT: all CUs enabled */
	ring_set_sh_reg(gcn, COMPUTE_STATIC_THREAD_MGMT_SE0, 0xFFFFFFFF);
	ring_set_sh_reg(gcn, COMPUTE_STATIC_THREAD_MGMT_SE1, 0xFFFFFFFF);

	/* USER_DATA_0..3 = src V# descriptor (loaded into s[0:3]) */
	ring_set_sh_reg_quad(gcn, COMPUTE_USER_DATA_0,
			     src_desc[0], src_desc[1],
			     src_desc[2], src_desc[3]);

	/* USER_DATA_4..7 = dst V# descriptor (loaded into s[4:7]) */
	ring_set_sh_reg_quad(gcn, COMPUTE_USER_DATA_4,
			     dst_desc[0], dst_desc[1],
			     dst_desc[2], dst_desc[3]);

	/* DISPATCH_DIRECT: 1 workgroup x 1 x 1, initiator=1 */
	ring_emit(gcn, PM4_TYPE3_HDR(PM4_OP_DISPATCH_DIRECT, 4) | 2);
	ring_emit(gcn, 1);   /* dim_x = 1 workgroup */
	ring_emit(gcn, 1);   /* dim_y */
	ring_emit(gcn, 1);   /* dim_z */
	ring_emit(gcn, 1);   /* dispatch initiator */

	/* EVENT_WRITE_EOP: fence to signal completion
	 *   event_type = 0x14 (CACHE_FLUSH_AND_INV_TS)
	 *   event_index = 5 (BOTTOM_OF_PIPE)
	 *   data_sel = 1 (send 32-bit immediate)
	 */
	fence_val = 0xCAFE0001;
	ring_emit(gcn, PM4_TYPE3_HDR(PM4_OP_EVENT_WRITE_EOP, 5) | 2);
	ring_emit(gcn, 0x14 | (5 << 8));              /* event_type | event_index */
	ring_emit(gcn, VRAM_FENCE_WB_OFFSET);          /* addr lo */
	ring_emit(gcn, (1 << 24));                     /* addr hi + data_sel=1 */
	ring_emit(gcn, fence_val);                     /* data lo */
	ring_emit(gcn, 0);                             /* data hi */

	printk(KERN_INFO "ail_payload: PM4 packets emitted, WPTR=%u, committing\n",
	       gcn->wptr);

	/* Pre-commit diagnostics */
	printk(KERN_INFO "ail_payload: pre-commit RPTR=%u GRBM=0x%08x\n",
	       gpu_rd32(gcn, CP_RB0_RPTR), gpu_rd32(gcn, GRBM_STATUS));

	/* 6. Commit — kick the GPU */
	ring_commit(gcn);

	/* Post-commit: check if RPTR moves at all */
	msleep(5);
	printk(KERN_INFO "ail_payload: +5ms RPTR=%u GRBM=0x%08x\n",
	       gpu_rd32(gcn, CP_RB0_RPTR), gpu_rd32(gcn, GRBM_STATUS));

	/* 7. Wait for fence — short timeout, sleepable waits to avoid lockup */
	for (i = 0; i < 200; i++) {
		u32 fv = vram_rd32(gcn, VRAM_FENCE_WB_OFFSET);
		if (fv == fence_val) {
			printk(KERN_INFO "ail_payload: fence received"
			       " (0x%08x) after %d ms\n", fv, i);
			goto verify;
		}
		msleep(1);  /* 1ms sleep, yields CPU, no lockup */
	}

	/* Fence timeout — dump diagnostics */
	printk(KERN_WARNING "ail_payload: FENCE TIMEOUT — val=0x%08x want 0x%08x\n",
	       vram_rd32(gcn, VRAM_FENCE_WB_OFFSET), fence_val);
	printk(KERN_WARNING "ail_payload: GRBM_STATUS=0x%08x CP_ME_CNTL=0x%08x\n",
	       gpu_rd32(gcn, GRBM_STATUS), gpu_rd32(gcn, CP_ME_CNTL));
	printk(KERN_WARNING "ail_payload: RPTR=%u WPTR=%u\n",
	       gpu_rd32(gcn, CP_RB0_RPTR), gcn->wptr & RING_MASK);

	/* Still try to read results even if fence timed out */

verify:
	/* 8. Read back dst buffer and verify */
	rptr = gpu_rd32(gcn, CP_RB0_RPTR);
	printk(KERN_INFO "ail_payload: post-dispatch RPTR=%u WPTR=%u\n",
	       rptr, gcn->wptr & RING_MASK);

	{
		int errors = 0;
		for (i = 0; i < NUM_ELEMENTS; i++) {
			u32 got = vram_rd32(gcn, VRAM_DST_OFFSET + (i * 4));
			u32 expected = i + 42;
			if (got != expected) {
				if (errors < 8)
					printk(KERN_WARNING
					       "ail_payload:   dst[%d] = %u"
					       " (expected %u) FAIL\n",
					       i, got, expected);
				errors++;
			} else if (i < 4 || i >= 62) {
				printk(KERN_INFO
				       "ail_payload:   dst[%d] = %u OK\n",
				       i, got);
			}
		}

		printk(KERN_INFO "ail_payload: results: %d/%d correct,"
		       " %d errors\n",
		       NUM_ELEMENTS - errors, NUM_ELEMENTS, errors);

		if (errors == 0)
			printk(KERN_INFO "ail_payload:"
			       " *** ALL 64 ELEMENTS PASS ***\n");

		return errors ? -EIO : 0;
	}
}

/* =====================================================================
 * Module init/exit
 * ===================================================================== */

int ail_main(void)
{
	ail_printk("ail_shim: payload init — GCN driver\n");
	return ail_pci_register_driver();
}

void ail_exit(void)
{
	ail_pci_unregister_driver();
	ail_printk("ail_shim: payload exit — GCN driver\n");
}

/* =====================================================================
 * PCI probe
 * ===================================================================== */

int ail_pci_dev_probe(void *opaque_pdev)
{
	struct pci_dev *pdev = (struct pci_dev *)opaque_pdev;
	struct gcn_device *gcn;
	int rc;
	resource_size_t bar0_phys, bar0_len;

	gcn = kzalloc(sizeof(*gcn), GFP_KERNEL);
	if (!gcn)
		return -ENOMEM;

	rc = pci_enable_device(pdev);
	if (rc) goto err_free;
	pci_set_master(pdev);

	/* BAR2: MMIO */
	rc = pci_request_region(pdev, 2, "ailang_gcn_mmio");
	if (rc) goto err_disable;
	gcn->bar2_reserved = 1;
	gcn->mmio_size = pci_resource_len(pdev, 2);
	gcn->mmio = pci_iomap(pdev, 2, gcn->mmio_size);
	if (!gcn->mmio) { rc = -EIO; goto err_release_bar2; }

	/* BAR0: VRAM */
	gcn->vram_size = pci_resource_len(pdev, 0);
	bar0_phys = pci_resource_start(pdev, 0);
	bar0_len = gcn->vram_size;
	rc = pci_request_region(pdev, 0, "ailang_gcn_vram");
	if (rc == 0) {
		gcn->bar0_reserved = 1;
		gcn->vram = pci_iomap(pdev, 0, bar0_len);
	} else {
		gcn->bar0_reserved = 0;
		gcn->vram = ioremap_wc(bar0_phys, bar0_len);
	}
	if (!gcn->vram) { rc = -EIO; goto err_unmap_mmio; }

	printk(KERN_INFO "ail_payload: MMIO=%lluKB VRAM=%lluMB GRBM=0x%08x\n",
	       gcn->mmio_size / 1024, gcn->vram_size / (1024 * 1024),
	       gpu_rd32(gcn, GRBM_STATUS));

	pci_set_drvdata(pdev, gcn);

	/* Ring setup + test */
	pm4_setup_ring(gcn);
	rc = pm4_ring_test(gcn);
	if (rc) {
		printk(KERN_WARNING "ail_payload: ring test failed, skipping dispatch\n");
		return 0;
	}

	/* Compute dispatch */
	rc = compute_dispatch(gcn);
	printk(KERN_INFO "ail_payload: probe complete — compute %s\n",
	       rc == 0 ? "PASSED" : "FAILED");

	return 0;  /* always succeed probe so we can inspect */

err_unmap_mmio:
	pci_iounmap(pdev, gcn->mmio);
err_release_bar2:
	pci_release_region(pdev, 2);
err_disable:
	pci_clear_master(pdev);
	pci_disable_device(pdev);
err_free:
	kfree(gcn);
	return rc;
}

/* =====================================================================
 * PCI remove
 * ===================================================================== */

void ail_pci_dev_remove(void *opaque_pdev)
{
	struct pci_dev *pdev = (struct pci_dev *)opaque_pdev;
	struct gcn_device *gcn = pci_get_drvdata(pdev);

	if (gcn) {
		if (gcn->mmio) cp_halt(gcn);
		if (gcn->vram) {
			if (gcn->bar0_reserved) pci_iounmap(pdev, gcn->vram);
			else iounmap(gcn->vram);
		}
		if (gcn->mmio) pci_iounmap(pdev, gcn->mmio);
		if (gcn->bar0_reserved) pci_release_region(pdev, 0);
		if (gcn->bar2_reserved) pci_release_region(pdev, 2);
		kfree(gcn);
	}
	pci_clear_master(pdev);
	pci_disable_device(pdev);
	printk(KERN_INFO "ail_payload: removed\n");
}

/* Chardev stubs */
int ail_pci_dev_open(void *ctx, unsigned int minor) { return 0; }
int ail_pci_dev_release(void *ctx, unsigned int minor) { return 0; }
long ail_pci_dev_write(void *ctx, const void *ubuf, unsigned long count)
{ return (long)count; }
long ail_pci_dev_read(void *ctx, void *ubuf, unsigned long count)
{ return 0; }
long ail_pci_dev_ioctl(void *ctx, unsigned int cmd, unsigned long arg)
{ return -EPERM; }
