/*
 * Temporary C-language stand-in for the AiLang-emitted payload.
 * Compiled to ail_payload.o so kbuild can link ail_combined.ko before
 * the AiLang -kmod codegen lands. Replace with real AiLang output once
 * PLAN.md Steps 2-5 are complete.
 */

#include <linux/kernel.h>
#include "ail_shim.h"

int ail_main(void)
{
	ail_printk("hello from stub payload (C stand-in)");
	return 0;
}

void ail_exit(void)
{
	ail_printk("goodbye from stub payload");
}
