/*
 * Copyright (c) 2026, AiLang Project Contributors
 * SPDX-License-Identifier: GPL-2.0
 */

#ifndef AIL_SHIM_H
#define AIL_SHIM_H

#include <linux/types.h> // For size_t, u64
#include <linux/mutex.h> // For struct mutex
#include <linux/atomic.h> // For atomic_t
#include <linux/uaccess.h> // For copy_to_user, copy_from_user
#include <linux/sched.h> // For current process info

struct file_operations;
struct cdev;
struct file;
struct inode;

/*
 * This header defines the stable ABI between the AiLang-generated
 * kernel payload object (ail_payload.o) and the C shim object
 * (ail_shim.o).
 *
 * The shim provides wrappers around kernel functions that are
 * inconvenient to call directly from AiLang. The payload provides
 * the core logic.
 */

/*
 * == Functions provided by the AiLang payload ==
 * The shim expects the payload to define these symbols.
 */

// Called by the shim's module_init handler. Must return 0 on success.
extern int ail_main(void);

// Called by the shim's module_exit handler.
extern void ail_exit(void);

/*
 * == Functions provided by the C shim ==
 * The payload can call these functions. They are the only symbols
 * the payload should need to import from the shim.
 */

int ail_printk(const char *s);
void *ail_kmalloc(size_t size);
void ail_kfree(const void *obj);

void *ail_memcpy(void *dest, const void *src, size_t count);
void *ail_memset(void *s, int c, size_t n);
u64 ail_ktime_get_ns(void);
int ail_memcmp(const void *cs, const void *ct, size_t count);

/* User-space memory access (Syscall boundaries) */
unsigned long ail_copy_to_user(void *to, const void *from, unsigned long n);
unsigned long ail_copy_from_user(void *to, const void *from, unsigned long n);

/* Current process information */
int ail_get_current_pid(void);
int ail_get_current_tgid(void);

/* Delays */
void ail_msleep(unsigned int msecs);
void ail_udelay(unsigned long usecs);

/* Synchronization - Mutex */
void ail_mutex_init(struct mutex *lock);
void ail_mutex_lock(struct mutex *lock);
void ail_mutex_unlock(struct mutex *lock);

/* Synchronization - Atomics */
int ail_atomic_read(const atomic_t *v);
void ail_atomic_set(atomic_t *v, int i);
void ail_atomic_add(int i, atomic_t *v);
void ail_atomic_sub(int i, atomic_t *v);
void ail_atomic_inc(atomic_t *v);
int ail_atomic_dec_and_test(atomic_t *v);

/* Character Devices & /dev/ nodes */
int ail_alloc_chrdev_region(dev_t *dev, unsigned baseminor, unsigned count, const char *name);
void ail_unregister_chrdev_region(dev_t from, unsigned count);
void ail_cdev_init(struct cdev *cdev, const struct file_operations *fops);
int ail_cdev_add(struct cdev *p, dev_t dev, unsigned count);
void ail_cdev_del(struct cdev *p);

/* Device Number Macros */
unsigned int ail_MAJOR(dev_t dev);
unsigned int ail_MINOR(dev_t dev);
dev_t ail_MKDEV(unsigned int major, unsigned int minor);

/* Hardware I/O mapping */
void *ail_ioremap(phys_addr_t offset, unsigned long size);
void ail_iounmap(volatile void *addr);
u8 ail_readb(const volatile void *addr);
u16 ail_readw(const volatile void *addr);
u32 ail_readl(const volatile void *addr);
void ail_writeb(u8 b, volatile void *addr);
void ail_writew(u16 b, volatile void *addr);
void ail_writel(u32 b, volatile void *addr);

#endif // AIL_SHIM_H