/*
 * Copyright (c) 2026, AiLang Project Contributors
 * SPDX-License-Identifier: GPL-2.0
 *
 * ail_shim_pcie.h — PCIe/DMA/IRQ/chardev shim extensions
 *
 * Extends the base ail_shim ABI with functions needed to write
 * PCIe device drivers in AiLang. All functions take ≤6 parameters
 * (System V AMD64 ABI register limit).
 *
 * The PCI device table is populated at load time from module params
 * (pci_vendor, pci_device). Ailang calls ail_pci_register_driver()
 * (zero-arg) to activate.
 * Probe/remove dispatch to ail_pci_dev_probe/ail_pci_dev_remove (Ailang).
 * Char device fops dispatch to ail_pci_dev_open/read/write/ioctl/release.
 * ISR handlers stay in C — they call complete() and return.
 */

#ifndef AIL_SHIM_PCIE_H
#define AIL_SHIM_PCIE_H

#include <linux/types.h>

/* =====================================================================
 * Ailang payload callbacks (implemented in ail_payload.o)
 * The shim calls these; the payload defines them.
 * ===================================================================== */

extern int  ail_pci_dev_probe(void *pdev);
extern void ail_pci_dev_remove(void *pdev);
extern int  ail_pci_dev_open(void *ctx, unsigned int minor);
extern int  ail_pci_dev_release(void *ctx, unsigned int minor);
extern long ail_pci_dev_write(void *ctx, const void *ubuf, unsigned long count);
extern long ail_pci_dev_read(void *ctx, void *ubuf, unsigned long count);
extern long ail_pci_dev_ioctl(void *ctx, unsigned int cmd, unsigned long arg);

/* =====================================================================
 * PCI Driver Registration
 * Zero-arg: the struct pci_driver with dynamically-populated device
 * table lives entirely in the C shim.
 * ===================================================================== */

int  ail_pci_register_driver(void);
void ail_pci_unregister_driver(void);

/* =====================================================================
 * PCI Device Management
 * ===================================================================== */

int   ail_pci_enable_device(void *pdev);
void  ail_pci_set_master(void *pdev);
int   ail_pci_request_regions(void *pdev, const char *name);
void  ail_pci_release_regions(void *pdev);
void *ail_pci_iomap(void *pdev, int bar, unsigned long maxlen);
void  ail_pci_iounmap(void *pdev, void *addr);
u64   ail_pci_resource_start(void *pdev, int bar);
u64   ail_pci_resource_len(void *pdev, int bar);
void  ail_pci_disable_device(void *pdev);
void *ail_pci_get_dev(void *pdev);  /* returns &pdev->dev as Address */

/* =====================================================================
 * DMA — all use struct device* obtained via ail_pci_get_dev()
 * ===================================================================== */

int   ail_dma_set_mask_and_coherent(void *dev, u64 mask);
/*
 * dma_alloc_coherent returns vaddr; writes dma_handle through
 * caller-provided pointer (Ailang can't return two values).
 */
void *ail_dma_alloc_coherent(void *dev, unsigned long size,
                             void *dma_handle_out, unsigned int gfp);
void  ail_dma_free_coherent(void *dev, unsigned long size,
                            void *vaddr, u64 dma_handle);
void  ail_dma_sync_for_cpu(void *dev, u64 dma_handle,
                           unsigned long size, int direction);
void  ail_dma_sync_for_device(void *dev, u64 dma_handle,
                              unsigned long size, int direction);

/* =====================================================================
 * Interrupts (MSI-X / MSI / Legacy)
 * ===================================================================== */

int   ail_pci_alloc_irq_vectors(void *pdev, int min_vecs, int max_vecs,
                                unsigned int flags);
void  ail_pci_free_irq_vectors(void *pdev);
int   ail_pci_irq_vector(void *pdev, int nr);
/*
 * request_irq with a C-side ISR stub. The stub calls complete()
 * on the completion object associated with channel_index.
 * dev_ctx is an opaque pointer stored by the shim for IRQ routing.
 */
int   ail_request_irq_stub(int irq, int channel_index, void *dev_ctx);
void  ail_free_irq(int irq, void *dev_ctx);

/* =====================================================================
 * Completions (replaces wait_event_interruptible_timeout macro)
 * ===================================================================== */

void *ail_completion_alloc(void);       /* kmalloc + init_completion */
void  ail_completion_free(void *comp);
void  ail_completion_reinit(void *comp);
/* Returns remaining jiffies (>0 = signaled), 0 = timeout */
int   ail_wait_for_completion_timeout(void *comp, unsigned long timeout_jiffies);
void  ail_complete(void *comp);

/* =====================================================================
 * Spinlocks (wraps macro-based spin_lock_irqsave)
 * ===================================================================== */

void *ail_spinlock_alloc(void);         /* kmalloc + spin_lock_init */
void  ail_spinlock_free(void *lock);
u64   ail_spin_lock_irqsave(void *lock);    /* returns saved flags */
void  ail_spin_unlock_irqrestore(void *lock, u64 flags);

/* =====================================================================
 * Device Model
 * ===================================================================== */

void *ail_class_create(const char *name);
void  ail_class_destroy(void *cls);
/* device_create with fixed format string — 6 args (max) */
void *ail_device_create_fmt(void *cls, void *parent, u64 devt,
                            void *drvdata, const char *name_fmt,
                            int index);
void  ail_device_destroy(void *cls, u64 devt);

/* =====================================================================
 * Firmware
 * ===================================================================== */

/* Returns firmware data pointer; stores size at *size_out.
 * Caller must call ail_release_firmware_handle when done. */
void *ail_request_firmware_buf(const char *name, void *dev,
                               unsigned long *size_out);
void  ail_release_firmware_handle(void *fw_handle);

/* =====================================================================
 * kfifo (fixed-element ring buffer for IRQ→process communication)
 * ===================================================================== */

void *ail_kfifo_alloc(unsigned int size);
void  ail_kfifo_free(void *fifo);
int   ail_kfifo_in(void *fifo, const void *buf, unsigned int n);
int   ail_kfifo_out(void *fifo, void *buf, unsigned int n);
int   ail_kfifo_len(void *fifo);

/* =====================================================================
 * Semaphore
 * ===================================================================== */

void *ail_sema_alloc(int val);
void  ail_sema_free(void *sem);
void  ail_down(void *sem);
void  ail_up(void *sem);

/* =====================================================================
 * Char Device fops bridge
 * The shim creates a struct file_operations that dispatches to
 * ail_pci_dev_open/read/write/ioctl/release. Ailang calls
 * ail_chardev_register() once during probe.
 * ===================================================================== */

void *ail_chardev_register(const char *name, int minor_count);
void  ail_chardev_unregister(void *ctx);
void  ail_chardev_set_drvdata(void *ctx, void *drvdata);
void *ail_chardev_get_drvdata(void *ctx);

/* =====================================================================
 * Userspace helpers
 * ===================================================================== */

int   ail_put_user_u32(unsigned int val, void __user *uaddr);
int   ail_get_user_u32(unsigned int *val, const void __user *uaddr);

#endif /* AIL_SHIM_PCIE_H */
