#include <linux/module.h>
#include <linux/export-internal.h>
#include <linux/compiler.h>

MODULE_INFO(name, KBUILD_MODNAME);

__visible struct module __this_module
__section(".gnu.linkonce.this_module") = {
	.name = KBUILD_MODNAME,
	.init = init_module,
#ifdef CONFIG_MODULE_UNLOAD
	.exit = cleanup_module,
#endif
	.arch = MODULE_ARCH_INIT,
};



static const struct modversion_info ____versions[]
__used __section("__versions") = {
	{ 0x9dd4105e, "free_irq" },
	{ 0x9f222e1e, "alloc_chrdev_region" },
	{ 0xa61fd7aa, "__check_object_size" },
	{ 0xa96d32ba, "__udelay" },
	{ 0x1abc7887, "release_firmware" },
	{ 0x092a35a2, "_copy_from_user" },
	{ 0x57860fb4, "wait_for_completion_timeout" },
	{ 0xdf9d1cc9, "pci_enable_device" },
	{ 0xd710adbf, "__kmalloc_noprof" },
	{ 0x64905a6c, "pci_alloc_irq_vectors" },
	{ 0x40a621c5, "snprintf" },
	{ 0x65026e43, "complete" },
	{ 0x562e3aaa, "__kfifo_in" },
	{ 0x60c9c0b3, "__init_swait_queue_head" },
	{ 0x545aba25, "request_firmware" },
	{ 0x962cecbf, "class_destroy" },
	{ 0x8735657e, "__pci_register_driver" },
	{ 0x4073d0de, "up" },
	{ 0x12ad300e, "iounmap" },
	{ 0x135ab977, "pci_request_regions" },
	{ 0xa53f4e29, "memcpy" },
	{ 0xcb8b6ec6, "kfree" },
	{ 0x7777f410, "pcim_iounmap" },
	{ 0xb10c127e, "pci_irq_vector" },
	{ 0x283bce08, "__kfifo_free" },
	{ 0xe1e1f979, "_raw_spin_lock_irqsave" },
	{ 0xda9a4f67, "pci_unregister_driver" },
	{ 0xd272d446, "__fentry__" },
	{ 0xe8213e80, "_printk" },
	{ 0xbd03ed67, "__ref_stack_chk_guard" },
	{ 0xd272d446, "__stack_chk_fail" },
	{ 0xd272d446, "__put_user_4" },
	{ 0x90a48d82, "__ubsan_handle_out_of_bounds" },
	{ 0xfaadbd72, "cdev_add" },
	{ 0x3f7ce9b9, "__dma_sync_single_for_cpu" },
	{ 0x9126ce86, "request_threaded_irq" },
	{ 0x01f403fc, "device_create" },
	{ 0x4073d0de, "down" },
	{ 0xb3d7f998, "class_create" },
	{ 0xbd03ed67, "random_kmalloc_seed" },
	{ 0xf46d5bf3, "mutex_lock" },
	{ 0x618e9852, "dma_alloc_attrs" },
	{ 0x6848eb64, "const_current_task" },
	{ 0x97dd6ca9, "ioremap" },
	{ 0x402db74e, "memcmp" },
	{ 0xc1e6c71e, "__mutex_init" },
	{ 0x81a1a811, "_raw_spin_unlock_irqrestore" },
	{ 0x27683a56, "memset" },
	{ 0x871567f6, "pci_set_master" },
	{ 0xd272d446, "__x86_return_thunk" },
	{ 0x092a35a2, "_copy_to_user" },
	{ 0x927f50df, "dma_set_coherent_mask" },
	{ 0x149d58c4, "dma_free_attrs" },
	{ 0x0bc5fb0d, "unregister_chrdev_region" },
	{ 0xf46d5bf3, "mutex_unlock" },
	{ 0x341fa0ae, "pci_release_regions" },
	{ 0x3f7ce9b9, "__dma_sync_single_for_device" },
	{ 0x7851be11, "__get_user_4" },
	{ 0x3124a198, "device_destroy" },
	{ 0x957c6137, "__kmalloc_cache_noprof" },
	{ 0x97acb853, "ktime_get" },
	{ 0x546c19d9, "validate_usercopy_range" },
	{ 0x8b8cfff0, "pcim_iomap" },
	{ 0x871567f6, "pci_disable_device" },
	{ 0x927f50df, "dma_set_mask" },
	{ 0xb3d1d601, "__kfifo_alloc" },
	{ 0x1336016d, "pci_free_irq_vectors" },
	{ 0xd1ea1c88, "__kfifo_out" },
	{ 0x67628f51, "msleep" },
	{ 0xbbb26ca8, "cdev_init" },
	{ 0x78339609, "kmalloc_caches" },
	{ 0x881f0858, "cdev_del" },
	{ 0x984622ae, "module_layout" },
};

static const u32 ____version_ext_crcs[]
__used __section("__version_ext_crcs") = {
	0x9dd4105e,
	0x9f222e1e,
	0xa61fd7aa,
	0xa96d32ba,
	0x1abc7887,
	0x092a35a2,
	0x57860fb4,
	0xdf9d1cc9,
	0xd710adbf,
	0x64905a6c,
	0x40a621c5,
	0x65026e43,
	0x562e3aaa,
	0x60c9c0b3,
	0x545aba25,
	0x962cecbf,
	0x8735657e,
	0x4073d0de,
	0x12ad300e,
	0x135ab977,
	0xa53f4e29,
	0xcb8b6ec6,
	0x7777f410,
	0xb10c127e,
	0x283bce08,
	0xe1e1f979,
	0xda9a4f67,
	0xd272d446,
	0xe8213e80,
	0xbd03ed67,
	0xd272d446,
	0xd272d446,
	0x90a48d82,
	0xfaadbd72,
	0x3f7ce9b9,
	0x9126ce86,
	0x01f403fc,
	0x4073d0de,
	0xb3d7f998,
	0xbd03ed67,
	0xf46d5bf3,
	0x618e9852,
	0x6848eb64,
	0x97dd6ca9,
	0x402db74e,
	0xc1e6c71e,
	0x81a1a811,
	0x27683a56,
	0x871567f6,
	0xd272d446,
	0x092a35a2,
	0x927f50df,
	0x149d58c4,
	0x0bc5fb0d,
	0xf46d5bf3,
	0x341fa0ae,
	0x3f7ce9b9,
	0x7851be11,
	0x3124a198,
	0x957c6137,
	0x97acb853,
	0x546c19d9,
	0x8b8cfff0,
	0x871567f6,
	0x927f50df,
	0xb3d1d601,
	0x1336016d,
	0xd1ea1c88,
	0x67628f51,
	0xbbb26ca8,
	0x78339609,
	0x881f0858,
	0x984622ae,
};
static const char ____version_ext_names[]
__used __section("__version_ext_names") =
	"free_irq\0"
	"alloc_chrdev_region\0"
	"__check_object_size\0"
	"__udelay\0"
	"release_firmware\0"
	"_copy_from_user\0"
	"wait_for_completion_timeout\0"
	"pci_enable_device\0"
	"__kmalloc_noprof\0"
	"pci_alloc_irq_vectors\0"
	"snprintf\0"
	"complete\0"
	"__kfifo_in\0"
	"__init_swait_queue_head\0"
	"request_firmware\0"
	"class_destroy\0"
	"__pci_register_driver\0"
	"up\0"
	"iounmap\0"
	"pci_request_regions\0"
	"memcpy\0"
	"kfree\0"
	"pcim_iounmap\0"
	"pci_irq_vector\0"
	"__kfifo_free\0"
	"_raw_spin_lock_irqsave\0"
	"pci_unregister_driver\0"
	"__fentry__\0"
	"_printk\0"
	"__ref_stack_chk_guard\0"
	"__stack_chk_fail\0"
	"__put_user_4\0"
	"__ubsan_handle_out_of_bounds\0"
	"cdev_add\0"
	"__dma_sync_single_for_cpu\0"
	"request_threaded_irq\0"
	"device_create\0"
	"down\0"
	"class_create\0"
	"random_kmalloc_seed\0"
	"mutex_lock\0"
	"dma_alloc_attrs\0"
	"const_current_task\0"
	"ioremap\0"
	"memcmp\0"
	"__mutex_init\0"
	"_raw_spin_unlock_irqrestore\0"
	"memset\0"
	"pci_set_master\0"
	"__x86_return_thunk\0"
	"_copy_to_user\0"
	"dma_set_coherent_mask\0"
	"dma_free_attrs\0"
	"unregister_chrdev_region\0"
	"mutex_unlock\0"
	"pci_release_regions\0"
	"__dma_sync_single_for_device\0"
	"__get_user_4\0"
	"device_destroy\0"
	"__kmalloc_cache_noprof\0"
	"ktime_get\0"
	"validate_usercopy_range\0"
	"pcim_iomap\0"
	"pci_disable_device\0"
	"dma_set_mask\0"
	"__kfifo_alloc\0"
	"pci_free_irq_vectors\0"
	"__kfifo_out\0"
	"msleep\0"
	"cdev_init\0"
	"kmalloc_caches\0"
	"cdev_del\0"
	"module_layout\0"
;

MODULE_INFO(depends, "");

MODULE_ALIAS("pci:v00001FE9d00000100sv*sd*bc*sc*i*");

MODULE_INFO(srcversion, "90925515EEE3CEB304CB75C");
