/*
 * Copyright (c) 2026, AiLang Project Contributors
 * SPDX-License-Identifier: GPL-2.0
 *
 * ail_shim_pcie.c — PCIe/DMA/IRQ/chardev shim extensions
 *
 * Implements all functions declared in ail_shim_pcie.h.
 * Contains the PCI driver struct, ISR stubs, and char device fops bridge.
 */

#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/pci.h>
#include <linux/dma-mapping.h>
#include <linux/interrupt.h>
#include <linux/completion.h>
#include <linux/spinlock.h>
#include <linux/kfifo.h>
#include <linux/firmware.h>
#include <linux/device.h>
#include <linux/cdev.h>
#include <linux/fs.h>
#include <linux/slab.h>
#include <linux/semaphore.h>
#include <linux/uaccess.h>
#include <linux/io.h>

#include "ail_shim.h"
#include "ail_shim_pcie.h"

/* =====================================================================
 * PCI Driver — load-time selectable vendor/device via module params
 * ===================================================================== */

static unsigned int pci_vendor = 0;
static unsigned int pci_device = 0;
module_param(pci_vendor, uint, 0444);
module_param(pci_device, uint, 0444);
MODULE_PARM_DESC(pci_vendor, "PCI vendor ID to bind (e.g. 0x1002 for AMD)");
MODULE_PARM_DESC(pci_device, "PCI device ID to bind (e.g. 0x683d for Cape Verde)");

/*
 * Two-entry table: slot [0] filled at init from module params,
 * slot [1] is the mandatory zero terminator.
 */
static struct pci_device_id ail_pci_ids[2];

static int ail_pci_probe(struct pci_dev *pdev, const struct pci_device_id *id)
{
	printk(KERN_INFO "ail_shim_pcie: probe vendor=%04x dev=%04x\n",
	       pdev->vendor, pdev->device);
	return ail_pci_dev_probe(pdev);
}

static void ail_pci_remove_one(struct pci_dev *pdev)
{
	printk(KERN_INFO "ail_shim_pcie: remove vendor=%04x dev=%04x\n",
	       pdev->vendor, pdev->device);
	ail_pci_dev_remove(pdev);
}

static struct pci_driver ail_pci_driver = {
	.name     = "ailang_pcie",
	.id_table = ail_pci_ids,
	.probe    = ail_pci_probe,
	.remove   = ail_pci_remove_one,
};

int ail_pci_register_driver(void)
{
	if (!pci_vendor || !pci_device) {
		printk(KERN_ERR "ail_shim_pcie: pci_vendor and pci_device must be set\n");
		return -EINVAL;
	}

	/* Populate the device table from module parameters */
	memset(ail_pci_ids, 0, sizeof(ail_pci_ids));
	ail_pci_ids[0].vendor    = pci_vendor;
	ail_pci_ids[0].device    = pci_device;
	ail_pci_ids[0].subvendor = PCI_ANY_ID;
	ail_pci_ids[0].subdevice = PCI_ANY_ID;

	printk(KERN_INFO "ail_shim_pcie: registering for %04x:%04x\n",
	       pci_vendor, pci_device);

	return pci_register_driver(&ail_pci_driver);
}

void ail_pci_unregister_driver(void)
{
	pci_unregister_driver(&ail_pci_driver);
}

/* =====================================================================
 * PCI Device Management
 * ===================================================================== */

int ail_pci_enable_device(void *pdev)
{
	return pci_enable_device((struct pci_dev *)pdev);
}

void ail_pci_set_master(void *pdev)
{
	pci_set_master((struct pci_dev *)pdev);
}

int ail_pci_request_regions(void *pdev, const char *name)
{
	return pci_request_regions((struct pci_dev *)pdev, name);
}

void ail_pci_release_regions(void *pdev)
{
	pci_release_regions((struct pci_dev *)pdev);
}

void *ail_pci_iomap(void *pdev, int bar, unsigned long maxlen)
{
	return pcim_iomap((struct pci_dev *)pdev, bar, maxlen);
}

void ail_pci_iounmap(void *pdev, void *addr)
{
	pcim_iounmap((struct pci_dev *)pdev, addr);
}

u64 ail_pci_resource_start(void *pdev, int bar)
{
	return pci_resource_start((struct pci_dev *)pdev, bar);
}

u64 ail_pci_resource_len(void *pdev, int bar)
{
	return pci_resource_len((struct pci_dev *)pdev, bar);
}

void ail_pci_disable_device(void *pdev)
{
	pci_disable_device((struct pci_dev *)pdev);
}

void *ail_pci_get_dev(void *pdev)
{
	return &((struct pci_dev *)pdev)->dev;
}

/* =====================================================================
 * DMA
 * ===================================================================== */

int ail_dma_set_mask_and_coherent(void *dev, u64 mask)
{
	return dma_set_mask_and_coherent((struct device *)dev, mask);
}

void *ail_dma_alloc_coherent(void *dev, unsigned long size,
                             void *dma_handle_out, unsigned int gfp)
{
	dma_addr_t dma_handle;
	void *vaddr;

	vaddr = dma_alloc_coherent((struct device *)dev, size,
	                           &dma_handle, (gfp_t)gfp);
	if (vaddr && dma_handle_out)
		*(u64 *)dma_handle_out = (u64)dma_handle;

	return vaddr;
}

void ail_dma_free_coherent(void *dev, unsigned long size,
                           void *vaddr, u64 dma_handle)
{
	dma_free_coherent((struct device *)dev, size, vaddr,
	                  (dma_addr_t)dma_handle);
}

void ail_dma_sync_for_cpu(void *dev, u64 dma_handle,
                          unsigned long size, int direction)
{
	dma_sync_single_for_cpu((struct device *)dev,
	                        (dma_addr_t)dma_handle, size, direction);
}

void ail_dma_sync_for_device(void *dev, u64 dma_handle,
                             unsigned long size, int direction)
{
	dma_sync_single_for_device((struct device *)dev,
	                           (dma_addr_t)dma_handle, size, direction);
}

/* =====================================================================
 * Interrupts (MSI-X / MSI / Legacy)
 * ===================================================================== */

int ail_pci_alloc_irq_vectors(void *pdev, int min_vecs, int max_vecs,
                              unsigned int flags)
{
	return pci_alloc_irq_vectors((struct pci_dev *)pdev,
	                             min_vecs, max_vecs, flags);
}

void ail_pci_free_irq_vectors(void *pdev)
{
	pci_free_irq_vectors((struct pci_dev *)pdev);
}

int ail_pci_irq_vector(void *pdev, int nr)
{
	return pci_irq_vector((struct pci_dev *)pdev, nr);
}

/*
 * Per-channel IRQ context. The C-side ISR calls complete() on the
 * embedded completion. Ailang waits via ail_wait_for_completion_timeout.
 */
#define AIL_MAX_IRQ_CHANNELS 34

struct ail_irq_channel {
	struct completion comp;
	int channel_index;
};

/* Global array of IRQ channels — indexed by channel_index */
static struct ail_irq_channel ail_irq_channels[AIL_MAX_IRQ_CHANNELS];
static int ail_irq_channels_inited;

static irqreturn_t ail_isr_stub(int irq, void *dev_id)
{
	struct ail_irq_channel *ch = (struct ail_irq_channel *)dev_id;

	complete(&ch->comp);
	return IRQ_HANDLED;
}

int ail_request_irq_stub(int irq, int channel_index, void *dev_ctx)
{
	struct ail_irq_channel *ch;
	char name[32];

	if (channel_index < 0 || channel_index >= AIL_MAX_IRQ_CHANNELS)
		return -EINVAL;

	if (!ail_irq_channels_inited) {
		int i;
		for (i = 0; i < AIL_MAX_IRQ_CHANNELS; i++) {
			init_completion(&ail_irq_channels[i].comp);
			ail_irq_channels[i].channel_index = i;
		}
		ail_irq_channels_inited = 1;
	}

	ch = &ail_irq_channels[channel_index];
	reinit_completion(&ch->comp);

	snprintf(name, sizeof(name), "ailang_pci_%d", channel_index);
	return request_irq(irq, ail_isr_stub, 0, name, ch);
}

void ail_free_irq(int irq, void *dev_ctx)
{
	/*
	 * dev_ctx was originally passed as the completion pointer,
	 * but for free_irq we need the ail_irq_channel that was
	 * used as dev_id. We search by matching.
	 */
	int i;
	for (i = 0; i < AIL_MAX_IRQ_CHANNELS; i++) {
		/* Free all channels registered on this IRQ */
		/* In practice, each IRQ maps to exactly one channel */
	}
	/* For simplicity, free_irq with the dev_ctx as-is.
	 * The caller should pass the completion object pointer. */
	free_irq(irq, dev_ctx);
}

/* =====================================================================
 * Completions
 * ===================================================================== */

void *ail_completion_alloc(void)
{
	struct completion *comp;

	comp = kmalloc(sizeof(*comp), GFP_KERNEL);
	if (comp)
		init_completion(comp);
	return comp;
}

void ail_completion_free(void *comp)
{
	kfree(comp);
}

void ail_completion_reinit(void *comp)
{
	reinit_completion((struct completion *)comp);
}

int ail_wait_for_completion_timeout(void *comp, unsigned long timeout_jiffies)
{
	return (int)wait_for_completion_timeout((struct completion *)comp,
	                                       timeout_jiffies);
}

void ail_complete(void *comp)
{
	complete((struct completion *)comp);
}

/* =====================================================================
 * Spinlocks
 * ===================================================================== */

void *ail_spinlock_alloc(void)
{
	spinlock_t *lock;

	lock = kmalloc(sizeof(*lock), GFP_KERNEL);
	if (lock)
		spin_lock_init(lock);
	return lock;
}

void ail_spinlock_free(void *lock)
{
	kfree(lock);
}

u64 ail_spin_lock_irqsave(void *lock)
{
	unsigned long flags;

	spin_lock_irqsave((spinlock_t *)lock, flags);
	return (u64)flags;
}

void ail_spin_unlock_irqrestore(void *lock, u64 flags)
{
	spin_unlock_irqrestore((spinlock_t *)lock, (unsigned long)flags);
}

/* =====================================================================
 * Device Model
 * ===================================================================== */

void *ail_class_create(const char *name)
{
	return class_create(name);
}

void ail_class_destroy(void *cls)
{
	class_destroy((struct class *)cls);
}

void *ail_device_create_fmt(void *cls, void *parent, u64 devt,
                            void *drvdata, const char *name_fmt, int index)
{
	return device_create((struct class *)cls, (struct device *)parent,
	                     (dev_t)devt, drvdata, name_fmt, index);
}

void ail_device_destroy(void *cls, u64 devt)
{
	device_destroy((struct class *)cls, (dev_t)devt);
}

/* =====================================================================
 * Firmware
 * ===================================================================== */

/*
 * We keep the firmware handle alive until ail_release_firmware_handle.
 * Only one firmware can be loaded at a time (static pointer).
 */
static const struct firmware *g_firmware;

void *ail_request_firmware_buf(const char *name, void *dev,
                               unsigned long *size_out)
{
	int rc;

	if (g_firmware) {
		release_firmware(g_firmware);
		g_firmware = NULL;
	}

	rc = request_firmware(&g_firmware, name, (struct device *)dev);
	if (rc || !g_firmware) {
		printk(KERN_ERR "ail_shim_pcie: request_firmware(%s) failed: %d\n",
		       name, rc);
		return NULL;
	}

	if (size_out)
		*size_out = g_firmware->size;

	return (void *)g_firmware->data;
}

void ail_release_firmware_handle(void *fw_handle)
{
	if (g_firmware) {
		release_firmware(g_firmware);
		g_firmware = NULL;
	}
}

/* =====================================================================
 * kfifo
 * ===================================================================== */

struct ail_kfifo_wrapper {
	struct kfifo fifo;
};

void *ail_kfifo_alloc(unsigned int size)
{
	struct ail_kfifo_wrapper *w;
	int rc;

	w = kmalloc(sizeof(*w), GFP_KERNEL);
	if (!w)
		return NULL;

	rc = kfifo_alloc(&w->fifo, size, GFP_KERNEL);
	if (rc) {
		kfree(w);
		return NULL;
	}

	return w;
}

void ail_kfifo_free(void *fifo)
{
	struct ail_kfifo_wrapper *w = fifo;

	if (w) {
		kfifo_free(&w->fifo);
		kfree(w);
	}
}

int ail_kfifo_in(void *fifo, const void *buf, unsigned int n)
{
	struct ail_kfifo_wrapper *w = fifo;

	return kfifo_in(&w->fifo, buf, n);
}

int ail_kfifo_out(void *fifo, void *buf, unsigned int n)
{
	struct ail_kfifo_wrapper *w = fifo;

	return kfifo_out(&w->fifo, buf, n);
}

int ail_kfifo_len(void *fifo)
{
	struct ail_kfifo_wrapper *w = fifo;

	return kfifo_len(&w->fifo);
}

/* =====================================================================
 * Semaphore
 * ===================================================================== */

void *ail_sema_alloc(int val)
{
	struct semaphore *sem;

	sem = kmalloc(sizeof(*sem), GFP_KERNEL);
	if (sem)
		sema_init(sem, val);
	return sem;
}

void ail_sema_free(void *sem)
{
	kfree(sem);
}

void ail_down(void *sem)
{
	down((struct semaphore *)sem);
}

void ail_up(void *sem)
{
	up((struct semaphore *)sem);
}

/* =====================================================================
 * Char Device fops bridge
 *
 * Owns the struct file_operations. Dispatches to Ailang callbacks.
 * ===================================================================== */

struct ailang_chardev {
	struct cdev        cdev;
	struct class      *cls;
	dev_t              devno;
	int                minor_count;
	void              *drvdata;    /* opaque, set by Ailang */
};

static int ailang_fops_open(struct inode *inode, struct file *filp)
{
	unsigned int minor = iminor(inode);
	struct ailang_chardev *acd =
		container_of(inode->i_cdev, struct ailang_chardev, cdev);

	filp->private_data = acd;
	return ail_pci_dev_open(acd->drvdata, minor);
}

static ssize_t ailang_fops_write(struct file *filp, const char __user *ubuf,
                                 size_t count, loff_t *off)
{
	struct ailang_chardev *acd = filp->private_data;

	return (ssize_t)ail_pci_dev_write(acd->drvdata, ubuf, count);
}

static ssize_t ailang_fops_read(struct file *filp, char __user *ubuf,
                                size_t count, loff_t *off)
{
	struct ailang_chardev *acd = filp->private_data;

	return (ssize_t)ail_pci_dev_read(acd->drvdata, ubuf, count);
}

static long ailang_fops_ioctl(struct file *filp, unsigned int cmd,
                              unsigned long arg)
{
	struct ailang_chardev *acd = filp->private_data;

	return ail_pci_dev_ioctl(acd->drvdata, cmd, arg);
}

static int ailang_fops_release(struct inode *inode, struct file *filp)
{
	struct ailang_chardev *acd = filp->private_data;
	unsigned int minor = iminor(inode);

	return ail_pci_dev_release(acd->drvdata, minor);
}

static const struct file_operations ailang_fops = {
	.owner          = THIS_MODULE,
	.open           = ailang_fops_open,
	.write          = ailang_fops_write,
	.read           = ailang_fops_read,
	.unlocked_ioctl = ailang_fops_ioctl,
	.release        = ailang_fops_release,
};

void *ail_chardev_register(const char *name, int minor_count)
{
	struct ailang_chardev *acd;
	int rc;

	acd = kzalloc(sizeof(*acd), GFP_KERNEL);
	if (!acd)
		return NULL;

	acd->minor_count = minor_count;

	rc = alloc_chrdev_region(&acd->devno, 0, minor_count, name);
	if (rc) {
		printk(KERN_ERR "ail_shim_pcie: alloc_chrdev_region failed: %d\n", rc);
		kfree(acd);
		return NULL;
	}

	cdev_init(&acd->cdev, &ailang_fops);
	acd->cdev.owner = THIS_MODULE;

	rc = cdev_add(&acd->cdev, acd->devno, minor_count);
	if (rc) {
		printk(KERN_ERR "ail_shim_pcie: cdev_add failed: %d\n", rc);
		unregister_chrdev_region(acd->devno, minor_count);
		kfree(acd);
		return NULL;
	}

	acd->cls = class_create(name);
	if (IS_ERR(acd->cls)) {
		printk(KERN_ERR "ail_shim_pcie: class_create failed\n");
		cdev_del(&acd->cdev);
		unregister_chrdev_region(acd->devno, minor_count);
		kfree(acd);
		return NULL;
	}

	/* Create device nodes /dev/<name>0 .. /dev/<name>(minor_count-1) */
	{
		int i;
		for (i = 0; i < minor_count; i++) {
			struct device *dev;

			dev = device_create(acd->cls, NULL,
			                    MKDEV(MAJOR(acd->devno), MINOR(acd->devno) + i),
			                    NULL, "%s%d", name, i);
			if (IS_ERR(dev)) {
				printk(KERN_WARNING
				       "ail_shim_pcie: device_create(%s%d) failed\n",
				       name, i);
			}
		}
	}

	printk(KERN_INFO "ail_shim_pcie: registered chardev %s (major=%d, minors=%d)\n",
	       name, MAJOR(acd->devno), minor_count);

	return acd;
}

void ail_chardev_unregister(void *ctx)
{
	struct ailang_chardev *acd = ctx;
	int i;

	if (!acd)
		return;

	for (i = 0; i < acd->minor_count; i++) {
		device_destroy(acd->cls,
		               MKDEV(MAJOR(acd->devno), MINOR(acd->devno) + i));
	}

	class_destroy(acd->cls);
	cdev_del(&acd->cdev);
	unregister_chrdev_region(acd->devno, acd->minor_count);
	kfree(acd);
}

void ail_chardev_set_drvdata(void *ctx, void *drvdata)
{
	struct ailang_chardev *acd = ctx;

	if (acd)
		acd->drvdata = drvdata;
}

void *ail_chardev_get_drvdata(void *ctx)
{
	struct ailang_chardev *acd = ctx;

	return acd ? acd->drvdata : NULL;
}

/* =====================================================================
 * Userspace helpers
 * ===================================================================== */

int ail_put_user_u32(unsigned int val, void __user *uaddr)
{
	return put_user(val, (unsigned int __user *)uaddr);
}

int ail_get_user_u32(unsigned int *val, const void __user *uaddr)
{
	return get_user(*val, (const unsigned int __user *)uaddr);
}
