/*
 * Copyright (c) 2026, AiLang Project Contributors
 * SPDX-License-Identifier: GPL-2.0
 */

#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/string.h>
#include <linux/ktime.h>
#include <linux/delay.h>
#include <linux/mutex.h>
#include <linux/atomic.h>
#include <linux/uaccess.h>
#include <linux/sched.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/io.h>
#include <linux/kdev_t.h>

#include "ail_shim.h"

MODULE_LICENSE("GPL");
MODULE_AUTHOR("AiLang Compiler");
MODULE_DESCRIPTION("C shim for an AiLang kernel module payload.");

/* Implemented in ail_payload.o */
extern int ail_main(void);
extern void ail_exit(void);

static int __init ail_shim_init(void)
{
	printk(KERN_INFO "ail_shim: loaded, invoking ail_main()\n");
	return ail_main();
}

static void __exit ail_shim_exit(void)
{
	ail_exit();
	printk(KERN_INFO "ail_shim: unloaded\n");
}

module_init(ail_shim_init);
module_exit(ail_shim_exit);

/* ABI wrappers for AiLang code */

int ail_printk(const char *s)
{
	return printk(KERN_INFO "%s", s);
}

void *ail_kmalloc(size_t size)
{
	return kmalloc(size, GFP_KERNEL);
}

void ail_kfree(const void *obj)
{
	kfree(obj);
}

void *ail_memcpy(void *dest, const void *src, size_t count)
{
	return memcpy(dest, src, count);
}

void *ail_memset(void *s, int c, size_t n)
{
	return memset(s, c, n);
}

u64 ail_ktime_get_ns(void)
{
	return ktime_get_ns();
}

int ail_memcmp(const void *cs, const void *ct, size_t count)
{
	return memcmp(cs, ct, count);
}

/* User-space memory access */

unsigned long ail_copy_to_user(void *to, const void *from, unsigned long n)
{
	return copy_to_user(to, from, n);
}

unsigned long ail_copy_from_user(void *to, const void *from, unsigned long n)
{
	return copy_from_user(to, from, n);
}

/* Current process context */

int ail_get_current_pid(void)
{
	return current->pid;
}

int ail_get_current_tgid(void)
{
	return current->tgid;
}

/* Delays */

void ail_msleep(unsigned int msecs)
{
	msleep(msecs);
}

void ail_udelay(unsigned long usecs)
{
	udelay(usecs);
}

/* Synchronization - Mutex */

void ail_mutex_init(struct mutex *lock)
{
	mutex_init(lock);
}

void ail_mutex_lock(struct mutex *lock)
{
	mutex_lock(lock);
}

void ail_mutex_unlock(struct mutex *lock)
{
	mutex_unlock(lock);
}

/* Synchronization - Atomics */

int ail_atomic_read(const atomic_t *v) { return atomic_read(v); }
void ail_atomic_set(atomic_t *v, int i) { atomic_set(v, i); }
void ail_atomic_add(int i, atomic_t *v) { atomic_add(i, v); }
void ail_atomic_sub(int i, atomic_t *v) { atomic_sub(i, v); }
void ail_atomic_inc(atomic_t *v) { atomic_inc(v); }
int ail_atomic_dec_and_test(atomic_t *v) { return atomic_dec_and_test(v); }

/* Character Devices & /dev/ nodes */

int ail_alloc_chrdev_region(dev_t *dev, unsigned baseminor, unsigned count, const char *name)
{
	return alloc_chrdev_region(dev, baseminor, count, name);
}

void ail_unregister_chrdev_region(dev_t from, unsigned count)
{
	unregister_chrdev_region(from, count);
}

void ail_cdev_init(struct cdev *cdev, const struct file_operations *fops)
{
	cdev_init(cdev, fops);
}

int ail_cdev_add(struct cdev *p, dev_t dev, unsigned count)
{
	return cdev_add(p, dev, count);
}

void ail_cdev_del(struct cdev *p)
{
	cdev_del(p);
}

unsigned int ail_MAJOR(dev_t dev) { return MAJOR(dev); }
unsigned int ail_MINOR(dev_t dev) { return MINOR(dev); }
dev_t ail_MKDEV(unsigned int major, unsigned int minor) { return MKDEV(major, minor); }

/* Hardware I/O mapping */

void *ail_ioremap(phys_addr_t offset, unsigned long size)
{
	return ioremap(offset, size);
}

void ail_iounmap(volatile void *addr)
{
	iounmap(addr);
}

u8 ail_readb(const volatile void *addr) { return readb(addr); }
u16 ail_readw(const volatile void *addr) { return readw(addr); }
u32 ail_readl(const volatile void *addr) { return readl(addr); }

void ail_writeb(u8 b, volatile void *addr) { writeb(b, addr); }
void ail_writew(u16 b, volatile void *addr) { writew(b, addr); }
void ail_writel(u32 b, volatile void *addr) { writel(b, addr); }